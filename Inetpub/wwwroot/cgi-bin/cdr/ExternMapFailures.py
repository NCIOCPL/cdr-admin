#----------------------------------------------------------------------
# Report on values found in external systems (such as ClinicalTrials.gov)
# which have not yet been mapped to CDR documents.
#
# BZIssue::1339
# JIRA::OCECDR-3800
#----------------------------------------------------------------------
import cdrcgi
import cgi
import datetime
from cdrapi import db

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
usages   = fields.getlist('usage')
age      = fields.getvalue('age')
mappable = fields.getvalue('mappable') == "yes"
SUBMENU  = "Report Menu"
buttons  = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script   = "ExternMapFailures.py"
title    = "CDR Administration"
section  = "External Map Failures Report"

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
# Establish a database connection.
#----------------------------------------------------------------------
conn = db.connect(user="CdrGuest")
cursor = conn.cursor()

#----------------------------------------------------------------------
# Make sure the usage values haven't been tampered with by a hacker.
#----------------------------------------------------------------------
cursor.execute("SELECT name FROM external_map_usage ORDER BY name")
usage_values = [row[0] for row in cursor.fetchall()]
for usage in usages:
    if usage not in usage_values:
        cdrcgi.bail("Invalid usage value")

#----------------------------------------------------------------------
# If we don't have a request, put up the request form.
#----------------------------------------------------------------------
if not usages:
    page = cdrcgi.Page(title, subtitle=section, action=script,
                       buttons=buttons, session=session)
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Report Parameters"))
    page.add_select("usage", "Usage(s)", usage_values, multiple=True)
    page.add_text_field("age", "Age (days)", value="30")
    page.add("</fieldset>")
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Options"))
    page.add_radio("mappable", "Include only mappable values", "yes",
                   checked=True)
    page.add_radio("mappable", "Also include non-mappable values", "no")
    page.add("</fieldset>")
    page.send()

#----------------------------------------------------------------------
# Translate the age parameter into a date in the past.
#----------------------------------------------------------------------
try:
    start_date = datetime.date.today() - datetime.timedelta(int(age))
except:
    start_date = datetime.date.today() - datetime.timedelta(1000)

#----------------------------------------------------------------------
# Construct a report table for one of the selected usage values.
#----------------------------------------------------------------------
def make_table(usage):
    query = """\
  SELECT m.value, CONVERT(CHAR(10), m.last_mod, 102)
    FROM external_map m
    JOIN external_map_usage u
      ON u.id = m.usage
   WHERE doc_id IS NULL
     AND u.name = ?
     AND m.last_mod >= ?
"""
    if mappable:
        query += """\
     AND m.mappable <> 'N'
"""
    query += """\
ORDER BY 2 DESC, 1"""
    cursor.execute(query, (usage, start_date))
    rows = cursor.fetchall()
    if not rows:
        col = cdrcgi.Report.Column("No recent unmapped values found.",
                                   width="905px")
        return cdrcgi.Report.Table((col,), [], caption=usage)
    columns = (
        cdrcgi.Report.Column("Value", width="800px"),
        cdrcgi.Report.Column("Recorded", width="100px"),
    )
    return cdrcgi.Report.Table(columns, rows, caption=usage)

#----------------------------------------------------------------------
# Assemble and deliver the report.
#----------------------------------------------------------------------
today = datetime.date.today().strftime("%B %d, %Y")
tables = [make_table(usage) for usage in usages]
report = cdrcgi.Report(section, tables, banner=section, subtitle=today)
report.send()
