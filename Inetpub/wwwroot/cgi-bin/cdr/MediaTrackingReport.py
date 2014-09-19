#----------------------------------------------------------------------
#
# $Id$
#
# We need a Media Tracking report.  This spreadsheet report will keep track of
# the development and processing statuses of the Media documents.
#
# BZIssue::3839 - Add diagnosis column; modify date display
# BZIssue::4461 - Adjust for changed glossary document structure
# BZIssue::4873 - Remove Board Meeting Recordings display from Tracking Report
# JIRA::OCECDR-3800 - Address security vulnerabilities
#
#----------------------------------------------------------------------
import cgi
import cdr
import cdrdb
import cdrcgi
import datetime
import ExcelWriter
import lxml.etree as etree
import sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
cursor    = cdrdb.connect('CdrGuest').cursor()
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
from_date = fields.getvalue("start_date")
to_date   = fields.getvalue("end_date")
diagnosis = fields.getlist('Diagnosis') or ["any"]
title     = "CDR Administration"
instr     = "Media Tracking Report"
buttons   = ["Submit Request", "Report Menu", cdrcgi.MAINMENU, "Log Out"]
script    = "MediaTrackingReport.py"
start     = datetime.datetime.now()

#----------------------------------------------------------------------
# Handle requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == "Report Menu":
    cdrcgi.navigateTo("Reports.py", session)
elif request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Get the picklist values for diagnoses.
#----------------------------------------------------------------------
query = cdrdb.Query("query_term t", "t.doc_id", "t.value").unique().order(2)
query.join("query_term m", "m.int_val = t.doc_id")
query.where("t.path = '/Term/PreferredName'")
query.where("m.path = '/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref'")
diagnoses = [["any", "Any Diagnosis"]] + query.execute(cursor).fetchall()

#----------------------------------------------------------------------
# Ask the user for the report parameters.
#----------------------------------------------------------------------
if not request or not cdrcgi.is_date(from_date) or not cdrcgi.is_date(to_date):
    end = datetime.date.today()
    start = end - datetime.timedelta(30)
    page = cdrcgi.Page(title, subtitle=instr, action=script,
                       buttons=buttons, session=session)
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Report Filtering"))
    page.add_date_field("start_date", "Start Date", value=start)
    page.add_date_field("end_date", "End Date", value=end)
    page.add_select("diagnosis", "Diagnosis", diagnoses, "any", multiple=True)
    page.add("</fieldset>")
    page.send()

#----------------------------------------------------------------------
# Information from a single ProcessingStatus element in a Media doc.
#----------------------------------------------------------------------
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
    def __init__(self, cursor, docId, docTitle):
        self.docId = docId
        self.docTitle = docTitle
        self.title = None
        self.sourceFilename = None
        self.diagnoses = []
        self.statuses = []
        lastAny, lastPub, chng = cdr.lastVersions('guest', 'CDR%010d' % docId)
        self.lastVersionPublishable = (lastAny != -1 and lastAny == lastPub)
        query = cdrdb.Query("last_doc_publication", "MAX(dt)")
        query.where(query.Condition("doc_id", docId))
        query.where("pub_subset LIKE 'Push_Documents_To_Cancer.Gov%'")
        rows = query.execute(cursor).fetchall()
        self.published = rows and rows[0][0] and str(rows[0][0])[:10] or None
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
            elif node.tag == "MediaSource":
                for child in node:
                    if child.tag == "OriginalSource":
                        for grandchild in child:
                            if grandchild.tag == "SourceFilename":
                                value = grandchild.text
                                self.sourceFilename = value.strip() or None
            elif node.tag == "MediaContent":
                for child in node:
                    if child.tag == "Diagnoses":
                        for grandchild in child:
                            if grandchild.tag == "Diagnosis":
                                value = grandchild.text
                                if value is not None and value.strip():
                                    self.diagnoses.append(value.strip())

    def addToSheet(self, sheet, dateStyle, rowNum):
        diagnoses = []
        for d in self.diagnoses:
            diagnoses.append(d)
        flag = self.lastVersionPublishable and u'Y' or u'N'
        row = sheet.addRow(rowNum)
        mergeDown = len(self.statuses) - 1
        if mergeDown < 1:
            mergeDown = None
        if self.sourceFilename:
            titleCell = u'%s (%s)' % (self.title or u'', self.sourceFilename)
        else:
            titleCell = self.title or u''
        row.addCell(1, self.docId, 'Number', mergeDown = mergeDown)
        row.addCell(2, titleCell, mergeDown = mergeDown)
        row.addCell(3, u', '.join(diagnoses), mergeDown = mergeDown)
        row.addCell(7, flag, mergeDown = mergeDown)
        row.addCell(8, self.published or u'', mergeDown = mergeDown,
                    style = dateStyle)
        if not self.statuses:
            for colNum in (4, 5, 6):
                row.addCell(colNum, u'')
        else:
            self.statuses[0].addToRow(row, dateStyle)
            for status in self.statuses[1:]:
                rowNum += 1
                row = sheet.addRow(rowNum)
                status.addToRow(row, dateStyle)
        return rowNum + 1

#----------------------------------------------------------------------
# Create the SQL query. String interpolation for the dates in the
# HAVING clause is safe below, because we've validated those values
# above with calls to cdrcgi.is_date().
#----------------------------------------------------------------------
query = cdrdb.Query("document d", "d.id", "d.title", "MAX(v.dt)").order(2)
query.join("doc_version v", "v.id = d.id")
query.join("query_term q1", "q1.doc_id = d.id")
query.where("q1.path = '/Media/MediaContent/Categories/Category'")
query.where("q1.value <> 'Meeting Recording'")
if diagnosis and "any" not in diagnosis:
    query.join("query_term q2", "q2.doc_id = d.id")
    query.where("q2.path = '/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref'")
    query.where(query.Condition("q2.int_val", diagnosis, "IN"))
query.group("d.id", "d.title")
query.having("MAX(v.dt) BETWEEN '%s' AND '%s 23:59:59'" % (from_date, to_date))
query.log()

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
ws        = wb.addWorksheet("Media Tracking Report", tdStyle, frozenRows = 3)
ws.addCol(1,  46.70)
ws.addCol(2, 119.25)
ws.addCol(3, 125.00)
ws.addCol(4, 151.50)
ws.addCol(5,  71.25)
ws.addCol(6, 350.00)
ws.addCol(7,  71.25)
ws.addCol(8,  53.25)
row      = ws.addRow(1, h1Style, 15.75)
title    = 'Media Tracking Report'
row.addCell(1, title, mergeAcross = 7, style = h1Style)
row      = ws.addRow(2, h2Style)
subtitle = 'From %s - %s' % (from_date, to_date)
row.addCell(1, subtitle, mergeAcross = 7, style = h2Style)
row      = ws.addRow(3, thStyle, 27)
headings = (
    'CDRID',
    'Title (Source Filename)',
    'Diagnosis',
    'Processing Status',
    'Processing Status Date',
    'Comments',
    'Last Version Publishable?',
    'Published')
for i in range(len(headings)):
    row.addCell(i + 1, headings[i])
rowNum = 4
for docId, docTitle, created in query.execute(cursor, 300).fetchall():
    mediaDoc = MediaDoc(cursor, docId, docTitle)
    rowNum = mediaDoc.addToSheet(ws, dateStyle, rowNum)
now = datetime.datetime.now()
delta = now - start
row = ws.addRow(rowNum)
row.addCell(1, "elapsed: %s" % delta, mergeAcross=7)
name = 'MediaTrackingReport-%s.xls' % now.strftime("%Y%m%d%H%M%S")
if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=%s" % name
print
wb.write(sys.stdout, True)
