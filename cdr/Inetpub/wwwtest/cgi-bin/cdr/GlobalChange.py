#----------------------------------------------------------------------
# $Id: GlobalChange.py,v 1.11 2003-07-29 23:15:08 ameyer Exp $
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
# Revision 1.10  2003/07/29 20:05:36  ameyer
# Added support for global terminology changes.
#
# Revision 1.9  2003/03/27 18:30:50  ameyer
# Major refactoring of the program to work with a more scriptable logic
# and to handle a new, fourth type of global change.
#
# Revision 1.8  2002/11/21 14:00:42  bkline
# Fixed bug in call to cdrcgi.bail().
#
# Revision 1.7  2002/11/20 00:45:35  ameyer
# Added interface to query user for Principal Investigator if a Lead Org
# restriction is imposed.
#
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

import cgi, time, string, cdr, cdrcgi, cdrglblchg, cdrbatch

# Logfile
LF=cdr.DEFAULT_LOGDIR + "/GlobalChange.log"

# Name of job for batch_job table
JOB_NAME = "Global Change"
JOB_HTML_NAME = "Global+Change"

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
    header      = parms[0]
    formContent = parms[1]
    buttons     = None
    if len (parms) > 2:
        # Passed buttons
        buttons=parms[2]

    if buttons == None:
        # Default buttons if none (or None) passed
        buttons = (('submit', 'Submit'), ('cancel', 'Cancel'))

    # Create an overall header using the common header code
    html = cdrcgi.header ("CDR Global Change", "CDR Global Change",
                          header, "GlobalChange.py")

    # Save state in the form
    # Values are encoded to prevent quotes or other chars from
    #   causing problems in the output html
    for key in ssVars.keys():
        html += '<input type="hidden" name="%s" value="%s" />\n' %\
                (key, cgi.escape (str(ssVars[key]), 1))

    # Add form contents
    html += formContent

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

# Don't allow two global changes to run concurrently
countRunning = 0
try:
    # Gets number of active Global Change jobs
    countRunning = cdrbatch.activeCount (JOB_NAME)
except cdrbatch.BatchException, e:
    cdrcgi.bail (e)
if countRunning > 0:
    cdrcgi.bail ("""
Another global change job is still active.<br>
Please wait until it completes before starting another.<br>
See <a href='getBatchStatus.py?Session=%s&jobName=%s&jobAge=1'>
<u>Batch Status Report</u></a>
or go to the CDR Administration menu and select 'View Batch Job Status'.</p>
<p><p><p>""" % (session, JOB_HTML_NAME))

# Is user cancelling global change operations?
if fields.getvalue ("cancel", None):
    # Cancel button pressed.  Return user to admin screen
    cdrcgi.navigateTo ("Admin.py", session)

# This list contains pairs of variable name+value to be stored
#   as hidden html form variables.  Used to preserve state between
#   executions of this program.
# We always remember the session, usually other things too
ssVars = {}
ssVars[cdrcgi.SESSION] = session

# Get all relevant fields that can be saved as state in the system
# Not all of these will be present
for fd in ('docType', 'email', 'specificPhone', 'specificRole',
                'coopType', 'coopChk',
           'fromId', 'fromName', 'fromTitle', 'fromFragChk',
           'toId', 'toName', 'toTitle', 'toFragChk',
           'restrId', 'restrName', 'restrTitle', 'restrChk', 'restrFragChk',
           'restrPiId', 'restrPiName', 'restrPiTitle',
                'restrPiChk', 'restrPiFragChk',
           'insertPersId', 'insertPersName', 'insertPersTitle',
                'insertPersFragChk',
           'insertOrgId', 'insertOrgName', 'insertOrgTitle',
           'fromStatusName', 'toStatusName',
           'trmReqField0', 'trmReqVal0', 'termReqId0',
           'trmReqField1', 'trmReqVal1', 'termReqId1',
           'trmReqField2', 'trmReqVal2', 'termReqId2',
           'trmReqField3', 'trmReqVal3', 'termReqId3',
           'trmReqField4', 'trmReqVal4', 'termReqId4',
           'trmOptField0', 'trmOptVal0', 'termOptId0',
           'trmOptField1', 'trmOptVal1', 'termOptId1',
           'trmOptField2', 'trmOptVal2', 'termOptId2',
           'trmOptField3', 'trmOptVal3', 'termOptId3',
           'trmOptField4', 'trmOptVal4', 'termOptId4',
           'trmNotField0', 'trmNotVal0', 'termNotId0',
           'trmNotField1', 'trmNotVal1', 'termNotId1',
           'trmNotField2', 'trmNotVal2', 'termNotId2',
           'trmNotField3', 'trmNotVal3', 'termNotId3',
           'trmNotField4', 'trmNotVal4', 'termNotId4',
           'trmDelField0', 'trmDelVal0', 'termDelId0',
           'trmDelField1', 'trmDelVal1', 'termDelId1',
           'trmAddField0', 'trmAddVal0', 'termAddId0',
           'trmAddField1', 'trmAddVal1', 'termAddId1'):
    fdVal = fields.getvalue (fd, None)
    if fdVal:
        # If it's an Id type, normalize it to standard CDR000... form
        # Warning, only CDR IDs should have names ending in "Id"
        if fd[-2:] == "Id":
            try:
                fdVal = cdr.exNormalize (fdVal)[0]
            except StandardError, e:
                cdrcgi.bail ("Error normalizing id: %s: %s" % \
                             (str(fdVal), str(e)))

        # Store it in our state container
        ssVars[fd] = fdVal
        cdr.logwrite("   Saving '%s'='%s'" % (fd, ssVars[fd]), LF)

# What kind of change are we doing?
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
  Change person links in protocols</input>
</td></tr><tr><td>
<input type='radio' name='chgType' value='%s'>
  Change organization links in protocols</input>
</td></tr><tr><td>
<input type='radio' name='chgType' value='%s'>
  Insert new organization link in protocols</input>
</td></tr><tr><td>
<input type='radio' name='chgType' value='%s'>
  Modify terminology in protocols</input>
</td></tr><tr><td>
<input type='radio' name='chgType' value='%s'>
  Change status of protocol site</input>
</td></tr>
</table>
""" % (cdrglblchg.PERSON_CHG, cdrglblchg.ORG_CHG,
       cdrglblchg.INS_ORG_CHG, cdrglblchg.TERM_CHG,
       cdrglblchg.STATUS_CHG)

    sendGlblChgPage (("Choose type of change to perform", html))

#----------------------------------------------------------------------
# Construct an object of the proper type of global change
#----------------------------------------------------------------------
ssVars["chgType"] = chgType

try:
    chg = cdrglblchg.createChg (ssVars)
except Exception, e:
    cdrcgi.bail ("Error constructing chg object: %s" % str(e))

#----------------------------------------------------------------------
#                               Main loop
#----------------------------------------------------------------------

# We've got everything we need to start all the steps for one
# type of global change.
# We know:
#   All of the variables entered so far: (ssVars)
#   What kind of change we're doing: (ssVars['chgType'])
#   Everything specific for this type of change: (chg)
# Now we execute each stage in the global change.
for stage in chg.getStages():

    # For DEBUG, log something
    cdr.logwrite ("Main loop: " + stage.getExcpMsg(), LF)

    # Execute the stage
    # It will tell us if we need to go on or stop and talk to the user
    # It may not actually execute anything at all, just evaluate its
    #   condition and decide that no further processing is required in
    #   this stage.  After each user interaction the ssVars state will
    #   change so that work already done is passed over and we eventually
    #   get to something that needs doing, or we finish.
    result = chg.execStage (stage)

    # Was there an error?
    rc = result.getRetType()
    if rc == cdrglblchg.RET_ERROR:
        # Log it
        cdr.logwrite ("Main loop error: " + result.getErrMsg(), LF)

        # Tell user and abort.  User must press Back, or something to go on
        cdrcgi.bail (result.getErrMsg())

    # Display HTML?
    if rc == cdrglblchg.RET_HTML:
        # Send page to user and exit
        # User fills something in and comes back when he's ready
        sendGlblChgPage ((result.getPageTitle(),
                          result.getPageHtml(),
                          result.getPageButtons()))

    # Sanity check
    if rc != cdrglblchg.RET_NONE:
        cdrcgi.bail ("%s: Internal error, retType=[%s]" % \
                     (stage.getExcpMsg(), str(result.getRetType)))

#----------------------------------------------------------------------
# Give user final review
#   If we finish the for loop it means we've got all the chgType
#   specific info we need to do the actual work
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
            cdrcgi.bail ("Error fetching email address: %s" % usrObj)
        email = usrObj.email
    except:
        cdrcgi.bail ("Unable to fetch email address")

    result = chg.reportWillChange()
    if result.getRetType() == cdrglblchg.RET_ERROR:
        cdrcgi.bail ("Error creating change report: " + result.getErrMsg())

    if result.getRetType() == cdrglblchg.RET_NONE:
        sendGlblChgPage (("No documents found", chg.showSoFarHtml() +
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

        html = chg.showSoFarHtml() + instruct + result.getPageHtml()

        sendGlblChgPage (("Final review", html))

# If user pressed Cancel, we never got here
ssVars['email'] = email

#----------------------------------------------------------------------
# Invoke the batch process to complete the actual processing
#----------------------------------------------------------------------
# Convert all session info to a sequence of batch job args
args = []
for var in ssVars.keys():
    args.append ((var, ssVars[var]))

# Create batch job
newJob = cdrbatch.CdrBatch (jobName=JOB_NAME,
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
