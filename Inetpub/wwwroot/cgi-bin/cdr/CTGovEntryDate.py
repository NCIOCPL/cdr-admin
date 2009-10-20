#----------------------------------------------------------------------
#
# Interactive portion of report on differences between current
# publishable versions of CTGovProtocol documents and the first
# publishable version with the same EntryDate.
#
# Gathers parameters and launches CTGovEntryDateBatch.py
#
# $Id$
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------

import sys, cgi, cdr, cdrcgi, cdrbatch
import cgitb
cgitb.enable()

# Read submitted form, if there is one
fields   = cgi.FieldStorage()
emails   = fields and fields.getvalue("emailList") or None
format   = fields and fields.getvalue("diffFmt") or None

JOB_NAME = "CTGovEntryDateReport"
LF       = cdr.DEFAULT_LOGDIR + "/CTGovEntryDate.log"
TITLE    = "CTGovProtocol EntryDate Report"

# User logged in?
session = cdrcgi.getSession(fields)
if not session:
    cdrcgi.bail("Unknown or expired CDR session", logfile=LF)

# Requesting a different page?
request = cdrcgi.getRequest(fields)
if request == cdrcgi.mainMenu or fields.getvalue("cancel", None):
    cdrcgi.navigateTo("Admin.py", session)
elif request == "Report Menu":
    cdrcgi.navigateTo("Reports.py", session)
elif request == "Log Out":
    cdrcgi.logout(session)

# Only one job of this type allowed at a time
if cdrbatch.activeCount(JOB_NAME) > 0:
    cdrcgi.bail("Another job of this type seems to be running. Please wait.",
                logfile=LF)

# If we don't have a full form submission, put up the form
if not (emails and format):

    # Get user's email address
    usrEmail = None
    try:
        # Get current userid so we can get default email address
        resp = cdr.idSessionUser (None, session)
        if type(resp) in (type(""), type(u"")):
            cdrcgi.bail ("Error fetching session for email address: %s", resp,
                         logfile=LF)

        # Get current user's email address
        usrObj = cdr.getUser (session, resp[0])
        if type(usrObj) in (type(""), type(u"")):
            cdrcgi.bail ("Error fetching user object for session: %s" % usrObj,
                         logfile=LF)
        usrEmail = usrObj.email
    except Exception, info:
        cdrcgi.bail ("Unable to fetch email address: %s" % info, logfile=LF)
    except:
        cdrcgi.bail ("Unknown error fetching email address", logfile=LF)

    # Standard header style
    instr   = "Launch CTGovProtocol EntryDate diff report"
    buttons = ["Submit Request", "Report Menu", cdrcgi.MAINMENU, "Log Out"]
    script  = "CTGovEntryDate.py"
    html    = cdrcgi.header(TITLE, TITLE, instr, script, buttons)

    html += """
<h2>%s</h2>

<p>Use this screen to launch a batch program to compare
the latest publishable versions of all CTGovProtocols to
the earliest version of those protocols that had the same
PDQIndexing/EntryDate.</p>

<p>To prevent two users from inadvertently overwriting each
other's reports, and to avoid bogging down the machine, only
one batch report of this type is allowed to run at one time.
A user must wait for it to finish before attempting another
run.  (If you have waited more than two hours and know no
one else is running the report - check with support staff.)</p>

<p>The report itself is saved on the server.  When it is
ready, an email will be sent to all listed email addresses (see
below) informing them that the job has completed and giving
them a link to click to see the report.  The email will not
contain the report itself (which may be very large), only
a link to the report.</p>

<p>Up to two versions of the report are saved - the version we
will generate now, and the last version generated when this
program was previously run.  The email sent to users will
provide links to both versions.  Both versions are kept
permanently online and may be reviewed at any later time,
until they are overwritten by subsequent runs of this program.</p>

<p>Many, many documents and document versions are filtered
and examined to produce the report.  It typically requires
an hour or so to complete.</p>
<input type='hidden' name='Session' value='%s' />
<p />
<p />
<table border='0' width='75%%' align='center'>
 <tr>
  <th align='right'>Email address(es) separated by space or comma</th>
  <td><textarea name='emailList' rows='3' cols='30'>%s</textarea>
 </tr>
 <tr>
  <th colspan='2'>&nbsp;</th>
 </tr>
 <tr>
  <th align='right'>Output results in composite format</th>
  <td><input type='radio' name='diffFmt' value='XDiff' checked='checked' /></td>
 </tr>
 <tr>
  <th align='right'>Output results in UNIX diff format</th>
  <td><input type='radio' name='diffFmt' value='UDiff' /></td>
 </tr>
</table>
<p />
<p />
<table border='0' align='center'>
 <tr>
   <td><input type='submit' name='submit' value='Submit' /></td>
   <td><input type='submit' name='cancel' value='Cancel' /></td>
 </tr>
</table>
</form>
</body>
</html>
""" % (TITLE, session, usrEmail)

    cdrcgi.sendPage(html)

else:
    # Page has been sent, user filled it out.  Process his input
    cdr.logwrite ("About to launch batch job", LF)
    args = (("diffFmt", format),)
    newJob = cdrbatch.CdrBatch (jobName=JOB_NAME,
                                command="Utilities/CTGovEntryDateBatch.py",
                                args=args,
                                email=emails)

    # Queue it for background processing
    try:
       newJob.queue()
    except Exception, e:
        cdrcgi.bail ("Batch job could not be started: " + str (e), logfile=LF)

    # Get an id user can use to find out what happened
    jobId = newJob.getJobId()

    # Tell user how to find the results
    html = cdrcgi.header(TITLE, TITLE, "Batch job launched",
                         buttons=[cdrcgi.MAINMENU, "Log Out"])

    html += """
<input type='hidden' name='Session' value='%s' />
<h4>The report has been queued for background processing</h4>
<p>To monitor the status of the job, click this
<a href='getBatchStatus.py?Session=%s&jobId=%s'><u>link</u></a>
or go to the CDR Administration menu and select 'View Batch Job Status'.</p>
</form></body></html>
""" % (session, session, jobId)

    cdrcgi.sendPage(html)
