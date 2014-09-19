#----------------------------------------------------------------------
#
# $Id$
#
# Report on documents checked out to a user.
#
# BZIssue::161
# JIRA::OCECDR-3800
#
#----------------------------------------------------------------------
import cgi
import cdrdb
import cdrcgi

#----------------------------------------------------------------------
# Initialize the script's variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
user     = fields.getvalue("User")
fmt      = fields.getvalue("format")
TITLE    = "CDR Report on Checked Out Documents"
SUBMENU  = "Report Menu"
pageopts = { "banner": "CDR Reports", "subtitle": "Checked Out Documents", }

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
    cursor = cdrdb.connect("CdrGuest").cursor()
except:
    cdrcgi.bail("Unable to connect to the CDR database")

#----------------------------------------------------------------------
# Put up form if we have no user.
#----------------------------------------------------------------------
if not user:
    pageopts["action"] = "CheckedOutDocs.py"
    cursor.execute("""\
  SELECT COUNT(*), u.id, u.fullname
    FROM usr u
    JOIN checkout c
      ON c.usr = u.id
   WHERE c.dt_in IS NULL
GROUP BY u.id, u.fullname
ORDER BY u.fullname""")
    rows = cursor.fetchall()
    if rows:
        pageopts["buttons"] = ("Submit", SUBMENU, cdrcgi.MAINMENU)
        page = cdrcgi.Page(TITLE, **pageopts)
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Select User"))
        values = [(r[1], u"%s (%d locks)" % (r[2], r[0])) for r in rows]
        page.add_select("User", "User", values)
        page.add("</fieldset>")
        page.add_output_options("html")
    else:
        pageopts["buttons"] = (SUBMENU, cdrcgi.MAINMENU)
        page = cdrcgi.Page(TITLE, **pageopts)
        page.add(page.B.P("No CDR documents are locked."))
    page.send()

#----------------------------------------------------------------------
# Display the report.
#----------------------------------------------------------------------
if fmt != "excel":
    fmt = "html"
cursor.execute("""\
  SELECT c.dt_out, t.name, d.id, d.title
    FROM usr u
    JOIN checkout c
      ON c.usr = u.id
    JOIN document d
      ON d.id = c.id
    JOIN doc_type t
      ON t.id = d.doc_type
   WHERE u.id = ?
     AND c.dt_in IS NULL
ORDER BY c.dt_out, t.name, d.id""", user)
rows = cursor.fetchall()
columns = (
    cdrcgi.Report.Column("Checked Out", width="140px"),
    cdrcgi.Report.Column("Type", width="150px"),
    cdrcgi.Report.Column("CDR ID", width="70px"),
    cdrcgi.Report.Column("Document Title", width="700px"),
)
table = cdrcgi.Report.Table(columns, rows)
report = cdrcgi.Report(TITLE, [table], **pageopts)
report.send(fmt)
