#----------------------------------------------------------------------
#
# Publishing CGI script.
#
# $Id: publishing.py,v 1.16 2002-10-29 21:01:33 pzhang Exp $
# $Log: not supported by cvs2svn $
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
import cgi, cdrcgi, string, copy, urllib, cdr, cdr2cg, xml.dom.minidom
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
    #----------------------------------------------------------------
    def displaySystems(self):

        publishes = []
        pubsys = ["Publishing.py", "", "", ""]        
        pickList = self.__getPubSys()
        for s in pickList:
            pubsys[1] = "%s" % s[1]
            pubsys[2] = "%s" % s[2]
            pubsys[3] = "%s [Version %s]<BR>[%s]" % (s[0], s[2], s[3])            
            deep = copy.deepcopy(pubsys)
            publishes.append(deep)
        if type(publishes) == type(""): cdrcgi.bail(publishes)    

        form = "<H4>Publication Types</H4>\n"
        form += "<OL>\n"
        form += "<LI><A HREF='%s/%s?id=1&%s=%s&type=Manage'>%s</A>\
                     </LI>\n" % (cdrcgi.BASE, "PubStatus.py", cdrcgi.SESSION,
                     session, "Manage Publishing Job Status")

        for r in publishes:
            if r[3][0:7] == "Mailers":
                continue
            form += "<LI><A HREF='%s/%s?%s=%s&ctrlId=%s&version=%s'>%s</A>\
                     </LI>\n" % (cdrcgi.BASE, r[0], cdrcgi.SESSION, session, 
                     r[1], r[2], r[3])

        form += HIDDEN % (cdrcgi.SESSION, session)   
        self.__addFooter(form)

    # Display the pick list of all subsets of a publishing system.
    def displaySubsets(self, ctrlId, version):
        
        subsets = []
        subset = ["Publishing.py", "", "", "", ""]      
        pickList = self.__getPubSubsets(ctrlId, version)
        sysName = pickList[0][0] 
        for s in pickList:
            subset[1] =  s[1] 
            subset[2] = s[1]
            subset[2] += "<BR>[Desc]: &nbsp;"  + s[2]
            #subset[2] += "<BR>[Params]: &nbsp;" + s[3]             
            #subset[2] += "<BR>[UserSel]: &nbsp;"  + s[4]            
            subset[3] = s[3] and 'Param=Yes' or ''                        
            if s[4]:
                subset[3] += '&Doc=Yes'
            if not subset[3]:
                subset[3] = 'Confirm=Yes'
                
            deep = copy.deepcopy(subset)
            subsets.append(deep)
        if type(subsets) == type(""): cdrcgi.bail(subsets)    

        form = "<H4>Publishing Subsets of %s</H4>\n" % sysName
        form += "<OL>\n"

        for r in subsets:
            form += """<LI><A 
                HREF='%s/%s?%s=%s&ctrlId=%s&version=%s&SubSet=%s&%s'>
                %s</A></LI>\n""" % (cdrcgi.BASE, r[0], cdrcgi.SESSION, 
                session, ctrlId, version, urllib.quote_plus(r[1]), r[3], r[2])

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
                        Doc = None, Redirected = None):
        
        # Initialize hidden values.
        form = self.__initHiddenValues()  
        
        form += "<H4>User Selected Documents and Parameters for Subset %s \
                 </H4>\n" % SubSet 
        form += "<OL>\n"
        
        # UserSelect is allowed.
        if Doc:
            form += "<LI><H5>Enter Publishable Document Id/Version [e.g. \
                     190930 or 190930/3]: </H5></LI>\n"
            form += "<TABLE BORDER='1'>"
        
            # This is up to userselect element in the control document.
            # Will revisit this.
            docIdList = ""
            for r in range(10):
                form += "<TR>"
                for i in range(5):
                    id = 10 * r + i
                    docIdList += ",CdrDoc%d" % id
                    form += """<TD><INPUT NAME='CdrDoc%d' TYPE='TEXT' 
                               SIZE='10'></TD>""" % id
                form += "</TR>\n"
            if not Redirected: 
                form += HIDDEN % ('DocIds', docIdList)

            form += "</TABLE></LI><BR>\n"

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

            form += "<LI><H5>Modify Default Parameter Values: </H5>\n"
            form += "<TABLE BORDER='1'><TR><TD>Name</TD><TD>Default "               
            form += "Value</TD>\n<TD>New Value</TD></TR>\n"
        
            paramList = ""
            for r in params:
                paramList += ",%s" % r[1]
                if r[1] == "PubType":
                    if not cdr2cg.PUBTYPES.has_key(r[2]):
                        self.__addFooter("The value of parameter PubType,\
                             %s, is not supported. <BR>Please modify \
                            the control document or the source code." % r[2])
                    form += """<TR><TD>%s</TD><TD>%s</TD><TD><INPUT \
                        NAME='%s' VALUE='%s' READONLY></TD></TR>\n""" % (
                        r[1], r[2], r[1], r[2])
                elif r[2] == "Yes" or r[2] == "No":
               
                    # Create a picklist for parameter name/value pairs.
                    pickList = "<SELECT NAME='%s'>\n<OPTION>Yes</OPTION>"
                    pickList += "\n<OPTION>No</OPTION>\n</SELECT>" 
                    form += "<TR><TD>%s</TD><TD>%s</TD><TD>%s</TD></TR>\n" % (
                        r[1], r[2], pickList % r[1])
                else:
                    form += """<TR><TD>%s</TD><TD>%s</TD><TD><INPUT \
                        NAME='%s' VALUE='%s'></TD></TR>\n""" % (r[1], r[2], 
                        r[1], r[2])
            if not Redirected:
                form += HIDDEN % ('Params', paramList)
        
            form += "</TABLE></LI><BR>\n"
            
        form += "<LI><INPUT NAME='Confirm' TYPE='SUBMIT' "
        form += "VALUE='Confirm Publishing This SubSet'></LI>"
        form += "<BR><BR>\n"
        
        form += HIDDEN % (cdrcgi.SESSION, session)   
        self.__addFooter(form)

    # Display a confirmation page.
    def displayConfirm(self):

        # Initialize hidden values.
        form = self.__initHiddenValues()

        # Form the parameters and documents to match the required 
        # format of argument in publish.py.
        paramValues = ""
        if fields.has_key('Params'):
            paramList = fields.getvalue('Params')
            names = string.split(paramList, ",")
            for name in names:
                if fields.has_key(name):
                    paramValues += "," + name + ";" +  fields.getvalue(name)
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
        form += "<H4>Publishing System Confirmation</H4>\n" 
        form += "<p>Do you want to publish subset: %s? <BR><BR>\n" \
             % fields.getvalue('SubSet')
        # form += "of system %s?</p>\n" % fields.getvalue('PubSys')
        form += """Email notification of completion?
        <input type="checkbox" checked name="Email" value="y">&nbsp;&nbsp;
        <BR> Use comma to separate recipients: &nbsp
        <input type="text" size="50" name="EmailAddr" 
        value="***REMOVED***"><br><br>Messages only?
        <input type="checkbox" name="NoOutput" value="Y"><br><br>
        <input type="submit" name="Publish" value="Yes">&nbsp;&nbsp; """      
         
        form += HIDDEN % (cdrcgi.SESSION, session)           
        cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")
    
    # Publish and return a link for checking status.
    def initPublish(self, credential, ctrlDocId, version, subsetName, params,
                    docIds, email, no_output):
    
        systemName = self.__getPubSubsets(ctrlDocId, version)[0][0]

        form = "<H4>Publishing SubSet: %s</H4>\n" % subsetName     
           
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
            form += "Check the <A HREF='%s/%s?id=%s'>%s</A>\n" % (cdrcgi.BASE, 
                'PubStatus.py', jobId, "status of publishing job: %s" % jobId)

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
            docElem = rs.Fields("xml").Value.encode('latin-1')

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
            docElem = rs.Fields("xml").Value.encode('latin-1')

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
            docElem = rs.Fields("xml").Value.encode('latin-1')
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
        
    #----------------------------------------------------------------
    # Execute the SQL statement using ADODB.
    #----------------------------------------------------------------
    def __execSQL(self, sql):     
      
        try:
            (rs, err) = self.__cdrConn.Execute(sql)
        except pythoncom.com_error, (hr, msg, exc, arg):            
            if exc is None:
                reason += "Code %d: %s" % (hr, msg)
            else:
                wcode, source, text, helpFile, helpId, scode = exc
                reason += "Src: " + source + ". Msg: " + text          
            rs = None
            self.__cdrConn.Close()
            self.__cdrConn = None
            self.__addFooter("Execute SQL failed. %s" % reason)
        return rs;

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
title   = "CDR Administration"
section = "Publishing"
buttons = [cdrcgi.MAINMENU, "Log Out"]
header  = cdrcgi.header(title, title, section, "Publishing.py", buttons)
HIDDEN = """<INPUT TYPE='HIDDEN' NAME='%s' VALUE='%s'>\n"""

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

if fields.has_key('Session') and fields.has_key('SubSet') and \
    fields.has_key('Publish'):
    ctrlDocId = fields.getvalue('ctrlId')
    version = fields.getvalue('version')
    subsetName = fields.getvalue('SubSet')
    credential = fields.getvalue('Session')
    answer = fields.getvalue('Publish')

    if answer == 'No':
        d.displayDocParam(ctrlDocId, subsetName, Redirected = "Redirect")
    else:        
        docs = fields.getvalue('Documents')
        docIds = None
        if docs:
            docIds = string.split(docs[1:], ",")  

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

elif fields.has_key('Session') and fields.has_key('SubSet') and \
    fields.has_key('ctrlId') and (fields.has_key('Param') or \
    fields.has_key('Doc')):
    ctrlId = fields.getvalue('ctrlId')
    version = fields.getvalue('version')
    SubSet = fields.getvalue('SubSet')
    param = fields.getvalue('Param')
    doc = fields.getvalue('Doc')
    d.displayDocParam(ctrlId, version, SubSet, param, doc)

elif fields.has_key('Session') and fields.has_key('SubSet') \
    and fields.has_key('ctrlId') and fields.has_key('Confirm'):
    d.displayConfirm()

elif fields.has_key('Session') and fields.has_key('ctrlId'):
    ctrlId = fields.getvalue('ctrlId')
    version = fields.getvalue('version')
    d.displaySubsets(ctrlId, version)

elif fields.has_key('Session'):    
    d.displaySystems()

else:
    cdrcgi.logout(session)
