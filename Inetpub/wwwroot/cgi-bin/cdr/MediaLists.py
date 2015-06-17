#----------------------------------------------------------------------
#
# $Id$
#
# Report to list Media documents, optionally filtered by
# category and/or diagnosis.
#
# JIRA::OCECDR-3800 - Address security vulnerabilities
#
#----------------------------------------------------------------------
import cgi
import cdrcgi
import cdrdb
import datetime

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
show_id   = fields.getvalue("show_id") == "Y"
diagnosis = fields.getlist("diagnosis")
category  = fields.getlist("category")
request   = cdrcgi.getRequest(fields)
title     = "CDR Media List"
instr     = "Media Lists"
script    = "MediaLists.py"
SUBMENU   = "Report Menu"
buttons   = ("Submit", SUBMENU, cdrcgi.MAINMENU)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect("CdrGuest")
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Assemble the lists of valid values.
#----------------------------------------------------------------------
query = cdrdb.Query("query_term t", "t.doc_id", "t.value").order(2).unique()
query.join("query_term m", "m.int_val = t.doc_id")
query.where("t.path = '/Term/PreferredName'")
query.where("m.path = '/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref'")
results = query.execute(cursor).fetchall()
diagnoses = [("any", "Any Diagnosis")] + results
query = cdrdb.Query("query_term", "value", "value").order(1).unique()
query.where("path = '/Media/MediaContent/Categories/Category'")
query.where("value <> ''")
results = query.execute(cursor).fetchall()
categories = [("any", "Any Category")] + results

#----------------------------------------------------------------------
# Validate the form values. The expectation is that any bogus values
# will come from someone tampering with the form, so no need to provide
# the hacker with any useful diagnostic information.
#----------------------------------------------------------------------
for value, values in ((diagnosis, diagnoses), (category, categories)):
    values = [str(v[0]).lower() for v in values]
    for val in value:
        if val.lower() not in values:
            cdrcgi.bail("Corrupted form value")

#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
if not categories or not request:
    page = cdrcgi.Page(title, subtitle=instr, action=script,
                       buttons=buttons, session=session)
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Report Filtering"))
    page.add_select("diagnosis", "Diagnosis", diagnoses, "any", multiple=True)
    page.add_select("category", "Category", categories, "any", multiple=True)
    page.add("</fieldset>")
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Display Options"))
    page.add_radio("show_id", "Do not include CDR ID", "N", checked=True)
    page.add_radio("show_id", "Include CDR ID", "Y")
    page.add("</fieldset>")
    page.send()

#----------------------------------------------------------------------
# Build the SQL query.
#----------------------------------------------------------------------
content_path = "/Media/MediaContent"
diagnosis_path = content_path + "/Diagnoses/Diagnosis/@cdr:ref"
category_path = content_path + "/Categories/Category"
query = cdrdb.Query("query_term m", "m.doc_id", "m.value").unique().order(2)
query.where("m.path = '/Media/MediaTitle'")
if category and "any" not in category:
    query.join("query_term c", "c.doc_id = m.doc_id")
    query.where(query.Condition("c.path", category_path))
    query.where(query.Condition("c.value", category, "IN"))
    category_names = ", ".join(category)
else:
    category_names = "Any Category"
if diagnosis and "any" not in diagnosis:
    query.join("query_term d", "d.doc_id = m.doc_id")
    query.where(query.Condition("d.path", diagnosis_path))
    query.where(query.Condition("d.int_val", diagnosis, "IN"))
    diag_query = cdrdb.Query("query_term", "value").order(1)
    diag_query.where("path = '/Term/PreferredName'")
    diag_query.where(query.Condition("doc_id", diagnosis, "IN"))
    diagnosis_names = [row[0] for row in diag_query.execute().fetchall()]
    diagnosis_names = u", ".join(diagnosis_names)
else:
    diagnosis_names = "Any Diagnosis"

#----------------------------------------------------------------------
# Submit the query to the database.
#----------------------------------------------------------------------
try:
    rows = query.execute(cursor).fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Failure retrieving Media documents: %s' % info[1][0])
if not rows:
    criteria = "Diagnosis: %s; Condition: %s" % (diagnosis_names,
                                                 category_names)
    cdrcgi.bail("No Records Found for Criteria: %s" % criteria)

#----------------------------------------------------------------------
# Assemble and return the report.
#----------------------------------------------------------------------
id_column = cdrcgi.Report.Column("Doc ID", width="80px")
title_column = cdrcgi.Report.Column("Doc Title", width="800px")
columns = show_id and [id_column, title_column] or [title_column]
if not show_id:
    rows = [[row[1]] for row in rows]
caption = ("Category: %s" % category_names, "Diagnosis: %s" % diagnosis_names)
title = "PDQ Media Documents (%d)" % len(rows)
subtitle = "Media List -- %s" % datetime.date.today().strftime("%B %d, %Y")
table = cdrcgi.Report.Table(columns, rows, caption=caption)
report = cdrcgi.Report(title, [table], banner=title, subtitle=subtitle)
report.send()
