#----------------------------------------------------------------------
#
# $Id$
#
# Reports on citation documents which have changed.
#
# BZIssue::161 - Changed "Title" label to "DocTitle" as requested by Eileen
# JIRA::OCECDR-3800 - Address security vulnerabilities
#
#----------------------------------------------------------------------
import cgi
import cdrcgi
import cdrdb
import urllib

#----------------------------------------------------------------------
# Named constants.
#----------------------------------------------------------------------
SCRIPT  = "ModifiedPubMedDocs.py"
SUBMENU = "Report Menu"

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields) or cdrcgi.bail("Please log in")
request = cdrcgi.getRequest(fields)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Submit the query to the database.
#----------------------------------------------------------------------
query = cdrdb.Query("document d", "d.id", "d.title").unique().order(2)
query.join("query_term q", "q.doc_id = d.id")
query.where("q.path = '/Citation/PubmedArticle/ModifiedRecord'")
query.where("q.value = 'Yes'")
rows = query.execute().fetchall()

#----------------------------------------------------------------------
# Assemble the report.
#----------------------------------------------------------------------
title   = u"CDR Administration"
instr   = u"Modified PubMed Documents"
buttons = (SUBMENU, cdrcgi.MAINMENU)
caption = "Modified Documents (%d)" % len(rows)
columns = (
    cdrcgi.Report.Column("Doc ID"),
    cdrcgi.Report.Column("Doc Title"),
)
table_rows = []
parms = {
    cdrcgi.SESSION: session,
    "Filter": "name:Citation QC Report"
}
for doc_id, doc_title in rows:
    doc_id_string = "CDR%010d" % doc_id
    parms["DocId"] = doc_id_string
    url = "Filter.py?" + urllib.urlencode(parms)
    short_title = doc_title[:100]
    if len(doc_title) > 100:
        short_title += " ..."
    row = (
        cdrcgi.Report.Cell(doc_id_string, href=url),
        short_title,
    )
    table_rows.append(row)
table = cdrcgi.Report.Table(columns, table_rows, caption=caption)
report = cdrcgi.Report(title, [table], banner=title, subtitle=instr)
report.send()
