#----------------------------------------------------------------------
#
# $Id$
#
# We need a Media Tracking report.  This spreadsheet report will keep track of
# the development and processing statuses of the Media documents.
#
# BZIssue::4880 - Board Meeting Recordings Tracking Report
#                 (report adapted from Media Tracking Report)
# BZIssue::5068 - [Media] Board Meeting Recording Tracking Report to
#                 display blocked documents
# JIRA::OCECDR-3800 - Address security vulnerabilities
#
#----------------------------------------------------------------------
import cgi
import cdr
import cdrdb
import cdrcgi
import datetime
import lxml.etree as etree
import ExcelWriter
import sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
cursor   = cdrdb.connect("CdrGuest").cursor()
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
fromDate = fields.getvalue('FromDate')
toDate   = fields.getvalue('ToDate')
today    = datetime.date.today().strftime("%B %d, %Y")
title    = "CDR Administration"
instr    = "Board Meeting Recordings Tracking Report - %s" % today
buttons  = ["Submit", "Report Menu", cdrcgi.MAINMENU, "Log Out"]
script   = "RecordingTrackingReport.py"

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == "Report Menu":
    cdrcgi.navigateTo("Reports.py", session)
elif request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Ask the user for the report parameters. William asked that the start
# date be hard-code to March 1, 2010
#----------------------------------------------------------------------
if not cdrcgi.is_date(fromDate) or not cdrcgi.is_date(toDate):
    toDate = datetime.date.today()
    #fromDate = toDate - datetime.timedelta(30)
    fromDate = "2010-03-01"
    page = cdrcgi.Page(title, subtitle=instr, action=script,
                       buttons=buttons, session=session)
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Select Date Range"))
    page.add_date_field("FromDate", "Start Date", value=fromDate)
    page.add_date_field("ToDate", "End Date", value=toDate)
    page.add("</fieldset>")
    page.send()

class Status:
    def __init__(self, node):
        self.value = u''
        self.date = u''
        self.comment = u''
        for child in node:
            if child.tag == "ProcessingStatusValue":
                self.value = child.text
            elif child.tag == "ProcessingStatusDate":
                self.date = child.text
            elif child.tag == "Comment" and not self.comment:
                self.comment = child.text.strip()
    def addToRow(self, row, dateStyle):
        row.addCell(4, self.value)
        row.addCell(5, self.date)
        row.addCell(6, self.comment)

#----------------------------------------------------------------------
# Media document object definition.
#----------------------------------------------------------------------
class MediaDoc:
    def __init__(self, cursor, docId, docTitle, encoding):
        self.docId         = docId
        self.docTitle      = docTitle
        self.encoding      = encoding
        self.title         = None
        self.comment       = None
        self.dateCreated   = None
        self.dateVersioned = None
        self.statuses      = []

        # Get the date the document was first saved (this can be different
        # then the date of the first version)
        # ----------------------------------------------------------------
        query = cdrdb.Query("audit_trail t", "t.dt")
        query.join("action a", "a.id = t.action AND a.name = 'Add Document'")
        query.where(query.Condition("t.document", docId))
        rows = query.execute(cursor).fetchall()
        self.dateCreated = rows and rows[0][0] and str(rows[0][0])[:10] or None

        # Get the date the document was last versioned
        # ----------------------------------------------------------------
        query = cdrdb.Query("doc_version", "id", "MAX(num)", "dt",
                            "publishable").group("id", "dt", "publishable")
        query.where(query.Condition("id", docId))
        rows = query.execute(cursor).fetchall()
        self.dateVersioned = rows and rows[0][2] \
                                  and str(rows[0][2])[:10] or None
        self.flag = rows and rows[0][3] and str(rows[0][3]) or None

        # Get the XML of the document to select additional data elements
        # --------------------------------------------------------------
        query = cdrdb.Query("document", "xml")
        query.where(query.Condition("id", docId))
        docXml = query.execute(cursor).fetchall()[0][0]
        tree = etree.XML(docXml.encode("utf-8"))
        for node in tree:
            if node.tag == "ProcessingStatuses":
                for child in node:
                    if child.tag == "ProcessingStatus":
                        self.statuses.append(Status(child))
            elif node.tag == "MediaTitle":
                self.title = node.text
            elif node.tag == "Comment":
                self.comment = node.text

    def addToSheet(self, sheet, dateStyle, rowNum):
        row = sheet.addRow(rowNum)
        mergeDown = len(self.statuses) - 1
        if mergeDown < 1:
            mergeDown = None

        row.addCell(1, self.docId, 'Number', mergeDown = mergeDown)
        row.addCell(2, self.title, mergeDown = mergeDown)
        row.addCell(3, self.encoding, mergeDown = mergeDown)
        row.addCell(4, self.dateCreated or u'', mergeDown = mergeDown,
                    style = dateStyle)
        row.addCell(5, self.flag, mergeDown = mergeDown)
        row.addCell(6, self.dateVersioned, mergeDown = mergeDown)
        row.addCell(7, self.comment, mergeDown = mergeDown)

        return rowNum + 1

#----------------------------------------------------------------------
# Create/display the report. Can't use the active_doc view, because
# several of the meeting recording documents are blocked. String
# interpolation for the dates in the HAVING clause is safe, because
# we have vetted them with calls to cdrcgi.is_date().
#----------------------------------------------------------------------
query = cdrdb.Query("document d", "d.id", "d.title", "r.value", "MAX(v.dt)")
query.join("doc_type t", "t.id = d.doc_type")
query.join("doc_version v", "v.id = d.id")
query.join("query_term c", "d.id = c.doc_id")
query.join("query_term r", "d.id = r.doc_id")
query.where("c.path = '/Media/MediaContent/Categories/Category'")
query.where("r.path = '/Media/PhysicalMedia/SoundData/SoundEncoding'")
query.where("t.name = 'Media'")
query.where("c.value = 'Meeting Recording'")
query.group("d.id", "d.title", "r.value")
query.having("MAX(v.dt) BETWEEN '%s' AND '%s 23:59:59'" % (fromDate, toDate))
query.order("d.title").execute(cursor, 300)

#----------------------------------------------------------------------
# Set up the spreadsheet.
#----------------------------------------------------------------------
wb        = ExcelWriter.Workbook()
border    = ExcelWriter.Border()
f         = ExcelWriter.Font(family = 'Swiss')
a         = ExcelWriter.Alignment('Left', 'Top', wrap = True)
b         = ExcelWriter.Borders(border, border, border, border)
tdStyle   = wb.addStyle(font = f, alignment = a, borders = b)
d         = 'YYYY-mm-dd'
dateStyle = wb.addStyle(font = f, alignment = a, borders = b, numFormat = d)
f         = ExcelWriter.Font(family = 'Swiss', bold = True)
thStyle   = wb.addStyle(font = f, alignment = a, borders = b)
a         = ExcelWriter.Alignment('Center', 'Bottom')
b         = ExcelWriter.Borders()
h2Style   = wb.addStyle(font = f, alignment = a, borders = b)
f         = ExcelWriter.Font(family = 'Swiss', size = 12, bold = True)
h1Style   = wb.addStyle(font = f, alignment = a, borders = b)
ws        = wb.addWorksheet("Board Meeting Recordings", tdStyle, frozenRows = 3)
ws.addCol(1,  45)
ws.addCol(2, 300)
ws.addCol(3,  50)
ws.addCol(4,  55)
ws.addCol(5,  70)
ws.addCol(6,  55)
ws.addCol(7, 300)
row      = ws.addRow(1, h1Style, 15.75)
title    = 'Board Meeting Recordings Tracking Report'
row.addCell(1, title, mergeAcross = 6, style = h1Style)
row      = ws.addRow(2, h2Style)
subtitle = 'From %s - %s' % (fromDate, toDate)
row.addCell(1, subtitle, mergeAcross = 6, style = h2Style)
row      = ws.addRow(3, thStyle, 27)
headings = (
    'CDRID',
    'Media Title',
    'Encoding',
    'Date Created',
    'Last Version Publishable',
    'Version Date',
    'Comments')
for i in range(len(headings)):
    row.addCell(i + 1, headings[i])
rowNum = 4
for docId, docTitle, encoding, created in cursor.fetchall():
    mediaDoc = MediaDoc(cursor, docId, docTitle, encoding)
    rowNum = mediaDoc.addToSheet(ws, dateStyle, rowNum)
now = datetime.datetime.now()
name = 'RecordingTrackingReport-%s.xls' % now.strftime("%Y%m%d%H%M%S")
if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=%s" % name
print
wb.write(sys.stdout, True)
