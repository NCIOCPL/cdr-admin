#----------------------------------------------------------------------
# $Id: GlobalChange.py,v 1.7 2002-11-20 00:45:35 ameyer Exp $
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
# Revision 1.6  2002/11/13 02:39:07  ameyer
# Added support for multiple email addresses.
#
# Revision 1.5  2002/09/24 23:40:00  ameyer
# Fix cgi escape for attribute values with quote marks.
# Discovered by Bob.
#
# Revision 1.4  2002/08/27 22:45:40  ameyer
# Now allowing user to enter organization ids with or without address
# fragments.
#
# Revision 1.3  2002/08/09 03:49:15  ameyer
# Changes for organization status protocol global change.
# Some small cosmetic changes.
# Needs some work on sendGlblChgPage.  See commented out except clause.
#
# Revision 1.2  2002/08/02 03:33:48  ameyer
# First fully working version.  Needs more test and have to add 3rd type
# of global change.
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
    # Values are encoded to prevent quotes or other chars from
    #   causing problems in the output html
    for key in sessionVars.keys():
        html += '<input type="hidden" name="%s" value="%s" />\n' %\
                (key, cgi.escape (sessionVars[key], 1))

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
  Status of protocol site</input>
</td></tr>
</table>
""" % (cdrglblchg.PERSON_CHG, cdrglblchg.ORG_CHG, cdrglblchg.STATUS_CHG)

    sendGlblChgPage (("Choose type of change to perform", html))

#----------------------------------------------------------------------
# Construct an object of the proper type of global change
#----------------------------------------------------------------------
sessionVars["chgType"] = chgType

try:
    chg = cdrglblchg.createChg (sessionVars)
except Exception, e:
    cdrcgi.bail ("Error constructing chg object: %s" % str(e))

#----------------------------------------------------------------------
# Change from what?
#----------------------------------------------------------------------
fromId    = fields.getvalue ("fromId", None)
fromTitle = fields.getvalue ("fromTitle", None)

# If found, verify title and doctype.
# Bails out if doctype is wrong or id format won't parse
if fromId and not fromTitle:
    try:
        fromTitle = cdrglblchg.verifyId (fromId, sessionVars['docType'])
    except Exception, e:
        cdrcgi.bail ("Error verifying from ID: %s" % str(e))

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
# Did we already ask for a from fragment?  If not, we will
didFromFrag = fields.getvalue ("didFromFrag", None)
sessionVars['didFromFrag'] = 'Y'

# We prompt for a fragment id under the following circumstances:
#   Don't already have one
#   This is a person global change (from fragment is required).
#   This is an org change (from fragment is optional) and we haven't
#     already asked for a fragment
if not fromFragment and (chgType == cdrglblchg.PERSON_CHG or
                         (chgType == cdrglblchg.ORG_CHG and not didFromFrag)):
    try:
        sendGlblChgPage (chg.genFragPickListHtml('from'))
    except cdrbatch.BatchException, e:
        cdrcgi.bail ("Error generating FROM fragment picklist: %s" % str(e))


#----------------------------------------------------------------------
# Change to what? - just like change from
#----------------------------------------------------------------------
# Not needed for status change
if chgType == cdrglblchg.PERSON_CHG or chgType == cdrglblchg.ORG_CHG:
    toId    = fields.getvalue ("toId", None)
    toTitle = fields.getvalue ("toTitle", None)
    if toId and not toTitle:
        try:
            toTitle = cdrglblchg.verifyId (toId, sessionVars['docType'])
        except cdrbatch.BatchException, e:
            cdrcgi.bail ("Error verifying TO id: %s" % str(e))

    if not toId:

        toName = fields.getvalue ("toName", None)
        if not toName:
            sendGlblChgPage (chg.getToId())

        else:
            sendGlblChgPage (chg.getToPick (toName))

    (toId, toIdNum, toFragment) = cdr.exNormalize (toId)
    sessionVars['toId'] = cdr.exNormalize(toId)[0]
    sessionVars['toTitle'] = toTitle

    #------------------------------------------------------------------
    # Get fragment if not already supplied
    #------------------------------------------------------------------
    # See comments on didFromFrag
    didToFrag = fields.getvalue ("didToFrag", None)
    sessionVars['didToFrag'] = 'Y'
    if not toFragment and (chgType == cdrglblchg.PERSON_CHG or not didToFrag):
        try:
            sendGlblChgPage (chg.genFragPickListHtml('to'))
        except cdrbatch.BatchException, e:
            cdrcgi.bail ("Error generating TO fragment picklist: %s" % str(e))


#----------------------------------------------------------------------
# For status change only, get to/from status
#----------------------------------------------------------------------
if chgType == cdrglblchg.STATUS_CHG:
    fromStatusName = fields.getvalue ('fromStatusName', None)
    toStatusName   = fields.getvalue ('toStatusName', None)

    if not fromStatusName or not toStatusName:
        # try:
        sendGlblChgPage (chg.getFromToStatus())
        # except cdrbatch.BatchException, e:
        #    cdrcgi.bail ("Error getting status picklist: %s" % str(e))

    sessionVars['fromStatusName'] = fromStatusName
    sessionVars['toStatusName']   = toStatusName


#----------------------------------------------------------------------
# Get any restrictions on protocols to be processed
#----------------------------------------------------------------------
# Has user chosen whether or not to restrict ids?
restrByLeadOrgChk = fields.getvalue ('restrByLeadOrgChk', None)
if not restrByLeadOrgChk:
    # Haven't chosen yet.  Choose
    sendGlblChgPage (chg.getRestrId())

# Don't check again
sessionVars['restrByLeadOrgChk'] = 'N'

# Input is optional on this form, if no input, then no restriction
# Did user input an organization ID?
restrId    = fields.getvalue ('restrId', None)
restrTitle = fields.getvalue ('restrTitle', None)
if not restrId:
    # No, perhaps he entered a name
    restrName = fields.getvalue ('restrName', None)
    if restrName:
        # Choose matching organization for name
        sendGlblChgPage (chg.getRestrPick (restrName))

else:
    sessionVars['restrId'] = cdr.exNormalize(restrId)[0]
    if not restrTitle:
        try:
            restrTitle = cdrglblchg.verifyId (restrId, 'Organization')
        except cdrbatch.BatchException, e:
            cdrcgi.bail ("Error verifying restriction id: %s" % str(e))
    sessionVars['restrTitle'] = restrTitle

#----------------------------------------------------------------------
# Get optional restrictions on Principal Investigator involved in a
#   status change - only when also restricting by lead organization
#----------------------------------------------------------------------
restrByPiChk = fields.getvalue ('restrByPiChk', None)
restrPiId    = fields.getvalue ('restrPiId', None)
restrPiTitle = fields.getvalue ("restrPiTitle", None)
restrPiName  = fields.getvalue ('restrPiName', None)
if chgType == cdrglblchg.STATUS_CHG and restrId:
    # It's optional, only ask if we haven't already
    if not restrByPiChk:
        # Don't check again
        sessionVars['restrByPiChk'] = 'N'
        sendGlblChgPage (chg.getRestrPiId())

    # Need to do this here too
    sessionVars['restrByPiChk'] = 'N'

    # If user entered name instead of ID, translate it
    if restrPiName and not restrPiId:
        # Choose matching person ID for name
        sendGlblChgPage (chg.getRestrPiPick (restrPiName))

    # If we got an id, verify that it's for a person
    if restrPiId:
        if not restrPiTitle:
            try:
                restrPiTitle = cdrglblchg.verifyId (restrPiId, 'Person')
            except cdrbatch.BatchException, e:
                cdrcgi.bail ("Error verifying Principal Investigator id: %s"\
                             % str(e))
        # Save the Principal Investigator id and display title
        sessionVars['restrPiTitle'] = restrPiTitle
        sessionVars['restrPiId'] = cdr.exNormalize(restrPiId)[0]

#----------------------------------------------------------------------
# Give user final review
#----------------------------------------------------------------------
# If review already done, we already have one or more email addresses
email = fields.getvalue ('email', None)
if not email:
    try:
        # Get current userid so we can get default email address
        resp = cdr.idSessionUser (None, session)
        if type(resp)==type("") or type(resp)==type(u""):
            cdrcgi.bail ("Error fetching userid for email address: %s", resp)

        # Get current user's email address
        usrObj = cdr.getUser (session, resp[0])
        if type(usrObj)==type("") or type(usrObj)==type(u""):
            cdrcgi.bail ("Error fetching email address: %s", resp)
        email = usrObj.email
    except:
        cdrcgi.bail ("Unable to fetch email address")

    report = chg.reportWillChange()
    if not report:
        sendGlblChgPage (("",
            "<h2>No documents found matching global search criteria<h2>\n",
            (('cancel', 'Done'),)))
    else:
        instruct = """
<p>A background job will be created to perform the global change.
Results of the job will be emailed.</p>
<p>To start the job, review the list of protocols to be modified and
either:</p>
<ol>
 <li>Enter one or more email addresses for results (separated by
     space, comma or semicolon) and click 'Submit', or</li>
 <li>Click 'Cancel' to return to the administration menu</li>
</ol>
<p><p>
<p>Email(s): <input type='text' name='email' value='%s' size='80' /></p>
<p><p><p>
""" % email

        html = chg.showSoFarHtml() + instruct + report

        sendGlblChgPage (("Final review", html))

# If user pressed Cancel, we never got here
sessionVars['email'] = email

#----------------------------------------------------------------------
# Invoke the batch process to complete the actual processing
#----------------------------------------------------------------------
# Convert all session info to a sequence of batch job args
args = []
for var in sessionVars.keys():
    args.append ((var, sessionVars[var]))

# Create batch job
newJob = cdrbatch.CdrBatch (jobName="Global Change",
                            command="lib/Python/GlobalChangeBatch.py",
                            args=args,
                            email=email)

# Queue it for background processing
try:
    newJob.queue()
except Exception, e:
    cdrcgi.bail ("Batch job could not be started: " + str (e))

# Get an id user can use to find out what happened
jobId = newJob.getJobId()

# Tell user how to find the results
html = """
<h4>Global change has been queued for background processing</h4>
<p>To monitor the status of the job, click this
<a href='getBatchStatus.py?Session=%s&jobId=%s'><u>link</u></a>
or go to the CDR Administration menu and select 'View Batch Job Status'.</p>
<p><p><p>""" % (session, jobId)

sendGlblChgPage (("Background job queued", html, (('cancel', 'Done'),)))
