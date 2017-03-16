#----------------------------------------------------------------------
# New report to track the processing of audio pronunciation media
# documents.
#
# BZIssue::5123
# JIRA::OCECDR-3800 - Address security vulnerabilities
#----------------------------------------------------------------------
import cdr
import cdrbatch
import cdrcgi
import cgi
import datetime

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
today      = datetime.date.today()
fields     = cgi.FieldStorage()
request    = cdrcgi.getRequest(fields)
session    = cdrcgi.getSession(fields) or cdrcgi.bail("Please log in")
email      = cdr.getEmail(session) or cdrcgi.bail("No email for user")
language   = fields.getvalue("language") or "all"
start_date = fields.getvalue("start_date") or "2011-01-01"
end_date   = fields.getvalue("end_date") or str(today)
SUBMENU    = "Report Menu"
buttons    = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script     = "PronunciationRecordings.py"
title      = "CDR Administration"
section    = "Audio Pronunciation Recordings Tracking Report"

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Validate the parameters.
#----------------------------------------------------------------------
cdrcgi.valParmDate(start_date, msg="invalid start date")
cdrcgi.valParmDate(end_date, msg="invalid end date")
if start_date > end_date:
    cdrcgi.bail("end date cannot precede start date")

#----------------------------------------------------------------------
# Put up the menu if we don't have selection criteria yet.
#----------------------------------------------------------------------
if not request:
    instructions = (
        "All fields are required. "
        "The end date cannot precede the start date."
    )
    page = cdrcgi.Page(title, subtitle=section, buttons=buttons,
                       action=script, session=session)
    page.add(page.B.FIELDSET(page.B.P(instructions)))
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Date Range"))
    page.add_date_field("start_date", "Start Date", value=start_date)
    page.add_date_field("end_date", "End Date", value=end_date)
    page.add("</fieldset>")
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Language"))
    page.add_radio("language", "All", "all", checked=True)
    page.add_radio("language", "English", "en")
    page.add_radio("language", "Spanish", "es")
    page.add("</fieldset>")
    page.send()

#----------------------------------------------------------------------
# Queue up a request for the report.
#----------------------------------------------------------------------
if language not in ("en", "es"):
    language = "all"
args = (
    ("start", start_date),
    ("end", end_date),
    ("language", language),
)
if not email or "@" not in email:
    cdrcgi.bail("No email address for logged-in user")
try:
    batch = cdrbatch.CdrBatch(jobName=section, email=email, args=args,
                              command="lib/Python/CdrLongReports.py")
except Exception, e:
    cdrcgi.bail("Failure creating batch job: %s" % repr(e))
try:
    batch.queue()
except Exception, e:
    cdrcgi.bail("Unable to start job: %s" % repr(e))
jobId = batch.getJobId()
batch.show_status_page(session, title, section, script, SUBMENU)
