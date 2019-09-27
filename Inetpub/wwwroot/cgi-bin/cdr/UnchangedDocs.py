#----------------------------------------------------------------------
# Reports on documents unchanged for a specified number of days.
#
# BZissue::161
# JIRA::OCECDR-3800 - Address security vulnerabilities
#----------------------------------------------------------------------
import cgi
import cdrcgi
import datetime
from cdrapi import db

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
cursor   = db.connect(user="CdrGuest").cursor()
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
days     = fields.getvalue("days")
doc_type = fields.getvalue("doctype")
max_rows = fields.getvalue("max")
SUBMENU  = 'Report Menu'

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Get the list of active document types. We'll need these both for
# populating the form's picklist as well as scrubbing the incoming
# parameter values.
#----------------------------------------------------------------------
query = db.Query("doc_type", "name").order(1)
query.where("name IS NOT NULL")
query.where("name <> ''")
doc_types = [row[0] for row in query.execute(cursor).fetchall()]

#----------------------------------------------------------------------
# Do the report if we have a request.
#----------------------------------------------------------------------
if request:
    cdrcgi.valParmVal(request, valList=("Submit Request", SUBMENU,
                                         cdrcgi.MAINMENU))
    try:
        max_rows = max_rows and int(max_rows) or 1000
        days = days and int(days) or 365
    except:
        max_rows = 1000
        days = 365
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days)
    query = db.Query("document d", "d.id", "d.title", "MAX(a.dt)")
    query.join("audit_trail a", "d.id = a.document")
    query.group("d.id", "d.title")
    query.having("MAX(a.dt) < '%s'" % cutoff)
    query.order(3, 1)
    query.limit(max_rows)
    if doc_type and doc_type != "All":
        if doc_type not in doc_types:
            cdrcgi.bail()
        query.join("doc_type t", "t.id = d.doc_type")
        query.where(query.Condition("t.name", doc_type))
    docs    = query.execute(cursor, 600).fetchall()
    title   = "Documents Unchanged for %d Days" % days
    instr   = "Document type: %s" % doc_type
    buttons = (SUBMENU, cdrcgi.MAINMENU)
    columns = (
        cdrcgi.Report.Column("Doc ID"),
        cdrcgi.Report.Column("Doc Title"),
        cdrcgi.Report.Column("Last Change"),
    )
    rows = []
    for doc_id, doc_title, last_change in docs:
        short_title = doc_title[:100]
        if len(doc_title) > 100:
            short_title += " ..."
        row = ("CDR%010d" % doc_id, short_title, str(last_change)[:10])
        rows.append(row)
    table = cdrcgi.Report.Table(columns, rows)
    report = cdrcgi.Report(title, table, banner=title, subtitle=instr)
    report.send()

#----------------------------------------------------------------------
# Put out the form if we don't have a request.
#----------------------------------------------------------------------
title   = "CDR Administration"
section = "Unchanged Documents"
buttons = ("Submit Request", SUBMENU, cdrcgi.MAINMENU)
page = cdrcgi.Page(title, subtitle=section, action="UnchangedDocs.py",
                   buttons=buttons, session=session)
page.add("<fieldset>")
page.add(page.B.LEGEND("Report Parameters"))
page.add_text_field("days", "Age", value="365")
page.add_select("doctype", "Doc Type", ["All"] + doc_types, "All")
page.add_text_field("max", "Max Rows", value="1000")
page.add("</fieldset>")
page.send()
