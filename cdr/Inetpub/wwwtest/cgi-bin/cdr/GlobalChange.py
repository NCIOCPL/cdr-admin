#----------------------------------------------------------------------
# $Id: GlobalChange.py,v 1.2 2002-08-02 03:33:48 ameyer Exp $
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

try:
    chg = cdrglblchg.createChg (sessionVars)
except cdrbatch.BatchException, be:
    cdrcgi.bail (str(be))

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
    except cdrbatch.BatchException, be:
        cdrcgi.bail (str(be))

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
    try:
        sendGlblChgPage (chg.genFragPickListHtml('from'))
    except cdrbatch.BatchException, be:
        cdrcgi.bail (str(be))


#----------------------------------------------------------------------
# Change to what? - just like change from
#----------------------------------------------------------------------
toId    = fields.getvalue ("toId", None)
toTitle = fields.getvalue ("toTitle", None)
if toId and not toTitle:
    try:
        toTitle = cdrglblchg.verifyId (toId, sessionVars['docType'])
    except cdrbatch.BatchException, be:
        cdrcgi.bail (str(be))

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
    try:
        sendGlblChgPage (chg.genFragPickListHtml('to'))
    except cdrbatch.BatchException, be:
        cdrcgi.bail (str(be))


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
# Give user final review
#----------------------------------------------------------------------
# If review already done, we already have an email address
email = fields.getvalue ('email', None)
if not email:
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
 <li>Fill in an email address for results and click 'Submit', or</li>
 <li>Click 'Cancel' to return to the administration menu</li>
</ol>
<p><p>
<p>Email address: <input type='text' name='email' size='50' /></p>
<p><p><p>
"""
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
    cdr.logwrite ((str(type(var)), str(type(sessionVars[var]))))

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
