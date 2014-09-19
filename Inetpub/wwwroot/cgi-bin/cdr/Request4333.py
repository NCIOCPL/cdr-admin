#----------------------------------------------------------------------
#
# $Id$
#
# "We need a New Published Glossary Terms Report which will serve as a
# QC report to verify which new Glossary Term Name documents have been
# published within the given time frame.  We would like a new Mailer
# report so we can track responses easier."
#
# JIRA::OCECDR-3800 - Address security vulnerabilities
#
#----------------------------------------------------------------------
import cgi
import cdr
import cdrdb
import cdrcgi
import datetime
import sys
import ExcelWriter
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
    def addToSheet(self, sheet, nextRow, style, urlStyle):
        spNames = u"; ".join(self.spNames)
        row = sheet.addRow(nextRow, style)
        nextRow += 1
        row.addCell(1, self.docId)
        row.addCell(2, self.enName)
        row.addCell(3, u"; ".join(self.spNames))
        row.addCell(4, str(self.firstPub)[:10])
        return nextRow

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
def addColumnHeaders(book, sheet, startDate, endDate, total):
    font  = ExcelWriter.Font(size = 10, bold = True, color = 'blue')
    align = ExcelWriter.Alignment('Center', 'Top')
    style = book.addStyle(font = font, alignment = align)
    sheet.addCol(1,  70)
    sheet.addCol(2, 300)
    sheet.addCol(3, 300)
    sheet.addCol(4, 100)
    row = sheet.addRow(1, style)
    row.addCell(1, u"CDR ID")
    row.addCell(2, u"Term Name (English)")
    row.addCell(3, u"Term Name (Spanish)")
    row.addCell(4, u"Date First Published")

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
    book = ExcelWriter.Workbook()
    sheet = book.addWorksheet('Term Names')
    addColumnHeaders(book, sheet, startDate, endDate, len(names))
    alignment = ExcelWriter.Alignment('Left', 'Top', True)
    font = ExcelWriter.Font('blue', True)
    style = book.addStyle(alignment = alignment)
    urlStyle = book.addStyle(font = font, alignment = alignment)
    nextRow = 2
    for name in names:
        nextRow = name.addToSheet(sheet, nextRow, style, urlStyle)
    font = ExcelWriter.Font(size = 10, bold = True)
    style = book.addStyle(font = font)
    row = sheet.addRow(nextRow, style)
    row.addCell(1, u"Total: %d" % len(names))
    try:
        import msvcrt, os
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    except:
        pass
    now = datetime.datetime.now()
    stamp = now.strftime("%Y%m%d%H%M%S")
    print "Content-type: application/vnd.ms-excel"
    print "Content-Disposition: attachment; filename=TermNames-%s.xls" % stamp
    print
    book.write(sys.stdout, True)

#----------------------------------------------------------------------
# Create the report or as for the report parameters.
#----------------------------------------------------------------------
if cdrcgi.is_date(begin) and cdrcgi.is_date(end):
    createReport(cursor, begin, end)
else:
    createForm()
