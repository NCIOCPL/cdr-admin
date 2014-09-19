#----------------------------------------------------------------------
#
# $Id$
#
# Reports on documents which link to specified terms.
#
# JIRA::OCECDR-3800 - Address security vulnerabilities
#
#----------------------------------------------------------------------
import cgi
import cdr
import cdrcgi
import cdrdb

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
doc_ids = fields.getvalue("doc_ids") or ""
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
SUBMENU = "Report Menu"

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Normalize the field values.
#----------------------------------------------------------------------
try:
    term_ids = [cdr.exNormalize(i)[1] for i in doc_ids.strip().split()]
except:
    cdrcgi.bail("Invalid document ID format in %s" % repr(doc_ids))

#----------------------------------------------------------------------
# Put out the form if we don't have a request.
#----------------------------------------------------------------------
if not term_ids:
    title    = "Term Usage"
    subtitle = "Report on documents indexed by specified terms"
    script   = "TermUsage.py"
    buttons  = ("Submit Request", SUBMENU, cdrcgi.MAINMENU)
    page     = cdrcgi.Page(title, subtitle=subtitle, buttons=buttons,
                           action=script, session=session)
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Enter Term IDs Separated By Spaces"))
    page.add_textarea_field("doc_ids", "Term IDs")
    page.add("</fieldset>")
    page.send()

#----------------------------------------------------------------------
# Find the documents using the specified terms.
#----------------------------------------------------------------------
columns = ("doc_type.name", "doc.id", "doc.title", "term.id", "term.title")
query = cdrdb.Query("doc_type", *columns).unique()
query.join("document doc", "doc_type.id = doc.doc_type")
query.join("query_term cdr_ref", "doc.id = cdr_ref.doc_id")
query.join("document term", "term.id = cdr_ref.int_val")
query.where("cdr_ref.path LIKE '%/@cdr:ref'")
query.where("doc_type.name <> 'Term'")
query.where(query.Condition("term.id", term_ids, "IN"))
query.order("doc_type.name", "doc.title", "term.id")
rows = query.execute().fetchall()

#----------------------------------------------------------------------
# Assemble the report.
#----------------------------------------------------------------------
count   = len(set([row[1] for row in rows]))
title   = "CDR Term Usage Report"
caption = "Number of documents using specified terms: %d" % count
columns = (
    cdrcgi.Report.Column("Doc Type"),
    cdrcgi.Report.Column("Doc ID"),
    cdrcgi.Report.Column("Doc Title"),
    cdrcgi.Report.Column("Term ID"),
    cdrcgi.Report.Column("Term Title"),
)
rows = [(
    row[0],
    cdr.normalize(row[1]),
    row[2],
    cdr.normalize(row[3]),
    row[4],
) for row in rows]
table = cdrcgi.Report.Table(columns, rows)
report = cdrcgi.Report(title, table, banner=title, subtitle=caption)
report.send()
