#----------------------------------------------------------------------
# $Id: GlobalChange.py,v 1.1 2002-07-25 15:50:11 ameyer Exp $
#
# Perform global changes on XML records in the database.
#
# Performs one of three types of global change:
#   Person link changes in protocols.
#   Organization link changes in protocols.
#   Protocol status.
#
# This program functions as both the creator and reader of multiple
# CGI forms.  It progresses through multiple screens, gathering
# information on each one until is has the information it needs to
# present the next one - to the end.
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------

import cgi, cdr, cdrcgi, cdrglblchg, cdrbatch, time

# Logfile
LF=cdr.DEFAULT_LOGDIR + "/GlobalChange.log"

#----------------------------------------------------------------------
# Generate a page in uniform style for form
#----------------------------------------------------------------------
def sendGlblChgPage (parms):

    """
    Generate an HTML page in our standard style with all saved
    state information, buttons, etc.

    This routine calls cdrcgi.sendPage to send the page to the
    browser and exit.  There is no return.

    Pass:
        Tuple of:
            Header to appear on Cdr Admin banner.
            Contents of form, as html
            Optional button values as tuple of:
                Tuples of:
                    button name
                    button value
                or None
    """
    # Passed parameters
    header = parms[0]
    formContent = parms[1]
    if len (parms) > 2:
        buttons=parms[2]
    else:
        buttons = None

    # Create an overall header using the common header code
    html = cdrcgi.header ("CDR Global Change", "CDR Global Change",
                          header, "GlobalChange.py")

    # Save state in the form
    for key in sessionVars.keys():
        html += "<input type='hidden' name='%s' value='%s' />\n" %\
                (key, sessionVars[key])

    # Add form contents
    html += formContent

    # Construct default buttons
    if not buttons:
        buttons = (('submit', 'Submit'), ('cancel', 'Cancel'))

    # Button table
    html += "<p><p><table border='0' align='center'>\n <tr>\n"
    for btn in buttons:
        html += "  <td><input type='submit' name='" + \
                btn[0] + "' value='" + btn[1] + "' /></td>\n"
    html += " </tr></table>\n"

    # Form termination
    html += "</form>\n</body>\n</html>\n"

    cdrcgi.sendPage (html)


#----------------------------------------------------------------------
# Log an error and return message suitable for display
#----------------------------------------------------------------------
def logErr (docId, where, msg):
    """
    Write a message to the log file and return it.

    Pass:
        Doc id  - Document id (numeric form).
        where   - Where it happened
        msg     - Error message.

    Return:
        Error message suitable for display.
    """
    # If the error message is in XML, extract error portion from it
    msg = cdr.getErrors (msg)

    # Put it together for log file
    cdr.logwrite (("Error on doc %d %s:" % (docId, where), msg), LF)

    # Different format for HTML report to user
    return ("Error %s:<br>%s" % (where, msg))


##----------------------------------------------------------------------
##----------------------------------------------------------------------
## START OF MAIN
##----------------------------------------------------------------------
##----------------------------------------------------------------------
# Parse form variables
fields = cgi.FieldStorage()
if not fields:
    cdrcgi.bail ("Unable to load form fields - should not happen!")

# Establish user session and authorization
session = cdrcgi.getSession(fields)
if not session:
    cdrcgi.bail ("Unknown or expired CDR session.")
if not cdr.canDo (session, "MAKE GLOBAL CHANGES", "InScopeProtocol"):
    cdrcgi.bail ("Sorry, user not authorized to make global changes")

# Is user cancelling global change operations?
if fields.getvalue ("cancel", None):
    # Cancel button pressed.  Return user to admin screen
    cdrcgi.navigateTo ("Admin.py", session)

# This list contains pairs of variable name+value to be stored
#   as hidden html form variables.  Used to preserve state between
#   executions of this program.
# We always remember the session, usually other things too
sessionVars = {}
sessionVars[cdrcgi.SESSION] = session

# Are we doing a person, organization, or protocol status change?
# May or may not know this at this time
chgType = fields.getvalue ("chgType", None)

#----------------------------------------------------------------------
# Initial choice of type of global change
#----------------------------------------------------------------------
if not chgType:
    html = """
<table border='0'>
<tr><td>
<input type='radio' name='chgType' value='%s' checked='1'>
  Person links in protocols</input>
</td></tr><tr><td>
<input type='radio' name='chgType' value='%s'>
  Organization links in protocols</input>
</td></tr><tr><td>
<input type='radio' name='chgType' value='%s'>
  Protocol status</input>
</td></tr>
</table>
""" % (cdrglblchg.PERSON_CHG, cdrglblchg.ORG_CHG, cdrglblchg.STATUS_CHG)

    sendGlblChgPage (("Choose type of change to perform", html))

#----------------------------------------------------------------------
# Construct an object of the proper type of global change
#----------------------------------------------------------------------
sessionVars["chgType"] = chgType
chg = cdrglblchg.createChg (sessionVars)

#----------------------------------------------------------------------
# Change from what?
#----------------------------------------------------------------------
fromId    = fields.getvalue ("fromId", None)
fromTitle = fields.getvalue ("fromTitle", None)

# If found, verify title and doctype.  Bails out if doctype is wrong.
if fromId and not fromTitle:
    fromTitle = cdrglblchg.verifyId (fromId, sessionVars['docType'])

# If no id present, there may be a name, or partial name
if not fromId:
    fromName = fields.getvalue ("fromName", None)
    if not fromName:
        # User hasn't entered any "from" information yet
        # Put form up to get id or name
        # Different types of chg object construct slightly
        #   different html for this
        sendGlblChgPage (chg.getFromId())
    else:
        # We got a name (from previous sendGlblChg) but user hasn't yet
        #   picked a definite hit from a picklist generated from the name
        # That's why we don't have an id yet
        # Get the picklist
        sendGlblChgPage (chg.getFromPick (fromName))

# We have an id, get the parts
(fromId, fromIdNum, fromFragment) = cdr.exNormalize (fromId)

# Save for future use
sessionVars['fromId'] = fromId
sessionVars['fromTitle'] = fromTitle


#----------------------------------------------------------------------
# Get fragment if not already supplied
#----------------------------------------------------------------------
if not fromFragment and (chgType == cdrglblchg.PERSON_CHG or
                         chgType == cdrglblchg.ORG_CHG):
    sendGlblChgPage (chg.genFragPickListHtml('from'))


#----------------------------------------------------------------------
# Change to what? - just like change from
#----------------------------------------------------------------------
toId    = fields.getvalue ("toId", None)
toTitle = fields.getvalue ("toTitle", None)
if toId and not toTitle:
    toTitle = cdrglblchg.verifyId (toId, sessionVars['docType'])

if not toId:

    toName = fields.getvalue ("toName", None)
    if not toName:
        sendGlblChgPage (chg.getToId())

    else:
        sendGlblChgPage (chg.getToPick (toName))

(toId, toIdNum, toFragment) = cdr.exNormalize (toId)
sessionVars['toId'] = cdr.exNormalize(toId)[0]
sessionVars['toTitle'] = toTitle


#----------------------------------------------------------------------
# Get fragment if not already supplied
#----------------------------------------------------------------------
if not toFragment and (chgType == cdrglblchg.PERSON_CHG or
                         chgType == cdrglblchg.ORG_CHG):
    sendGlblChgPage (chg.genFragPickListHtml('to'))


#----------------------------------------------------------------------
# Get any restrictions on protocols to be processed
#----------------------------------------------------------------------
if chgType != cdrglblchg.STATUS_CHG:

    # Has user chosen whether or not to restrict ids?
    restrByLeadOrgChk = fields.getvalue ('restrByLeadOrgChk', None)
    if not restrByLeadOrgChk:
        # Haven't chosen yet.  Choose
        sendGlblChgPage (chg.getRestrId())

    # Don't check again
    sessionVars['restrByLeadOrgChk'] = 'N'

    # Input is optional on this form, if no input, then no restriction
    # Did user input an organization ID?
    restrId = fields.getvalue ('restrId', None)
    if not restrId:
        # No, perhaps he entered a name
        restrName = fields.getvalue ("restrName", None)
        if restrName:
            # Choose matching organization for name
            sendGlblChgPage (chg.getRestrPick (restrName))

    else:
        sessionVars['restrId'] = cdr.exNormalize(restrId)[0]


#----------------------------------------------------------------------
# Select the protocols to change
#----------------------------------------------------------------------
okToRun = fields.getvalue ('okToRun', None)
if not okToRun:
    html = chg.reportWillChange()
    if not html:
        sendGlblChgPage (("",
            "<h2>No documents found matching global search criteria<h2>\n",
            (('cancel', 'Done'),)))
    else:
        html = chg.showSoFarHtml() + \
               "<p>The following protocols will be modified<br>\n" + \
               "Please review and Submit or Cancel</p>\n" + html

        sendGlblChgPage (("Final review", html))

# If user pressed Cancel, we never got here
sessionVars['okToRun'] = okToRun

#----------------------------------------------------------------------
# Perform the global change
#----------------------------------------------------------------------

# We'll store up to 3 versions of the doc
oldCwdXml = None    # Original current working document
chgCwdXml = None    # Transformed CWD
chgPubVerXml = None # Transformed version of last pub version

# We'll build two lists of docs to report
# Documents successfully changed, id + title tuples
changedDocs = [("<b>CDR ID</b>", "<b>Title</b>")]

# Couldn't be changed, id + title + error text
failedDocs  = [("<b>CDR ID</b>", "<b>Title</b>", "<b>Reason</b>")]

# Get the list of documents - different for each type of change
# Gets list of tuples of id + title
cdr.logwrite ("Selecting docs for final processing", LF)
originalDocs = chg.selDocs()
cdr.logwrite ("Done selecting docs for final processing", LF)
cdr.logwrite ("Processing %d docs, changing %s to %s" % \
              (len(originalDocs), fromId, toId), LF)

# Process each one
for idTitle in originalDocs:

    docId    = idTitle[0]
    title    = idTitle[1]
    docIdStr = cdr.exNormalize(docId)[0]

    # No problems yet
    failed     = None
    checkedOut = 0

    # Attempt to check it out, getting a Doc object (in cdr.py)
    cdr.logwrite ("Fetching doc %d for final processing" % docId, LF)
    oldCwdDocObj = cdr.getDoc (session, docId=docId, checkout='Y',
                               version='Current', getObject=1)
    cdr.logwrite ("Finished fetch of doc %d for final processing" % docId, LF)

    # Got a Doc object, or a string of errors
    if type (oldCwdDocObj) == type (""):
        failed = logErr (docId, "checking out document", oldCwdDocObj)
    else:
        oldCwdXml = oldCwdDocObj.xml

    # Filter current working document
    # XXXX Check that Volker uses these same variables in all scripts
    parms = [['changeFrom', fromId], ['changeTo', toId]]

    if not failed:
        # We need to check this back in at end
        checkedOut = 1

        # Get version info
        cdr.logwrite ("Checking lastVersions", LF)
        result = cdr.lastVersions (session, docIdStr)
        cdr.logwrite ("Finished checking lastVersions", LF)
        if type (result) == type ("") or type (result) == (u""):
            failed = logErr (docId, "fetching last version information",result)
        else:
            (lastVerNum, lastPubVerNum, isChanged) = result

            # Filter doc to get new, changed CWD
            cdr.logwrite ("Filtering doc", LF)
            filtResp = cdr.filterDoc (session, filter=chg.chgFilter, parm=parms,
                                      docId=docId, docVer=None)

            if type(filtResp) != type(()):
                failed = logErr (docId, "filtering CWD", filtResp)
            else:
                # Get document, ignore messages (filtResp[1])
                chgCwdXml = filtResp[0]
            cdr.logwrite ("Finished filtering doc", LF)

    if not failed:
        # If there was a publishable version, and
        # It's different from the CWD,
        #   Filter the last publishable version too
        if (lastVerNum == lastPubVerNum and isChanged):

            cdr.logwrite ("Filtering last version", LF)
            filtResp = cdr.filterDoc (session, filter=chg.chgFilter,
                                      parm=parms, docId=docId,
                                      docVer=lastPubVerNum)
            if type(filtResp) != type(()):
                failed = logErr (docId, "filtering last publishable version",
                                 filtResp)
            else:
                chgPubVerXml = filtResp[0]
            cdr.logwrite ("Finished filtering last version", LF)

    if not failed:
        # For debug
        # willDo = ""
        # if isChanged:
        #     willDo = "<h1>Saved old working copy:</h1>" + oldCwdXml
        # if chgPubVerXml:
        #     willDo += "<h1>Changed published version:</h1>" + chgPubVerXml
        # willDo += "<h1>New CWD version:</h1>" + chgCwdXml
        # cdrcgi.bail (willDo)

        # Store documents in the following order:
        #    CWD before filtering - if it's not the same as last version
        #    Filtered publishable version, if there is one
        #    Filtered CWD
        if isChanged:
            cdr.logwrite ("Saving copy of working doc before change", LF)
            repDocResp = cdr.repDoc (session, doc=str(oldCwdDocObj), ver='Y',
                checkIn='N', verPublishable='N',
                reason="Copy of working document from before global change "
                       "of %s to %s at %s" % (fromId, toId,
                                              time.ctime (time.time())))
            if repDocResp.startswith ("<Errors"):
                failed = logErr (docId,
                         "attempting to create version of pre-change doc",
                         repDocResp)
                cdr.logwrite (("Creating pre-change doc", "Original CWD:",
                               oldCwdXml, "================"), LF)
            cdr.logwrite ("Finished saving copy of working doc before change",
                           LF)

    if not failed:
        # If new publishable version was created, store it
        if chgPubVerXml:
            chgPubVerDocObj = cdr.Doc(id=docId, type='InScopeProtocol',
                                      x=chgPubVerXml)
            repDocResp = cdr.repDoc (session, doc=str(chgPubVerDocObj),
                ver='Y', checkIn='N', verPublishable='Y',
                reason="Last publishable version, revised by global change "
                       "of %s to %s at %s" % (fromId, toId,
                                              time.ctime (time.time())))
            if repDocResp.startswith ("<Errors"):
                failed = logErr (docId,
                  "attempting to store last publishable version after change",
                  + repDocResp)

    if not failed:
        # Finally, the working document
        chgCwdDocObj = cdr.Doc(id=docIdStr, type='InScopeProtocol',
                               x=chgCwdXml)
        cdr.logwrite ("Saving CWD after change", LF)
        repDocResp = cdr.repDoc (session, doc=str(chgCwdDocObj), ver='N',
            checkIn='Y',
            reason="Revised by global change "
                   "of %s to %s at %s" % (fromId, toId,
                                          time.ctime (time.time())))
        if repDocResp.startswith ("<Errors"):
            failed = logErr (docId, "attempting to store changed CWD",
                             repDocResp)

        else:
            # Replace was successful.  Document checked in
            checkedOut = 0
        cdr.logwrite ("Finished saving CWD after change", LF)

    # If we did not complete all the way to check-in, have to unlock doc
    if checkedOut:
        cdr.unlock (session, docId)

    # If successful, add this document to the list of sucesses
    if not failed:
        changedDocs.append ((docId, title))
    else:
        failedDocs.append ((docId, title, failed))

# Final report
html = "<h2>Please print this report now if you need a permanent copy</h2>\n"
if len (failedDocs) > 1:
    html += \
    "<h2>Documents that could <font color='red'>NOT</font> be changed</h2>\n"+\
    cdrcgi.tabularize (failedDocs, "border='1' align='center'")

if len (changedDocs) > 1:
    html += "<h2>Documents successfully changed</h2>\n" +\
           cdrcgi.tabularize (changedDocs, "border='1' align='center'")

sendGlblChgPage (("Global Change Completion Report",html,(("cancel","Done"),)))
