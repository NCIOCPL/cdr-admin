#----------------------------------------------------------------------
#
# Publishing CGI script.
#
# $Id$
#
# BZIssue::2533
# BZIssue::4870
# BZIssue::5051 - [Media] Modify Publishing Software to Process Audio Files
#
#----------------------------------------------------------------------
import cgi, cdrcgi, string, copy, urllib, cdr, xml.dom.minidom
import lxml.etree as etree
import cdrdb, socket, re

#----------------------------------------------------------------------
# Testing if the document to be hot-fixed is a meeting recording doc.
#----------------------------------------------------------------------
def isMeetingRecording(id, cursor):

    # Meeting recordings have an attribute 'Internal'
    # -----------------------------------------------
    cursor.execute("""
        SELECT q.doc_id
          FROM query_term_pub q
         WHERE q.doc_id = ?
           AND q.value = 'Internal'   -- Meeting Recording
           AND q.path = '/Media/@Usage' """, id)
    row = cursor.fetchall()
    cursor.close()

    if row:
        return True
    return False

#----------------------------------------------------------------------
# Display Publishing System PickList
#----------------------------------------------------------------------
class Display:

    # Class private variables
    __cdrConn = None

    #----------------------------------------------------------------
    # Set up a connection to CDR. Abort when failed.
    #----------------------------------------------------------------
    def __init__(self):
        try:
            self.__conn   = cdrdb.connect()
            self.__cursor = self.__conn.cursor()
        except cdrdb.Error, info:
            reason = "Failure: %s" % info[1][0]
            self.__addFooter("Cdr connection failed. %s" % reason)

    #----------------------------------------------------------------
    # Display the pick list of all publishing systems by PubCtrl
    # document type.
    # This is the main screen of the Publishing interface
    #----------------------------------------------------------------
    def displaySystems(self):
        form = [u"""\
    <h4>Publication Types</h4>
    <ol>
     <li><a href='%s/PubStatus.py?id=1&%s=%s&type=Manage'
      >Manage Publishing Job Status</a></li>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session)]
        self.__cursor.execute("""\
            SELECT id
              FROM doc_type
             WHERE name = 'PublishingSystem'""")
        rows = self.__cursor.fetchall()
        if not rows:
            cdrcgi.bail("Publishing control document has disappeared!")
        self.__cursor.execute("""\
            SELECT id, title
              FROM active_doc
             WHERE doc_type = ?""", rows[0][0])
        rows = self.__cursor.fetchall()
        for docId, docTitle in rows:
            name = docTitle.upper().strip()
            if name == 'MAILERS':
                continue
            if cdr.isProdHost() and name == 'QCFILTERSETS':
                continue
            self.__cursor.execute("""\
                SELECT MAX(num)
                  FROM doc_version
                 WHERE publishable = 'Y'
                   AND val_status = 'V'
                   AND id = ?""", docId)
            rows = self.__cursor.fetchall()
            if not rows:
                continue
            docVersion = rows[0][0]
            self.__cursor.execute("""\
                SELECT xml
                  FROM doc_version
                 WHERE id = ?
                   AND num = ?""", (docId, docVersion))
            docXml = self.__cursor.fetchall()[0][0]
            tree = etree.XML(docXml.encode('utf-8'))
            desc = u"*** NO SYSTEM DESCRIPTION FOUND ***"
            for node in tree.findall('SystemDescription'):
                desc = node.text.strip()
            form.append(u"""\
     <li><a href='%s/publishing.py?%s=%s&ctrlId=%s&version=%d'
      >%s [Version %d]<br>%s</a></li>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session, docId, docVersion,
       cgi.escape(docTitle), docVersion, cgi.escape(desc)))
        form.append(u"""\
   </ol>
   <input type='hidden' name='%s' value='%s' />
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session))
        form = u"".join(form).encode('utf-8')
        cdrcgi.sendPage(header + form)

    #----------------------------------------------------------------
    # Display all subsets of the publishing system main menu.
    #----------------------------------------------------------------
    def displaySubsets(self, ctrlId, version):
        subsets = []
        subset = ["Publishing.py", "", "", "", ""]
        pickList = self.__getPubSubsets(ctrlId, version)
        sysName = pickList[0][0]
        for s in pickList:
            subset[1]  = s[1]
            subset[2]  = s[1]
            subset[2] += "<BR><FONT SIZE=3>%s</FONT>" % s[2]
            subset[2] += "<BR><BR>"
            subset[3]  = s[3] and 'Param=Yes' or ''
            if s[4]:
                subset[3] += '&amp;Doc=Yes'
            if not subset[3]:
                subset[3] = 'Confirm=Yes'

            deep = copy.deepcopy(subset)
            subsets.append(deep)
        if type(subsets) == type(""): cdrcgi.bail(subsets)

        form  = "<H4>Publishing Subsets of System:<BR>%s</H4>\n" % sysName
        form += "<OL>\n"

        for r in subsets:
            if not r[1] == 'Republish-Export':
                form += """ <LI><A
                    href='%s/%s?%s=%s&amp;ctrlId=%s&amp;version=%s&amp;SubSet=%s&amp;%s'>
                    %s</A></LI>\n""" % (cdrcgi.BASE, r[0], cdrcgi.SESSION,
                                        session, ctrlId, version,
                                        urllib.quote_plus(r[1]), r[3], r[2])

        form += "</OL>\n"
        form += HIDDEN % (cdrcgi.SESSION, session)
        self.__addFooter(form)

    #----------------------------------------------------------------------
    # Display the pick list of parameters of a publishing subset.
    # Don't want to display the SQL statement?
    # When it is redirected from Confirm page, don't add hidden
    #       Params and DocIds to avoid multiple values yielding
    #       a list instead of a string. Tricky!
    #----------------------------------------------------------------------
    def displayDocParam(self, ctrlId, version, SubSet, Param = None,
                        Doc = None, Redirected = None, idMethod = None):

        # Initialize hidden values.
        form = self.__initHiddenValues()

        form += HIDDEN % ('idMethod', idMethod)

        form += """
<H4>User Selected Documents and Parameters for Subset:
<BR>
%s</H4>
""" % SubSet
        form += "<OL>\n"

        if Doc:
            # -------------------------------------------------------------
            # The idMethod "MultiFieldEntry" has been selected.  Presenting
            # a form to enter CDR-IDs one by one
            # -------------------------------------------------------------
            if idMethod == 'MultiFieldEntry':
                form += """ <LI>
  <B>Enter publishable document Id/Version [e.g.,190930 or 190930/3]:</B>
  <BR>
  <TABLE BORDER='1'>
"""

                # This is up to userselect element in the control document.
                # Will revisit this.
                docIdList = []
                for r in range(4):
                    form += "   <TR>\n"
                    for i in range(5):
                        id = 5 * r + i
                        docIdList.append("CdrDoc%d" % id)
                        form += """    <TD>
     <INPUT NAME='CdrDoc%d' TYPE='TEXT' SIZE='10'>
    </TD>
""" % id
                    form += "   </TR>\n"
                if not Redirected:
                    form += HIDDEN % ('DocIds',
                           ','.join(["%s" % x for x in docIdList]))

                form += "  </TABLE>\n  <P/>\n </LI>"

            else:
                # ---------------------------------------------------------
                # Enter the CDR IDs by copy/pasting from e-mail to operator
                # ---------------------------------------------------------
                form += """  <LI>
   <B>Paste in all CDR IDs</B>
   <BR>
   <TEXTAREA NAME='DocIds' rows="10" cols="40"></TEXTAREA>
   <P/>
  </LI>"""

        # Subset parameters exist.
        if Param:
            params = []
            param = ["Publishing.py", "", ""]
            pickList = self.__getParamSQL(ctrlId, version, SubSet)
            for s in pickList:
                param[1] =  s[0]
                param[2] = s[1]
                deep = copy.deepcopy(param)
                params.append(deep)

            form += """
  <LI>
   <B>Modify default parameter values if applicable</B>

   <TABLE BORDER='1'>
    <TR>
     <TD>
      <B>Name</B>
     </TD>
     <TD>
      <B>Default Value</B>
     </TD>
     <TD>
      <B>Current Value</B>
     </TD>
    </TR>"""

            paramList = ""
            for r in params:
                paramList += ",%s" % r[1]
                if r[1] == "PubType":
                    if not cdr.PUBTYPES.has_key(r[2]):
                        self.__addFooter("The value of parameter PubType,\
                             %s, is not supported. <BR>Please modify \
                            the control document or the source code." % r[2])
                    form += """
    <TR>
     <TD>%s</TD>
     <TD>%s</TD>
     <TD><INPUT NAME='%s' VALUE='%s' READONLY></TD>
    </TR>\n""" % (r[1], r[2] or "&nbsp;", r[1], r[2])
                elif r[1] == "SubSetName" or r[1] == "GroupEmailAddrs":
                    form += """
    <TR>
     <TD>%s</TD>
     <TD>%s</TD>
     <TD><INPUT NAME='%s' VALUE='%s' READONLY></TD>
    </TR>
""" % (r[1], r[2] or "&nbsp;", r[1], r[2])
                elif r[2] in ("Yes", "No"):
                    # Create a picklist for parameter name/value pairs.
                    YesNo = (r[2] == "No") and "Yes" or "No"
                    pickList = """
      <SELECT NAME='%s'>
       <OPTION>%s</OPTION>
       <OPTION>%s</OPTION>
      </SELECT>
     """
                    form += """
    <TR>
     <TD>%s</TD>
     <TD>%s</TD>
     <TD>%s</TD>
    </TR>
""" % (r[1], r[2], pickList % (r[1], r[2], YesNo))
                else:
                    form += """
    <TR>
     <TD>%s</TD>
     <TD>%s</TD>
     <TD><INPUT NAME='%s' VALUE='%s'></TD>
    </TR>
""" % (r[1], r[2], r[1], r[2])
            if not Redirected:
                form += HIDDEN % ('Params', paramList)

            form += "</TABLE><P/>\n"

        form += "<INPUT NAME='Confirm' TYPE='SUBMIT' VALUE='Next >'></LI>"

        form += "</OL>\n"
        form += HIDDEN % (cdrcgi.SESSION, session)
        self.__addFooter(form)


    # -----------------------------------------------
    # Display a confirmation page.
    # -----------------------------------------------
    def displayConfirm(self):

        # Initialize hidden values.
        form = self.__initHiddenValues()

        # Form the parameters and documents to match the required
        # format of argument in publish.py.
        paramValues = ""
        grpEmailAddr = ""
        if fields.has_key('Params'):
            paramList = fields.getvalue('Params')
            names = string.split(paramList, ",")
            for name in names:
                if fields.has_key(name):
                    if name == "GroupEmailAddrs":
                        grpEmailAddr += fields.getvalue(name)
                    else:
                        paramValues += "," + name + ";" + \
                            fields.getvalue(name)

        form += HIDDEN % ('Parameters', paramValues)

        docIdValues = []
        if fields.has_key('DocIds'):
            docIdList = fields.getvalue('DocIds')
            inputMethod = fields.getvalue('idMethod')
            names = string.split(docIdList, ",")

            # CDR-IDs listed in text-area
            # ---------------------------
            if inputMethod == 'SingleFieldEntry':  
                # We're not supporting to publish older versions here
                # ---------------------------------------------------
                if docIdList.find('/') > -1:
                    cdrcgi.bail('Error: Publishing older versions not supported')
                docs = re.split('\D+', docIdList)

                # Prefixing 'CDR' to doc IDs to keep format of 
                # 'MultiFieldEntry' option. If a value isn't an integer 
                # (i.e. null), skip it.
                # -----------------------------------------------------------
                for doc in docs:
                    try:
                        docIdValues.append('CDR%d' % int(doc))
                    except ValueError:
                        pass

                # Sort the list and reverse the list.  We want to process
                # the newest files first.
                # -------------------------------------------------------
                docIdValues.sort()
                docIdValues.reverse()
            else:                # CDR-IDs listed in individual fields
                for name in names:
                    if fields.has_key(name):
                        docIdValues.append("CDR%s" % \
                                           fields.getvalue(name).strip())

        form += HIDDEN % ('Documents',','.join(["%s" % n for n in docIdValues]))

        # Display message.
        form += """<H4>Publishing System Confirmation
        <BR>%s</H4>""" % fields.getvalue('SubSet')

        addresses = grpEmailAddr and (grpEmailAddr + ";") or ""
        addresses += self.__getUsrAddr()
        form += """<table>
        <tr>
          <td>
            <input type="checkbox" checked name="Email" value="y">
          </td>
          <td>
            Email notification of completion?
          </td>
        </tr>
        <tr>
          <td>
            &nbsp;
          </td>
          <td>
            Email to [use comma or semicolon between addresses]:<BR>
            <input type="text" size="60" name="EmailAddr" value="%s">
          </td>
        </tr>
        <tr>
          <td>
            <input type="checkbox" name="NoOutput" value="Y">
          </td>
          <td>
            Messages only [no DB document files created]?
          </td>
        <tr>
        </table>

        <P/>""" % addresses

        form += """Publish this subset?&nbsp;&nbsp;
        <input type="submit" name="Publish" value="OK">"""

        form += HIDDEN % (cdrcgi.SESSION, session)
        cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")


    # -----------------------------------------------
    # Publish and return a link for checking status.
    # -----------------------------------------------
    def initPublish(self, credential, ctrlDocId, version, subsetName, params,
                    docIds, email, no_output):

        systemName = self.__getPubSubsets(ctrlDocId, version)[0][0]

        form = "<H4>Publishing SubSet:<BR>%s</H4>\n" % subsetName

        # Get publishing job ID.
        if subsetName == 'Hotfix-Remove':
            resp = cdr.publish(credential, systemName, subsetName, params, docIds,
                            email, no_output, port = cdr.getPubPort(),
                            allowInActive = 'Y')
        else:
            resp = cdr.publish(credential, systemName, subsetName, params, docIds,
                            email, no_output, port = cdr.getPubPort())
        jobId = resp[0]
        if not jobId:
            form += "<B>Failed:</B> %s\n" % resp[1]
        else:
            form += "<B>Started:</B> "
            form += "<A style='text-decoration: underline;' \
                    href='%s/%s?id=%s'>%s</A>\n" % (cdrcgi.BASE, 'PubStatus.py',
                    jobId, "Check the status of publishing job: %s" % jobId)

        form += HIDDEN % (cdrcgi.SESSION, session)
        self.__addFooter(form)

    # -------------------------------------------------------------
    # Display screen to request SingleFieldEntry option for CDR IDs
    # -------------------------------------------------------------
    def displayLoadParam(self, ctrlId, version, SubSet, Param = None,
                        Doc = None, Redirected = None):

        # Initialize hidden values.
        form = self.__initHiddenValues()
        if fields.has_key('Param'):
            form += HIDDEN % ('Param', fields.getvalue('Param'))
        if fields.has_key('Doc'):
            form += HIDDEN % ('Doc', fields.getvalue('Doc'))

        form += """<H4>User Selected Documents and Parameters for Subset:
<BR>
%s</H4>""" % SubSet

        # UserSelect is allowed.
        form += """
<p>
<INPUT TYPE="radio" NAME="id-method" 
       value="MultiFieldEntry">&nbsp; Enter CDR IDs<BR>
<INPUT TYPE="radio" NAME="id-method" 
       value="SingleFieldEntry" CHECKED>&nbsp; Load/Paste CDR IDs<BR>
"""

        form += "<BR>\n"
        form += "<INPUT NAME='Load' TYPE='SUBMIT' "
        form += "VALUE='Next >'>"

        form += HIDDEN % (cdrcgi.SESSION, session)
        self.__addFooter(form)


    def __addFooter(self, form):
        cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")


    def __initHiddenValues(self):
        form = ""

        if fields.has_key('ctrlId'):
            form += HIDDEN % ('ctrlId', fields.getvalue('ctrlId'))
        if fields.has_key('version'):
            form += HIDDEN % ('version', fields.getvalue('version'))
        if fields.has_key('SubSet'):
            form += HIDDEN % ('SubSet', fields.getvalue('SubSet'))
        if fields.has_key('Params'):
            form += HIDDEN % ('Params', fields.getvalue('Params'))
        if fields.has_key('DocIds'):
            form += HIDDEN % ('DocIds', fields.getvalue('DocIds'))
        if fields.has_key('idMethod'):
            form += HIDDEN % ('idMethod', fields.getvalue('idMethod'))
        return form


    #----------------------------------------------------------------------
    # Log debugging message to d:/cdr/log/publish.log.
    #----------------------------------------------------------------------
    def __logPub(self, line):
        file = "d:/cdr/log/publish.log"
        open(file, "a").write("== %s\n" % line)


    #----------------------------------------------------------------------
    # Return a list of publishing systems.
    #----------------------------------------------------------------------
    def __getPubSys(self):
        # Initialized the list of tuples: (title, id, version, desc).
        pickList = []
        tuple = ["", "", "", ""]

        sql = """SELECT d.title, d.id, d.num, d.xml
                   FROM doc_version d
                   JOIN doc_type t
                     ON d.doc_type = t.id
                   JOIN document active
                     ON active.id = d.id
                  WHERE t.name = 'PublishingSystem'
                    AND d.val_status = 'V'
                    and d.publishable = 'Y'
                    AND d.num = (SELECT MAX(num)
                                   FROM doc_version
                                  WHERE d.id = id)"""
        rows = self.__execSQL(sql)

        for row in rows:
            tuple[0] = row[0]
            tuple[1] = row[1]
            tuple[2] = row[2]
            docElem  = row[3].encode('utf-8')

            docElem = xml.dom.minidom.parseString(docElem).documentElement
            for node in docElem.childNodes:
                if node.nodeType == xml.dom.minidom.Node.ELEMENT_NODE:
                    if node.nodeName == 'SystemDescription':
                        tuple[3] = ''
                        for n in node.childNodes:
                            if n.nodeType == xml.dom.minidom.Node.TEXT_NODE:
                                tuple[3] = tuple[3] + n.nodeValue

            deep = copy.deepcopy(tuple)
            pickList.append(deep)

        return pickList


    #----------------------------------------------------------------
    # Return all subsets based on ctrlId.
    #----------------------------------------------------------------
    def __getPubSubsets(self, ctrlId, version):

        # Initialized the list of tuples: (sysName, subsetName, desc,
        #       param, userSelect, docTypes).
        pickList = []
        tuple = ["", "", "", "", ""]

        sql = "SELECT xml FROM doc_version \
                WHERE id = %s AND num = %s" % (ctrlId, version)
        rows = self.__execSQL(sql)

        for row in rows:
            docElem = row[0].encode('utf-8')

            docElem = xml.dom.minidom.parseString(docElem).documentElement
            for node in docElem.childNodes:
                if node.nodeType == xml.dom.minidom.Node.ELEMENT_NODE:
                    # SystemName comes first by schema. So tuple[0] will
                    #       be initialized once for all.
                    # We may not need this if the next page
                    #       does not show the system name.
                    if node.nodeName == 'SystemName':
                        tuple[0] = cdr.getTextContent(node)

                    if node.nodeName == 'SystemSubset':
                        tuple[1] = ''
                        tuple[2] = ''
                        tuple[3] = ''
                        tuple[4] = ''
                        for n in node.childNodes:
                            if n.nodeName == 'SubsetName':
                                tuple[1] = cdr.getTextContent(n)
                            if n.nodeName == 'SubsetDescription':
                                tuple[2] = cdr.getTextContent(n)
                            if n.nodeName == 'SubsetParameters':
                                tuple[3] = 'Yes'
                            if n.nodeName == 'SubsetSpecifications':
                                for m in n.childNodes:
                                    if m.nodeName == 'SubsetSpecification':
                                        for l in m.childNodes:
                                            if l.nodeName == 'SubsetSelection':
                                                for k in l.childNodes:
                                                    if k.nodeName == 'UserSelect':
                                                        tuple[4] = 'Yes'
                        deep = copy.deepcopy(tuple)
                        pickList.append(deep)

        return pickList


    #----------------------------------------------------------------
    # Return a SubSet node based on subsetName.
    # Don't need to check nodeType since the schema is known
    #    and subsetName is unique.
    # Error checking: node not found.
    #----------------------------------------------------------------
    def __getSubSet(self, docElem):

        pubSys = xml.dom.minidom.parseString(docElem).documentElement
        for node in pubSys.childNodes:
            if node.nodeName == "SystemSubset":
                for n in node.childNodes:
                    if n.nodeName == "SubsetName":
                        for m in n.childNodes:
                            if m.nodeValue == self.subsetName:
                                return node

        # not found
        msg = "Failed in __getSubSet. SubsetName: %s." % self.subsetName
        self.addFooter(msg)

    #----------------------------------------------------------------
    # Wanted to return the SQL statement for picking up DocIds as well,
    # but not done yet. Only returns the parameters so far.
    #----------------------------------------------------------------
    def __getParamSQL(self, ctrlId, version, Subset):
        # Initialized the list of tuples: (name, value).
        pickList = []
        tuple = ["", ""]

        sql = "SELECT xml FROM doc_version \
                WHERE id = %s AND num = %s" % (ctrlId, version)
        rows = self.__execSQL(sql)

        for row in rows:
            docElem = row[0].encode('utf-8')

        # Find the Subset node.
        subsetNode = None
        pubSys = xml.dom.minidom.parseString(docElem).documentElement
        for node in pubSys.childNodes:
            if subsetNode: break
            if node.nodeName == "SystemSubset":
                for n in node.childNodes:
                    if n.nodeName == "SubsetName":
                        if Subset == cdr.getTextContent(n):
                            subsetNode = node

        # Get the name/value pairs.
        for node in subsetNode.childNodes:
            if node.nodeName == "SubsetParameters":
                for n in node.childNodes:
                    if n.nodeName == "SubsetParameter":
                        for m in n.childNodes:
                            if m.nodeName == "ParmName":
                                tuple[0] = cdr.getTextContent(m)
                            elif m.nodeName == "ParmValue":
                                tuple[1] = cdr.getTextContent(m)
                        deep = copy.deepcopy(tuple)
                        pickList.append(deep)

        return pickList

    #----------------------------------------------------------------------
    # Return the email address of the session owner.
    #----------------------------------------------------------------------
    def __getUsrAddr(self):
        sql = """SELECT u.email
                   FROM usr u
                   JOIN session s
                     ON u.id = s.usr
                  WHERE s.name = '%s'""" % session
        rows = self.__execSQL(sql)

        email = ""
        for row in rows:
            email = row[0] or ""
            break

        return email


    #----------------------------------------------------------------
    # Execute the SQL statement using ADODB.
    #----------------------------------------------------------------
    def __execSQL(self, sql):
        try:
            self.__cursor.execute(sql, timeout = 300)
            rows = self.__cursor.fetchall()
        except cdrdb.Error, info:
            reason = "Failure: %s" % info[1][0]
            self.__addFooter("Execute SQL failed. %s" % reason)
            raise

        return rows

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
idMethod = fields and fields.getvalue("id-method") or "MultiFieldEntry"
session  = cdrcgi.getSession(fields)
action   = cdrcgi.getRequest(fields)
title    = "CDR Administration"
section  = "Publishing"
buttons  = [cdrcgi.MAINMENU, "Log Out"]
header   = cdrcgi.header(title, title, section, "publishing.py", buttons)
HIDDEN   = """<INPUT TYPE='HIDDEN' NAME='%s' VALUE='%s'>\n"""

#----------------------------------------------------------------------
# Return to the main menu if requested.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if action == "Log Out":
    cdrcgi.logout(session)

# Initialize Display class.
# This class does all the complex work.
d = Display()

# ------------------------------------------------------------------
# Submit the publishing job
# If the Publish variable exists we've entered Doc IDs to be
# published.
# Otherwise we are running a full set of documents to be published.
# ------------------------------------------------------------------
if fields.has_key('Session') and fields.has_key('SubSet') and \
    fields.has_key('Publish'):
    ctrlDocId = fields.getvalue('ctrlId')
    version = fields.getvalue('version')
    subsetName = fields.getvalue('SubSet')
    credential = fields.getvalue('Session')
    answer = fields.getvalue('Publish')
    getCdrIds = fields.getvalue('idMethod')

    if answer == 'No':
        d.displayDocParam(ctrlDocId, subsetName, Redirected = "Redirect")
    else:
        docIds = None
        # ---------------------------------------------------
        # Process CDR IDs based on individual data entry
        # Regular publishing jobs don't list documents.
        # ---------------------------------------------------
        docs = fields.getvalue('Documents')

        if docs:
            docIds = docs.split(",")

            # Create DB connection to pass a cursor
            # -------------------------------------
            try:
                conn   = cdrdb.connect()
                cursor = conn.cursor()
            except cdrdb.Error, info:
                reason = "Failure: %s" % info[1][0]
                cdr.logwrite("Cdr connection failed in isMeetingRecording(). \
                              %s" % reason)

            for docId in docIds:
                # At the moment the media documents include image files,
                # audio pronunciation files, and meeting recordings.  The
                # meeting recordings (MR) are excluded from regular
                # publishing but the hot-fix publishing would allow a
                # document to be published if the ID gets entered manually.
                # We're checking the IDs here to prevent this.
                # ---------------------------------------------------------
                if isMeetingRecording(cdr.exNormalize(docId)[1], cursor):
                    cdr.logwrite("Error: Internal document detected - %s" % 
                                                                       docId)
                    cdrcgi.bail("Error: Unable to publish Meeting \
                                 Recordings (usage='internal') - %s" % docId)

        params = None
        listParams = []
        parms = fields.getvalue('Parameters')
        if parms:
            params = string.split(parms[1:], ",")
            for p in params:
                deep = copy.deepcopy(tuple(string.split(p, ";")))
                listParams.append(deep)

        if fields.getvalue('Email') == 'y':
            email = fields.getvalue('EmailAddr')
        else:
            email = "Do not notify"
        if fields.getvalue('NoOutput') == 'Y':
            no_output = "Y"
        else:
            no_output = "N"
        d.initPublish(credential, ctrlDocId, version, subsetName,
                      listParams, docIds, email, no_output)

# ------------------------------------------------------------------
# Display the HotFix menu if the Param and Doc parameters are set
# in addition to session, control ID, and Subset ID
# ------------------------------------------------------------------
elif fields.has_key('Session') and fields.has_key('SubSet') and \
    fields.has_key('ctrlId') and fields.has_key('Load') and \
    fields.has_key('Param') and fields.has_key('Doc'):
    ctrlId = fields.getvalue('ctrlId')
    version = fields.getvalue('version')
    SubSet = fields.getvalue('SubSet')
    param = fields.getvalue('Param')
    doc = fields.getvalue('Doc')
    d.displayDocParam(ctrlId, version, SubSet, param, doc, idMethod = idMethod)

# ------------------------------------------------------------------
# Display Intermediary page to enter if CDR IDs should be entered
# manually or entered as copy/paste
# ------------------------------------------------------------------
elif fields.has_key('Session') and fields.has_key('SubSet') and \
    fields.has_key('ctrlId') and fields.has_key('Param') and \
    fields.has_key('Doc') and not fields.has_key('Load'):
    ctrlId = fields.getvalue('ctrlId')
    version = fields.getvalue('version')
    SubSet = fields.getvalue('SubSet')
    param = fields.getvalue('Param')
    doc = fields.getvalue('Doc')
    d.displayLoadParam(ctrlId, version, SubSet, param, doc)

# ------------------------------------------------------------------
# Display the Push Jobs menu if the Param and Doc parameters are set
# in addition to session, control ID, and Subset ID
# ------------------------------------------------------------------
elif fields.has_key('Session') and fields.has_key('SubSet') and \
    fields.has_key('ctrlId') and not fields.has_key('Load') and \
    (fields.has_key('Param') or fields.has_key('Doc')):
    ctrlId = fields.getvalue('ctrlId')
    version = fields.getvalue('version')
    SubSet = fields.getvalue('SubSet')
    param = fields.getvalue('Param')
    doc = fields.getvalue('Doc')
    idMethod = fields.getvalue('idMethod')
    d.displayDocParam(ctrlId, version, SubSet, param, doc)

# ------------------------------------------------------------------
# Display the confirmation page when the session parameter is
# specified, the control ID, and the SubSet ID and the submit button
# has been entered.
# ------------------------------------------------------------------
elif fields.has_key('Session') and fields.has_key('SubSet') \
    and fields.has_key('ctrlId') and fields.has_key('Confirm'):
    d.displayConfirm()

# ------------------------------------------------------------------
# Display the SubMenu System when the session parameter is specified
# and a control ID exists (identifying the parent menu item)
# ------------------------------------------------------------------
elif fields.has_key('Session') and fields.has_key('ctrlId'):
    ctrlId = fields.getvalue('ctrlId')
    version = fields.getvalue('version')
    d.displaySubsets(ctrlId, version)

# ------------------------------------------------------------------
# Display the Menu System if only the Session parameter is specified
# (the program is started)
# ------------------------------------------------------------------
elif fields.has_key('Session'):
    d.displaySystems()

# ------------------------------------------------------------------
# Log off if no parameters are specified
# ------------------------------------------------------------------
else:
    cdrcgi.logout(session)
