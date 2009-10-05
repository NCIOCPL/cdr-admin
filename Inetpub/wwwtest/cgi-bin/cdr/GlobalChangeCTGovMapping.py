#----------------------------------------------------------------------
# $Id: GlobalChangeCTGovMapping.py,v 1.2 2007-10-03 04:15:47 ameyer Exp $
#
# Search CTGovProtocol documents for values that can be mapped
# using the external_map table.  Map them if any are found.
#
# Only looks for CT.gov Agency and CT.Gov Facility usages.
#
# This is the CGI portion of the program used for initiating the job,
# the actual job is performed in the background by a job initiated
# via cdrbatch.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2007/09/19 04:44:23  ameyer
# Initial version.
#
#----------------------------------------------------------------------
import cgitb; cgitb.enable()

import cgi, time, string, cdr, cdrcgi, ModifyDocs, cdrbatch

# Logfile
LF=cdr.DEFAULT_LOGDIR + "/GlobalChangeCTGovMapping.log"

# Name of job for batch_job table
JOB_NAME = "Global Change CTGov Mappings"

# Parse form variables
fields = cgi.FieldStorage()
if not fields:
    cdrcgi.bail ("Unable to load form fields - should not happen!", logfile=LF)

# Establish user session and authorization
session = cdrcgi.getSession(fields)
if not session:
    cdrcgi.bail ("Unknown or expired CDR session.", logfile=LF)

# Bailing out?
request = cdrcgi.getRequest(fields)
if request in (cdrcgi.MAINMENU, "Cancel"):
    cdrcgi.navigateTo ("Admin.py", session)
elif request == "Log Out":
    cdrcgi.logout(session)

# Running for real, or in test mode (None = bug)
runMode = None
if request == "Test":
    runMode = "test"
elif request == "Submit":
    runMode = "run"

# Authorization?
if not cdr.canDo (session, "MAKE GLOBAL CHANGES", "CTGovProtocol"):
    cdrcgi.bail (
    "Sorry, user not authorized to make global changes to CTGovProtocols",
     logfile=LF)

# Should we ask user if he's worried about other jobs running?
concurrentJobs   = cdrbatch.getJobStatusHTML(ageDays=1)
checkedOtherJobs = fields.getvalue("checkedOtherJobs") or None
if request == 'Continue' or checkedOtherJobs == "yes" or not concurrentJobs:
    checkedOtherJobs = "yes"
    headerPrompt = "Enter batch job parameters"
else:
    checkedOtherJobs = "no"
    headerPrompt = "Confirm continuation in spite of other batch jobs"

# Today's date is default end date
today = time.strftime("%Y-%m-%d", time.localtime())

# Get user input
startDate = fields.getvalue("startDate") or None
endDate   = fields.getvalue("endDate") or today
emailList = fields.getvalue("email") or None

# Check parameters
if startDate:
    startTm = cdr.strptime(startDate, "%Y-%m-%d")
    if not startTm:
        cdrcgi.bail ("Please enter start date in YYYY-MM-DD format")

    endTm = cdr.strptime(endDate, "%Y-%m-%d")
    if not endTm:
        cdrcgi.bail (
          "Please enter end date in YYYY-MM-DD or leave blank for today")

    if not emailList:
        cdrcgi.bail ("Please enter at least one email address")

    if not runMode:
        cdrcgi.bail ("BUG - Shouldn't be here unless Submit or Test clicked")

    # If we got here, we're ready to go
    args = (("startDt", startDate),
            ("endDt", endDate),
            (cdrcgi.SESSION, session),
            ("runMode", runMode))
    newJob = cdrbatch.CdrBatch(jobName=JOB_NAME,
                command="lib/Python/GlobalChangeCTGovMappingBatch.py",
                args=args,
                email=emailList)

    # Tell PublishingService we're ready
    try:
        newJob.queue()
    except Exception, e:
        cdrcgi.bail ("Batch job could not be started: " + str (e), logfile=LF)

    # Get ID to report to user
    jobId = newJob.getJobId()

    # Tell user
    title = "Global Change CTGovProtocol Mappings - Confirmation"
    html = cdrcgi.header(title, title, headerPrompt,
                         buttons=(cdrcgi.MAINMENU, "Log Out"))

    html += """
<h2>Global Change for CTGovProtocol Mappings</h2>

<p>A batch job has been queued to run the global change.  The job ID
is %d.</p>

<p>To monitor the status of the job, click this
<a href='getBatchStatus.py?Session=%s&jobId=%s'><u>link</u></a>
or go to the CDR Administration menu and select 'View Batch Job Status'.</p>
<p><p><p>
</form>
</body>
</html>
""" % (jobId, session, jobId)


    cdrcgi.sendPage(html)


#----------------------------------------------------------------------
# If parameters not present, present the form for them
#----------------------------------------------------------------------
# Generate HTML headers
title = "Global Change CTGovProtocol Mappings"
html = cdrcgi.header(title, title, headerPrompt,
                     script='GlobalChangeCTGovMapping.py',
                     buttons=(cdrcgi.MAINMENU, "Log Out"))
html += """
<h2>Global Change for CTGovProtocol Mappings</h2>

<p>Use this web page to start a batch program to search CTGovProtocol
documents for Facility/Name and/or LeadSponsor values that have not been
mapped but for which mappings exist in the external map table.  For each
document for which mappable values are found, the program will perform
standard global changes to the current working document and to last
and last publishable versions, as required, to map the values.</p>

<p>Results will be emailed to you or whoever you designate.</p>

<input type='hidden' name='%s' value='%s' />
""" % (cdrcgi.SESSION, session)

# Form for confirming continue in spite of other jobs
if checkedOtherJobs == "no":
    html +="""
<center><h3><font color='red'>Alert!</font></h3></center>

<p>One or more batch jobs may currently be running.  Please review
the list below to see what they are.  If you wish to start another
batch job anyway, please click "Continue".   Otherwise click "Cancel"</p>

<center>
%s
<p />
<input type='submit' name='%s' value="Continue" /> &nbsp;
<input type='submit' name='%s' value="Cancel" />
</center>
""" % (concurrentJobs, cdrcgi.REQUEST, cdrcgi.REQUEST)

# Form for gathering parameters
else:
    # Default email for output
    defaultEmail = None
    try:
        # Get current userid so we can get default email address
        resp = cdr.idSessionUser (None, session)
        if type(resp)==type("") or type(resp)==type(u""):
            cdrcgi.bail ("Error fetching userid for email address: %s", resp,
                         logfile=LF)

        # Get current user's email address
        usrObj = cdr.getUser (session, resp[0])
        if type(usrObj)==type("") or type(usrObj)==type(u""):
            cdrcgi.bail ("Error fetching email address: %s" % usrObj,
                         logfile=LF)
        defaultEmail = usrObj.email
    except:
        cdrcgi.bail ("Unable to fetch email address", logfile=LF)

    # Default date to start
    defaultDate = "%04d-%02d-%02d" % time.localtime()[:3]

    # Form to add to header
    html += """
<p>Please enter parameters for the job.</p>

<center>
<table>
  <tr>
    <td align='right'>
       Date as YYYY-MM-DD for oldest document change to examine:
    </td>
    <td><input type='text' name='startDate' value='%s' /></td>
  </tr>
  <tr>
    <td align='right'>
       Date as YYYY-MM-DD for newest document change to examine:
    </td>
    <td><input type='text' name='endDate' value='%s' /></td>
  </tr>
  <tr>
    <td align='right'>Email addresses, separated by spaces or commas:</td>
    <td><input type='text' name='email' value='%s' /></td>
  </tr>
</table>
<p />
<input type='submit' name='%s' value="Submit" /> &nbsp;
<input type='submit' name='%s' value="Test" /> &nbsp;
<input type='submit' name='%s' value="Cancel" />
</center>
""" % (defaultDate, today, defaultEmail, cdrcgi.REQUEST,
       cdrcgi.REQUEST, cdrcgi.REQUEST)

# This appears after either form
html += """
  </form>
 </body>
</html>
"""

# Send it
cdrcgi.sendPage(html)
