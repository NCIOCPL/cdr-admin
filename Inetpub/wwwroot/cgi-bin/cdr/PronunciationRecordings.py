#----------------------------------------------------------------------
#
# $Id$
#
# New report to track the processing of audio pronunciation media
# documents.
#
# BZIssue::5123
#
#----------------------------------------------------------------------
import cdr, cdrcgi, cgi, time, cdrbatch

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
today     = time.strftime('%Y-%m-%d')
fields    = cgi.FieldStorage()
request   = cdrcgi.getRequest(fields)
session   = cdrcgi.getSession(fields)
email     = cdr.getEmail(session)
language  = fields.getvalue('Language') or 'all'
startDate = fields.getvalue('StartDate') or '2011-01-01'
endDate   = fields.getvalue('EndDate') or today
SUBMENU   = "Report Menu"
buttons   = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script    = "PronunciationRecordings.py"
title     = "CDR Administration"
section   = "Audio Pronunciation Recordings Tracking Report"
header    = cdrcgi.header(title, title, section, script, buttons,
                          stylesheet = """\
   <link type='text/css' rel='stylesheet' href='/stylesheets/CdrCalendar.css'>
   <script language='JavaScript' src='/js/CdrCalendar.js'></script>
   <style type='text/css'>
    .err { width: 100%; text-align: center; font-weight: bold; color: red }
    .CdrDateField { width: 100px; }
   </style>
""")

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# William asked us to explain this to the users (I'm not kidding).
#----------------------------------------------------------------------
explanation = ""
if request and startDate > endDate:
    explanation = "<p class='err'>End date cannot precede start date.</p>"
    request = None

#----------------------------------------------------------------------
# Put up the menu if we don't have selection criteria yet.
#----------------------------------------------------------------------
if not request:
    form = """\
   <input type='hidden' name='%s' value='%s' />
   %s
   <fieldset class='dates'>
    <legend>Date Range</legend>
    <label for='start'>Start Date:</label>
    <input name='StartDate' value='%s' class='CdrDateField'
           id='start' /> &nbsp;
    <label for='end'>End Date:</label>
    <input name='EndDate' value='%s' class='CdrDateField' id='end' />
   </fieldset>
   <fieldset>
    <legend>Language</legend>
    <input name='Language' type='radio' value='all' class='choice'
           checked='checked' /> All<br />
    <input name='Language' type='radio' value='en' class='choice' /> English
    <br />
    <input name='Language' type='radio' value='es' class='choice' /> Spanish
  </form>
""" % (cdrcgi.SESSION, session, explanation, startDate, endDate)
    cdrcgi.sendPage(header + form + """\
 </body>
</html>
""")

#----------------------------------------------------------------------
# Queue up a request for the report.
#----------------------------------------------------------------------
args = (('start', startDate), ('end', endDate), ('language', language))
if not email or '@' not in email:
    cdrcgi.bail("No email address for logged-in user")
try:
    batch = cdrbatch.CdrBatch(jobName=section, email=email, args=args,
                              command='lib/Python/CdrLongReports.py')
except Exception, e:
    cdrcgi.bail("Failure creating batch job: %s" % repr(e))
try:
    batch.queue()
except Exception, e:
    cdrcgi.bail("Unable to start job: %s" % repr(e))
jobId = batch.getJobId()
cdrcgi.sendPage(header + """\
   <h4>Report has been queued for background processing</h4>
   <p>
    To monitor the status of the job, click this
    <a href='http://%s%s/getBatchStatus.py?%s=%s&jobId=%s'><u>link</u></a>
    or use the CDR Administration menu to select 'View
    Batch Job Status'.
   </p>
  </form>
 </body>
</html>
""" % (cdrcgi.WEBSERVER, cdrcgi.BASE, cdrcgi.SESSION, session, jobId))
