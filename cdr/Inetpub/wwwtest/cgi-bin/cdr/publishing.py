#----------------------------------------------------------------------
#
# Publishing CGI script.
#
# $Id: publishing.py,v 1.8 2002-03-01 22:43:01 pzhang Exp $
# $Log: not supported by cvs2svn $
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
import cgi, cdrcgi, re, string, copy, os, sys, urllib, cdrpub

#----------------------------------------------------------------------
# Display Publishing System PickList
#----------------------------------------------------------------------
class Display:

    # No parameters needed yet.
    def __init__(self):
        pass

    # Display the pick list of all publishing systems 
    #   by PubCtrl document type.
    def displaySystems(self):

        publishes = []
        pubsys = ["Publishing.py", "", ""]
        p = cdrpub.Publish("Fake", "Fake", "Fake", "Fake", "Fake")    
        pickList = p.getPubSys()
        for s in pickList:
            pubsys[1] =  "%d" % s[1] 
            pubsys[2] = s[2]
            #pubsys[2] += "<BR>[Control]: &nbsp;" + s[0]
            #pubsys[2] += "<BR>[CtrlId]: &nbsp;" + pubsys[1]
            pubsys[2] += "<BR>[" + s[3] + "]"
            deep = copy.deepcopy(pubsys)
            publishes.append(deep)
        if type(publishes) == type(""): cdrcgi.bail(publishes)    

        form = "<H4>Publication Types</H4>\n"
        form += "<OL>\n"

        for r in publishes:
            form += "<LI><A HREF='%s/%s?%s=%s&ctrlId=%s'>%s</A></LI>\n" \
                % (cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1], r[2])

        form += HIDDEN % (cdrcgi.SESSION, session)   
        self.__addFooter(form)

    # Display the pick list of all subsets of a publishing system.
    def displaySubsets(self, ctrlId):
        
        subsets = []
        subset = ["Publishing.py", "", "", ""]
        p = cdrpub.Publish(ctrlId, "Fake", "Fake", "Fake", "Fake")
        pickList = p.getPubSubset()
        sysName = pickList[0][2] # Not a good implementation.
        for s in pickList:
            subset[1] =  s[0] 
            subset[2] = s[0]
            subset[2] += "<BR>[Desc]: &nbsp;"  + s[1]
            subset[2] += "<BR>[Params]: &nbsp;"  + s[3]
            subset[2] += "<BR>[UserSel]: &nbsp;"  + s[4]
            subset[3] = s[3] and s[3] or s[4]
            if subset[3]:
                subset[3] = 'DocParam=Yes'
            else:
                subset[3] = 'Confirm=Yes'
                
            deep = copy.deepcopy(subset)
            subsets.append(deep)
        if type(subsets) == type(""): cdrcgi.bail(subsets)    

        form = "<H4>Publishing Subsets of %s</H4>\n" % sysName
        form += "<OL>\n"

        for r in subsets:
            form += """<LI><A HREF='%s/%s?%s=%s&ctrlId=%s&SubSet=%s&%s'>
                %s</A></LI>\n""" % (cdrcgi.BASE, r[0], cdrcgi.SESSION, session, 
                ctrlId, urllib.quote_plus(r[1]), r[3], r[2])

        form += HIDDEN % (cdrcgi.SESSION, session)   
        self.__addFooter(form)

    # Display the pick list of parameters of a publishing subset.
    # Don't want to display the SQL statement?
    # When it is redirected from Confirm page, don't add hidden
    #   Params and DocIds to avoid multiple values yielding
    #   a list instead of a string. Tricky!
    def displayDocParam(self, ctrlId, SubSet, Redirected = None):
        
        params = []
        param = ["Publishing.py", "", ""]
        p = cdrpub.Publish(ctrlId, SubSet, "Fake", "Fake", "Fake")
        pickList = p.getParamSQL()
        for s in pickList:
            param[1] =  s[0] 
            param[2] = s[1]        
            deep = copy.deepcopy(param)
            params.append(deep)
        if type(params) == type(""): cdrcgi.bail(params)
        
        # Initialize hidden values.
        form = self.__initHiddenValues()    

        form += "<H4>Parameters and Documents for Subset %s</H4>\n" % SubSet
        form += "<OL>\n"
        form += "<LI><H5>Enter Publishable Document IDs [e.g., 190930/3]: </H5></LI>\n"
        form += "<TABLE BORDER='1'>"
        
        # This is up to userselect element in the control document.
        # Will revisit this.
        docIdList = ""
        for r in range(5):
            form += "<TR>"
            for i in range(5):
                id = 10 * r + i
                docIdList += ",Doc%d" % id
                form += """<TD><INPUT NAME='Doc%d' TYPE='TEXT' SIZE='10'>
                    </TD>""" % id
            form += "</TR>\n"
        if not Redirected: 
            form += HIDDEN % ('DocIds', docIdList)

        form += "</TABLE></LI><BR>\n"
        form += "<LI><H5>Update Valid Parameter Values: </H5>\n"
        form += "<TABLE BORDER='1'><TR><TD>Name</TD><TD>Default Value</TD>\n"
        form += "<TD>New Value</TD></TR>\n"
        
        paramList = ""
        for r in params:
            paramList += ",%s" % r[1]
            form += """<TR><TD>%s</TD><TD>%s</TD><TD><INPUT NAME='%s' \
                VALUE='%s'></TD></TR>\n""" % (r[1], r[2], r[1], r[2])
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
                    value = fields.getvalue(name)
                    p = cdrpub.Publish(0, "Fake", "Fake", "Fake", "Fake")  
                    if -1 != p.isPublishable(value):
                        docIdValues += "," + fields.getvalue(name)
                    else:
                        form = "<H4>Document: %s is not publishable. " \
                            "Please click back and enter a publishable " \
                            "document.</H4>\n" % value
                        cdrcgi.bail(form)                
        form += HIDDEN % ('Documents', docIdValues)    

        # Display message.
        form += "<H4>Publishing System Confirmation</H4>\n" 
        form += "<p>Do you want to publish subset: %s? <BR><BR>\n" \
             % fields.getvalue('SubSet')
        # form += "of system %s?</p>\n" % fields.getvalue('PubSys')
        form += """Email notification of completion?
        <input type="checkbox" checked name="Email" value="y">&nbsp;&nbsp;
        <BR> Use comma to separate recipients: &nbsp
        <input type="text" size="50" name="EmailAddr" value="***REMOVED***"><br><br>
        Messages only?
        <input type="checkbox" name="NoOutput" value="Y"><br><br>
        <input type="submit" name="Publish" value="Yes">&nbsp;&nbsp;
        <input type="submit" name="Publish" value="No">""" 
         
        form += HIDDEN % (cdrcgi.SESSION, session)           
        cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")
    
    # Publish and return a link for checking status.
    def initPublish(self, ctrlDocId, subsetName, credential, docIds, params,
                    email, no_output):

        form = "<H4>Publishing SubSet %s</H4>\n" % subsetName
        form += "<OL>\n"
    
        # Get publishing job ID.       
        p = cdrpub.Publish(ctrlDocId, subsetName, credential, docIds, params,
                            email, no_output)
        jobId = p.getJobId()
        if type(jobId) == type(""):            
            form += "<LI>Failed: <H5>%s</H5></LI>\n" % jobId
        else:
            form += "<LI>Started: </LI><BR>\n"            
            form += """Check the <A HREF='%s/%s?id=%d'>%s</A></LI>\n
                    """ % (cdrcgi.BASE, 'PubStatus.py', jobId,
                        "status of publishing job: %d" % jobId)

        form += HIDDEN % (cdrcgi.SESSION, session)   
        self.__addFooter(form)

    # Display the status. Use Bob's PubStatus.py instead.
    def getStatus(self, jobId):

        # Initialize hidden values.
        form = self.__initHiddenValues()
        
        form += "<H4>Status of Publishing Job: %s</H4>\n" % jobId
        form += "<OL>\n"
            
        # Get publishing job status.
        form += "<LI><BR><TABLE BORDER='1'><TR><TD>Id</TD><TD>Output Directory</TD>" \
                "<TD>Started</TD><TD>Completed</TD><TD>Status</TD>" \
                "<TD>Messages</TD></TR>"
        
        # Return pub_proc id or an error message.
        p = cdrpub.Publish("Fake", "Fake", "Fake", "Fake", "Fake")
        row = p.getStatus(jobId)
        form += "<TR>"
        for i in range(6):
            form += "<TD>%s</TD>" % row[i]
        form += "</TR></TABLE><BR></LI>"    

        form += HIDDEN % (cdrcgi.SESSION, session)   
        self.__addFooter(form)
          
    def __addFooter(self, form):

        form += """\
        <LI><A HREF="%s/Logout.py?%s=%s">%s</A></LI>
        </OL>
        """ % (cdrcgi.BASE, cdrcgi.SESSION, session, "Log Out")      
        cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")

    def __initHiddenValues(self):
            
        form = ""
   
        if fields.has_key('ctrlId'):
            form += HIDDEN % ('ctrlId', fields.getvalue('ctrlId'))                  
        if fields.has_key('SubSet'):
            form += HIDDEN % ('SubSet', fields.getvalue('SubSet'))
        if fields.has_key('Params'):
            form += HIDDEN % ('Params', fields.getvalue('Params'))
        if fields.has_key('DocIds'):
            form += HIDDEN % ('DocIds', fields.getvalue('DocIds'))                    
        
        return form

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
title   = "CDR Administration"
section = "Publishing"
buttons = [cdrcgi.MAINMENU]
header  = cdrcgi.header(title, title, section, "Publishing.py", buttons)
HIDDEN = """<INPUT TYPE='HIDDEN' NAME='%s' VALUE='%s'>\n"""

# !!! Disable standout in publish.py. !!!
cdrpub.NCGI = 0

#----------------------------------------------------------------------
# Return to the main menu if requested.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

# Initialize Display class.
# This class is not much helpful yet.
d = Display()

if fields.has_key('Session') and fields.has_key('SubSet') and \
    fields.has_key('Publish'):
    ctrlDocId = fields.getvalue('ctrlId')
    subsetName = fields.getvalue('SubSet')
    credential = fields.getvalue('Session')
    answer = fields.getvalue('Publish')

    if answer == 'No':
        d.displayDocParam(ctrlDocId, subsetName, "Redirect")
    else:        
        docs = fields.getvalue('Documents')
        docIds = None
        if docs:
            docIds = string.split(docs[1:], ",")
        parms = fields.getvalue('Parameters')
        params = None
        if parms:
            params = string.split(parms[1:], ",")
        if fields.getvalue('Email') == 'y':        
            email = fields.getvalue('EmailAddr')
        else:
            email = "Do not notify"
        if fields.getvalue('NoOutput') == 'Y':        
            no_output = "Y"
        else:
            no_output = "N"
        d.initPublish(ctrlDocId, subsetName, credential, docIds, params,
                      email, no_output)

elif fields.has_key('Session') and fields.has_key('SubSet') and \
    fields.has_key('ctrlId') and fields.has_key('DocParam'):
    ctrlId = fields.getvalue('ctrlId')
    SubSet = fields.getvalue('SubSet')
    d.displayDocParam(ctrlId, SubSet)

elif fields.has_key('Session') and fields.has_key('SubSet') \
    and fields.has_key('ctrlId') and fields.has_key('Confirm'):
    d.displayConfirm()

elif fields.has_key('Session') and fields.has_key('ctrlId'):
    ctrlId = fields.getvalue('ctrlId')
    d.displaySubsets(ctrlId)

elif fields.has_key('Session') and fields.has_key('jobId'):
    jobId = fields.getvalue('jobId')
    d.getStatus(jobId)

elif fields.has_key('Session'):    
    d.displaySystems()

else:
    cdrcgi.logout(session)
