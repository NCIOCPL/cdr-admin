#----------------------------------------------------------------------
# Reports on invalid or blocked CDR documents.
#
# BZIssue::3533
# JIRA::OCECDR-3800
#----------------------------------------------------------------------
import cdrcgi
import cdrdb
import cgi

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
docType = fields.getvalue('docType')
docType = docType and int(docType) or None
cursor  = cdrdb.connect('CdrGuest').cursor()
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "InvalidDocs.py"
title   = "CDR Administration"
section = "Invalid Documents"

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
# Get the list of active document types.
#----------------------------------------------------------------------
query = cdrdb.Query("doc_type", "id", "name")
query.where("active = 'Y'")
query.where("xml_schema IS NOT NULL")
query.where("name NOT IN ('Filter', 'xxtest', 'schema')")
docTypes = query.order("name").execute(cursor).fetchall()

#----------------------------------------------------------------------
# Show the form if we don't have a document type selected.
#----------------------------------------------------------------------
if not docType:
    page = cdrcgi.Page(title, subtitle=section, action=script,
                       session=session, buttons=buttons)
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Select Document Type"))
    page.add_select("docType", "Type", docTypes)
    page.send()

#----------------------------------------------------------------------
# If a report has been requested, show it.
#----------------------------------------------------------------------
docTypeName = dict(docTypes).get(docType)
invalidCaption = "Invalid %s Documents" % docTypeName
blockedCaption = "Blocked %s Documents" % docTypeName
subquery = cdrdb.Query("doc_version", "MAX(num)").where("id = v.id")
query = cdrdb.Query("doc_version v", "v.id", "v.title", "d.active_status")
query.join("document d", "d.id = v.id")
query.join("doc_type t", "t.id = d.doc_type")
query.where(query.Condition("t.id", docType))
query.where(query.Condition("v.num", subquery))
query.where("v.val_status = 'I'")
rows = query.order("v.id").execute(cursor).fetchall()
invalid = []
blocked = []
for doc_id, doc_title, active_status in rows:
    doc = (cdrcgi.Report.Cell(doc_id, classes="right"), doc_title)
    if active_status == "I":
        blocked.append(doc)
    else:
        invalid.append(doc)
columns = (
    cdrcgi.Report.Column("ID", width="50px"),
    cdrcgi.Report.Column("Title", width="950px"),
)
tables = (
    cdrcgi.Report.Table(columns, invalid, caption=invalidCaption),
    cdrcgi.Report.Table(columns, blocked, caption=blockedCaption),
)
report = cdrcgi.Report(title, tables, banner=title, subtitle=section)
report.send()
