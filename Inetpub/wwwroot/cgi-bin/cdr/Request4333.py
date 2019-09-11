#----------------------------------------------------------------------
# "We need a New Published Glossary Terms Report which will serve as a
# QC report to verify which new Glossary Term Name documents have been
# published within the given time frame.  We would like a new Mailer
# report so we can track responses easier."
#
# JIRA::OCECDR-3800 - Address security vulnerabilities
#----------------------------------------------------------------------
import cgi
import cdr
import cdrdb
import cdrcgi
import datetime
import sys
import lxml.etree as etree

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
cursor    = cdrdb.connect("CdrGuest").cursor()
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
begin     = fields.getvalue("begin")
end       = fields.getvalue("end")
title     = "CDR Administration"
section   = "New Published Glossary Terms"
SUBMENU   = "Report Menu"
buttons   = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script    = 'Request4333.py'

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
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Object in which we collect what we need for the mailers.
#----------------------------------------------------------------------
class TermName:
    def __init__(self, docId, firstPub, cursor):
        self.docId = docId
        self.firstPub = firstPub
        cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE path = '/GlossaryTermName/TermName/TermNameString'
               AND doc_id = ?""", docId)
        self.enName = cursor.fetchall()[0][0]
        cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE path = '/GlossaryTermName/TranslatedName/TermNameString'
               AND doc_id = ?""", docId)
        self.spNames = [row[0] for row in cursor.fetchall()]
    def addToSheet(self, sheet, styles, row):
        sheet.write(row, 0, self.docId, styles.left)
        sheet.write(row, 1, self.enName, styles.left)
        sheet.write(row, 2, u"; ".join(self.spNames), styles.left)
        sheet.write(row, 3, str(self.firstPub)[:10], styles.left)
        return row + 1

#----------------------------------------------------------------------
# Display the form for the report's parameters.
#----------------------------------------------------------------------
def createForm():
    now = datetime.date.today()
    then = now - datetime.timedelta(7)
    page = cdrcgi.Page(title, subtitle=section, action=script,
                       buttons=buttons, session=session)
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Enter Report Parameters"))
    page.add_date_field("begin", "Start Date", value=then)
    page.add_date_field("end", "End Date", value=now)
    page.add("</fieldset>")
    page.send()

#----------------------------------------------------------------------
# Add the title row and the column headers.
#----------------------------------------------------------------------
def addColumnHeaders(styles, sheet):
    widths = (13, 55, 55, 23)
    labels = ("CDR ID", "Term Name (English)", "Term Name (Spanish)",
              "Date First Published")
    assert(len(widths) == len(labels))
    for col, width in enumerate(widths):
        sheet.col(col).width = styles.chars_to_width(width)
    for col, label in enumerate(labels):
        sheet.write(0, col, label, styles.header)

#----------------------------------------------------------------------
# Generate the Mailer Tracking Report. We have already scrubbed date
# parameters, so they're safe.
#----------------------------------------------------------------------
def createReport(cursor, startDate, endDate):
    query = cdrdb.Query("document d", "d.id", "d.first_pub").order(1)
    query.join("doc_type t", "t.id = d.doc_type")
    query.where("t.name = 'GlossaryTermName'")
    query.where("d.first_pub >= '%s'" % startDate)
    query.where("d.first_pub <= '%s 23:59:59'" % endDate)
    query.where("d.active_status = 'A'")
    rows = query.execute(cursor, 300).fetchall()
    names = []
    for docId, firstPub in rows:
        names.append(TermName(docId, firstPub, cursor))
    styles = cdrcgi.ExcelStyles()
    styles.set_color(styles.header, "blue")
    sheet = styles.add_sheet("Term Names")
    addColumnHeaders(styles, sheet)
    row = 1
    for name in names:
        row = name.addToSheet(sheet, styles, row)
    sheet.write(row, 0, u"Total: %d" % len(names), styles.bold)
    try:
        import msvcrt, os
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    except:
        pass
    now = datetime.datetime.now()
    stamp = now.strftime("%Y%m%d%H%M%S")
    print("Content-type: application/vnd.ms-excel")
    print("Content-Disposition: attachment; filename=TermNames-%s.xls" % stamp)
    print()
    styles.book.save(sys.stdout)

#----------------------------------------------------------------------
# Create the report or as for the report parameters.
#----------------------------------------------------------------------
if cdrcgi.is_date(begin) and cdrcgi.is_date(end):
    createReport(cursor, begin, end)
else:
    createForm()
