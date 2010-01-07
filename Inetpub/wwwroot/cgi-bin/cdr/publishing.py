#----------------------------------------------------------------------
#
# Publishing CGI script.
#
# $Id$
# $Log: not supported by cvs2svn $
# Revision 1.29  2007/10/31 21:11:42  bkline
# Fixed handling of Unicode.
#
# Revision 1.28  2007/05/16 12:37:38  bkline
# Added non-breaking space when default paramater value is empty.
#
# Revision 1.27  2007/05/09 18:32:28  venglisc
# Definition of PUBTYPES moved from cdr2cg to cdr module.  Importing cdr2gk
# instead of cdr2cg now.
# Suppressing the Republish menu from displaying.  There exists a separate
# menu for this pubType.
#
# Revision 1.26  2006/11/24 20:56:04  venglisc
# Minor modifications to the publishing UI.
#
# Revision 1.25  2006/11/21 15:58:40  venglisc
# Modified to allow QCFilterSets to be run not just on MAHLER (but not on
# BACH. (Bug 2533)
#
# Revision 1.24  2004/01/21 22:42:40  venglisc
# Created a new screen for the Hot-Fix process allowing the user to
# copy/paste CDR IDs instead entering manually.  Also allowing user to pick
# between entering CDR IDs and loading IDs.
#
# Revision 1.23  2003/06/19 19:37:08  bkline
# Bumped up the number of rows for document IDs from 10 to 24.
#
# Revision 1.22  2003/02/07 21:15:53  pzhang
# Changed "reason +=" to "reason =".
#
# Revision 1.21  2002/11/20 16:57:15  pzhang
# Added GroupEmailAddrs and extracted user email from usr table.
#
# Revision 1.20  2002/11/07 23:11:28  pzhang
# Hid QcFilterSets system; Made SubSetName readonly.
#
# Revision 1.19  2002/11/05 21:26:27  pzhang
# Changed FONT of DESC.
# Added code to show default value based on control document.
#
# Revision 1.18  2002/11/05 18:42:30  pzhang
# Changed New to Current
#
# Revision 1.17  2002/11/05 16:04:34  pzhang
# Enhanced interface per Eileen's input
#
# Revision 1.16  2002/10/29 21:01:33  pzhang
# Called cdr.publish() with parameter allowInActive for Hotfix-Remove.
#
# Revision 1.15  2002/10/21 15:42:55  pzhang
# Increased number of Hotfix DocIds from 25 to 50.
#
# Revision 1.14  2002/09/12 18:50:56  pzhang
# Added port parameter to cdr.py function call.
#
# Revision 1.13  2002/09/03 22:27:39  pzhang
# Added picklist for values 'Yes'/'No'.
#
# Revision 1.12  2002/09/03 17:20:37  pzhang
# Added managing status link.
# Dropped inactive and mailer control documents from being displayed.
#
# Revision 1.11  2002/05/15 22:47:49  pzhang
# Added code for control document version.
# Detected valid PubType parameter values.
#
# Revision 1.10  2002/05/10 16:12:40  pzhang
# Made PubType parameter READONLY.
#
# Revision 1.9  2002/04/17 21:43:24  pzhang
# Rewrote code to match new cdrpub.py design.
# Dropped all CGI helpers in cdrpub.py.
#
# Revision 1.8  2002/03/01 22:43:01  pzhang
# Fixed a bug in forming param using white space as delimeter.
#
# Revision 1.7  2002/02/22 17:19:17  pzhang
# Skiped DocIdParameter page if there is no parameters and no docIds.
#
# Revision 1.6  2002/02/22 16:36:40  pzhang
# Moved hidden Session variable out of initHiddenValues for
# 	navigateTo to work properly.
#
# Revision 1.5  2002/02/21 15:20:35  bkline
# Added navigation buttons.
#
# Revision 1.4  2002/02/20 22:39:53  pzhang
# Changed module publish to cdrpub.
#
# Revision 1.3  2002/02/07 14:45:52  mruben
# added no output option
#
# Revision 1.2  2001/12/03 23:10:05  Pzhang
# Added email notification feature. Used PubStatus.py for status check.
#
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#
#----------------------------------------------------------------------
import cgi, cdrcgi, string, copy, urllib, cdr, cdr2gk, xml.dom.minidom
import socket, re
from win32com.client import Dispatch
import pythoncom


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
            connStr = "DSN=cdr;UID=CdrPublishing;PWD=***REMOVED***"
            self.__cdrConn = Dispatch('ADODB.Connection')
            self.__cdrConn.ConnectionString = connStr
            self.__cdrConn.Open()
        except pythoncom.com_error, (hr, msg, exc, arg):
            self.__cdrConn = None                    
            if exc is None:
                reason = "Code %d: %s" % (hr, msg)
            else:
                wcode, source, text, helpFile, helpId, scode = exc
                reason = "Src: " + source + ". Msg: " + text            
            self.__addFooter("Cdr connection failed. %s" % reason)
    
    #---------------------------------------------------------------- 
    # Display the pick list of all publishing systems by PubCtrl 
    # document type.
    # This is the main screen of the Publishing interface
    #----------------------------------------------------------------
    def displaySystems(self):

        publishes = []
        pubsys = ["Publishing.py", "", "", ""]        
        pickList = self.__getPubSys()
        for s in pickList:
            pubsys[1] = "%s" % s[1]
            pubsys[2] = "%s" % s[2]
            pubsys[3] = "%s [Version %s]<BR><FONT SIZE=3>%s</FONT>" % (
                s[0], s[2], s[3])            
            deep = copy.deepcopy(pubsys)
            publishes.append(deep)
        if type(publishes) == type(""): cdrcgi.bail(publishes)    

        form = "<H4>Publication Types</H4>\n"
        form += "<OL>\n"
        form += "<LI><A href='%s/%s?id=1&%s=%s&type=Manage'>%s</A>\
                     </LI>\n" % (cdrcgi.BASE, "PubStatus.py", cdrcgi.SESSION,
                     session, "Manage Publishing Job Status")

        for r in publishes:
            if r[3][0:7] == "Mailers":
                continue            
            if "BACH" ==  string.upper(socket.gethostname()):
                if r[3][0:12] == "QcFilterSets":
                    continue
            form += "<LI><A href='%s/%s?%s=%s&ctrlId=%s&version=%s'>%s</A>\
                     </LI>\n" % (cdrcgi.BASE, r[0], cdrcgi.SESSION, session, 
                     r[1], r[2], r[3])

        form += HIDDEN % (cdrcgi.SESSION, session)   
        self.__addFooter(form)


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
                subset[3] += '&Doc=Yes'
            if not subset[3]:
                subset[3] = 'Confirm=Yes'
                
            deep = copy.deepcopy(subset)
            subsets.append(deep)
        if type(subsets) == type(""): cdrcgi.bail(subsets)    

        form  = "<H4>Publishing Subsets of System:<BR/>%s</H4>\n" % sysName
        form += "<OL>\n"

        for r in subsets:
            if not r[1] == 'Republish-Export':
                form += """<LI><A 
                    href='%s/%s?%s=%s&ctrlId=%s&version=%s&SubSet=%s&%s'>
                    %s</A></LI>\n""" % (cdrcgi.BASE, r[0], cdrcgi.SESSION, 
                                        session, ctrlId, version, 
                                        urllib.quote_plus(r[1]), r[3], r[2])


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
<BR/>
%s</H4>
""" % SubSet 
        form += "<OL>\n"
        
        if Doc:
            # -------------------------------------------------------------
            # The idMethod "enter" has been selected.  Presenting a form
            # to copy/paste CDR IDs one by one
            # -------------------------------------------------------------
            # cdrcgi.bail("IDMethod: %s" % idMethod)
            if idMethod == 'enter':
                form += """ <LI>
  <B>Enter publishable document Id/Version [e.g.,190930 or 190930/3]:</B>
  <BR/>
  <TABLE BORDER='1'>
"""
        
                # This is up to userselect element in the control document.
                # Will revisit this.
                docIdList = ""
                for r in range(4):
                    form += "   <TR>\n"
                    for i in range(5):
                        id = 10 * r + i
                        docIdList += ",CdrDoc%d" % id
                        form += """    <TD>
     <INPUT NAME='CdrDoc%d' TYPE='TEXT' SIZE='10'>
    </TD>
""" % id
                    form += "   </TR>\n"
                if not Redirected: 
                    form += HIDDEN % ('DocIds', docIdList)

                form += "  </TABLE>\n  <P/>\n </LI>"

            else:
                # ---------------------------------------------------------
                # Enter the CDR IDs by copy/pasting from e-mail to operator
                # ---------------------------------------------------------
                form += """  <LI>
   <B>Paste in all CDR IDs</B>
   <BR/>
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

        docIdValues = ""
        if fields.has_key('DocIds'):
            docIdList = fields.getvalue('DocIds')
            names = string.split(docIdList, ",")
            for name in names:
                if fields.has_key(name):                   
                    docIdValues += ",CDR" + fields.getvalue(name).strip()
                   
        form += HIDDEN % ('Documents', docIdValues)    

        # Display message.
        form += """<H4>Publishing System Confirmation
        <BR/>%s</H4>""" % fields.getvalue('SubSet')

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
            Email to [use comma or semicolon between addresses]:<BR/>
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

        form = "<H4>Publishing SubSet:<BR/>%s</H4>\n" % subsetName     
           
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

    # -------------------------------------------------
    # Display screen to request load option for CDR IDs
    # -------------------------------------------------
    def displayLoadParam(self, ctrlId, version, SubSet, Param = None, 
                        Doc = None, Redirected = None):
        
        # Initialize hidden values.
        form = self.__initHiddenValues()  
        if fields.has_key('Param'):
            form += HIDDEN % ('Param', fields.getvalue('Param'))  
        if fields.has_key('Doc'):
            form += HIDDEN % ('Doc', fields.getvalue('Doc'))  
        
        form += """<H4>User Selected Documents and Parameters for Subset:
<BR/>
%s</H4>""" % SubSet 
        
        # UserSelect is allowed.
        form += """
<p>
<INPUT TYPE="radio" NAME="id-method" value="enter">&nbsp; Enter CDR IDs<BR>
<INPUT TYPE="radio" NAME="id-method" value="load" CHECKED="1">&nbsp; Load/Paste CDR IDs<BR>
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
        rs = self.__execSQL(sql)

        while not rs.EOF:
            tuple[0] = rs.Fields("title").Value
            tuple[1] = rs.Fields("id").Value
            tuple[2] = rs.Fields("num").Value
            docElem = rs.Fields("xml").Value.encode('utf-8')

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

            rs.MoveNext()

        rs.Close()
        rs = None
   
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
        rs = self.__execSQL(sql)

        while not rs.EOF:
            docElem = rs.Fields("xml").Value.encode('utf-8')

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

            rs.MoveNext()

        rs.Close()
        rs = None
       
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
        rs = self.__execSQL(sql)

        while not rs.EOF:
            docElem = rs.Fields("xml").Value.encode('utf-8')
            rs.MoveNext()
        rs.Close()
        rs = None

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
        rs = self.__execSQL(sql)

        email = ""
        while not rs.EOF:
            email = rs.Fields("email").Value or ""
            break
        rs.Close()
        rs = None
   
        return email
        
    #----------------------------------------------------------------
    # Execute the SQL statement using ADODB.
    #----------------------------------------------------------------
    def __execSQL(self, sql):     
      
        try:
            (rs, err) = self.__cdrConn.Execute(sql)
        except pythoncom.com_error, (hr, msg, exc, arg):            
            if exc is None:
                reason = "Code %d: %s" % (hr, msg)
            else:
                wcode, source, text, helpFile, helpId, scode = exc
                reason = "Src: " + source + ". Msg: " + text          
            rs = None
            self.__cdrConn.Close()
            self.__cdrConn = None
            self.__addFooter("Execute SQL failed. %s" % reason)
        return rs;

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
idMethod = fields and fields.getvalue("id-method") or "enter"
session  = cdrcgi.getSession(fields)
action   = cdrcgi.getRequest(fields)
title    = "CDR Administration"
section  = "Publishing"
buttons  = [cdrcgi.MAINMENU, "Log Out"]
header   = cdrcgi.header(title, title, section, "Publishing.py", buttons)
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
        # ---------------------------------------------------
        if getCdrIds == 'enter':
            docs = fields.getvalue('Documents')
            if docs:
                docIds = string.split(docs[1:], ",")  
        # ---------------------------------------------------
        # Process CDR IDs based on pasted data into textarea
        # ---------------------------------------------------
        else:
            docs = fields.getvalue('DocIds')
            if docs:
                docIds = re.split('\D+', docs)

                # Sort the list and remove empty elements
                # ----------------------------------------
                docIds.sort()
                docIds.reverse()
                for j in 1,2:
                    if docIds[len(docIds)-1] == '':
                        docIds.pop()
                # cdr.logwrite("docIds After: %s" % docIds)
                for i in range(len(docIds)):
                    docIds[i] = 'CDR' + str(int(docIds[i]))

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