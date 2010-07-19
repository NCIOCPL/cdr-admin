#----------------------------------------------------------------------
#
# $Id$
#
# We need a Media Tracking report.  This spreadsheet report will keep track of
# the development and processing statuses of the Media documents.
#
# BZIssue::4873 - Remove Board Meeting Recordings display from Tracking Report
# 
# Revision 1.4  2009/02/03 22:47:17  venglisc
# Adjusted the XPath for the Glossary since the Glossary document structure
# had changed. (Bug 4461)
#
# Revision 1.3  2008/02/22 20:28:15  venglisc
# Modifications to add Diagnosis column and use different dates to display
# report results. (Bug 3839)
#
# Revision 1.2  2006/05/08 17:04:08  bkline
# Changed file extension to wrong string (.xls) to work around IE bug.
#
# Revision 1.1  2006/05/04 14:07:43  bkline
# Spreadsheet report to track processing of CDR Media documents.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi, string, time, xml.dom.minidom, xml.sax.saxutils
import ExcelWriter, sys

# ---------------------------------------------------------------------
# Select the available diagnosis terms
# ---------------------------------------------------------------------
def getDiagnoses():
    cursor.execute("""\
      SELECT DISTINCT value
        FROM query_term
       WHERE path = '/Media/MediaContent/Diagnoses/Diagnosis'
       ORDER BY value""")
    return cursor.fetchall() 

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = fields and fields.getvalue("Session") or None
fromDate = fields and fields.getvalue('FromDate') or None
toDate   = fields and fields.getvalue('ToDate') or None
diagnosis= fields and fields.getlist('Diagnosis') or None
request  = cdrcgi.getRequest(fields)
title    = "CDR Administration"
instr    = "Media Tracking Report"
buttons  = ["Submit Request", "Report Menu", cdrcgi.MAINMENU, "Log Out"]
script   = "MediaTrackingReport.py"
header   = cdrcgi.header(title, title, instr, script, buttons)

#----------------------------------------------------------------------
# Handle requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == "Report Menu":
    cdrcgi.navigateTo("Reports.py", session)
elif request == "Log Out": 
    cdrcgi.logout(session)

# ---------------------------------------------------------------------
# Create Database connection
# ---------------------------------------------------------------------
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()

#----------------------------------------------------------------------
# Ask the user for the report parameters.
#----------------------------------------------------------------------
if not fromDate or not toDate or not diagnosis:
    now         = time.localtime(time.time())
    toDateNew   = time.strftime("%Y-%m-%d", now)
    then        = list(now)
    then[1]    -= 1
    then[2]    += 1
    then        = time.localtime(time.mktime(then))
    fromDateNew = time.strftime("%Y-%m-%d", then)
    toDate      = toDate or toDateNew
    fromDate    = fromDate or fromDateNew

    diagnoses   = getDiagnoses()
    diagnoses[0]= [u'All']

    form        = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <TABLE BORDER='0'>
    <TR>
     <TD><B>Start Date:&nbsp;</B></TD>
     <TD><INPUT NAME='FromDate' VALUE='%s'>&nbsp;
         (use format YYYY-MM-DD for dates, e.g. 2002-01-01)</TD>
    </TR>
    <TR>
     <TD><B>End Date:&nbsp;</B></TD>
     <TD><INPUT NAME='ToDate' VALUE='%s'>&nbsp;</TD>
    </TR>
    <TR>
     <TD><B>Diagnosis:</B></TD>
     <TD>
      <SELECT NAME="Diagnosis" SIZE="10" MULTIPLE>
""" % (cdrcgi.SESSION, session, fromDate, toDate)

    for value in diagnoses:
        form   += """\
       <OPTION>%s</OPTION>
""" % value[0]

    form       += """\
      </SELECT>
     </TD>
    </TR>
   </TABLE>
  </FORM>
 </BODY>
</HTML>
"""
    cdrcgi.sendPage(header + form)

class Status:
    def __init__(self, node):
        self.value = u''
        self.date = u''
        self.comment = u''
        for child in node.childNodes:
            if child.nodeName == 'ProcessingStatusValue':
                self.value = cdr.getTextContent(child)
            elif child.nodeName == 'ProcessingStatusDate':
                self.date = cdr.getTextContent(child)
            elif child.nodeName == 'Comment' and not self.comment:
                self.comment = cdr.getTextContent(child).strip()
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
        cursor.execute("""\
            SELECT MAX(dt)
              FROM last_doc_publication
             WHERE doc_id = ?
               AND pub_subset LIKE 'Push_Documents_To_Cancer.Gov%'""", docId)
        rows = cursor.fetchall()
        self.published = rows and rows[0][0] and str(rows[0][0])[:10] or None
        cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
        docXml = cursor.fetchall()[0][0]
        dom = xml.dom.minidom.parseString(docXml.encode('utf-8'))
        for node in dom.documentElement.childNodes:
            if node.nodeName == 'ProcessingStatuses':
                for child in node.childNodes:
                    if child.nodeName == 'ProcessingStatus':
                        self.statuses.append(Status(child))
            elif node.nodeName == 'MediaTitle':
                self.title = cdr.getTextContent(node)
            elif node.nodeName == 'MediaSource':
                for child in node.childNodes:
                    if child.nodeName == 'OriginalSource':
                        for grandchild in child.childNodes:
                            if grandchild.nodeName == 'SourceFilename':
                                value = cdr.getTextContent(grandchild)
                                self.sourceFilename = value.strip() or None
            elif node.nodeName == 'MediaContent':
                for child in node.childNodes:
                    if child.nodeName == 'Diagnoses':
                        for grandchild in child.childNodes:
                            if grandchild.nodeName == 'Diagnosis':
                                value = cdr.getTextContent(grandchild)
                                self.diagnoses.append(value.strip()) or None

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
# Create/display the report.
#----------------------------------------------------------------------
# If 'All' has been selected we need to submit the SQL statement 
# without diagnosis filter.  Preparing the filter.
# ---------------------------------------------------------------------
if diagnosis[0] == 'All':
    sqlDiagnosis = u''
else:
    sqlDiagnosis = u'AND q.value in (%s)' % \
                     u','.join(["'%s'" % d for d in diagnosis])

cursor.execute("""\
         SELECT d.id, d.title, MAX(v.dt)
           FROM document d
           JOIN doc_type t
             ON t.id = d.doc_type
           JOIN doc_version v
             ON v.id = d.id
LEFT OUTER JOIN query_term q
             ON d.id = q.doc_id
            AND q.path = '/Media/MediaContent/Diagnoses/Diagnosis'
           JOIN query_term c
             ON d.id = c.doc_id
            AND c.path = '/Media/MediaContent/Categories/Category'
          WHERE t.name = 'Media'
            AND c.value <> 'Meeting Recording'
             %s
       GROUP BY d.id, d.title
         HAVING MAX(v.dt) BETWEEN '%s' AND DATEADD(s, -1, DATEADD(d, 1, '%s'))
       ORDER BY d.title
""" % (sqlDiagnosis, fromDate, toDate), timeout = 300)

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
subtitle = 'From %s - %s' % (fromDate, toDate)
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
for docId, docTitle, created in cursor.fetchall():
    mediaDoc = MediaDoc(cursor, docId, docTitle)
    rowNum = mediaDoc.addToSheet(ws, dateStyle, rowNum)
name = 'MediaTrackingReport-%s.xls' % time.strftime("%Y%m%d%H%M%S")
if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=%s" % name
print
wb.write(sys.stdout, True)
