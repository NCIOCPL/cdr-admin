#----------------------------------------------------------------------
#
# $Id: MediaTrackingReport.py 9796 2010-07-19 16:54:25Z volker $
#
# We need a Media Tracking report.  This spreadsheet report will keep track of
# the development and processing statuses of the Media documents.
#
# BZIssue::4880 - Board Meeting Recordings Tracking Report
#                 (report adapted from Media Tracking Report)
# BZIssue::5068 - [Media] Board Meeting Recording Tracking Report to 
#                 display blocked documents 
# 
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi, time, xml.dom.minidom
import ExcelWriter, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = fields and fields.getvalue("Session") or None
fromDate = fields and fields.getvalue('FromDate') or None
toDate   = fields and fields.getvalue('ToDate') or None
request  = cdrcgi.getRequest(fields)
title    = "CDR Administration"
instr    = "Board Meeting Recordings Tracking Report"
buttons  = ["Submit", "Report Menu", cdrcgi.MAINMENU, "Log Out"]
script   = "RecordingTrackingReport.py"

#----------------------------------------------------------------------
# Build date string for header.
#----------------------------------------------------------------------
dateString = time.strftime("%B %d, %Y")

jscript = """
<style type="text/css">
body {
    font-family: sans-serif;
    font-size: 11pt;
    }
legend  {
    font-weight: bold;
    color: teal;
    font-family: sans-serif;
    }
fieldset {
    width: 500px;
    margin-left: auto;
    margin-right: auto;
    display: block;
    }
p.title {
    font-family: sans-serif;
    font-size: 11pt;
    font-weight: bold;
    }
*.tablecenter {
    margin-left: auto;
    margin-right: auto;
    }
*.CdrDateField {
    width: 100px;
    }
*.mittich {
    width: 50px; 
    margin-left: auto;
    margin-right: auto;
    display: block;
    }
td.top {
    vertical-align: text-top;
    }
</style>

<link   type='text/css' rel='stylesheet' href='/stylesheets/CdrCalendar.css'>
<script type='text/javascript' language='JavaScript' src='/js/CdrCalendar.js'></script>

"""
header = cdrcgi.header(title, title, instr + ' - ' + dateString, 
                           script, buttons, 
                           numBreaks = 1,stylesheet = jscript)

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
if not fromDate or not toDate:
    now         = time.localtime(time.time())
    toDateNew   = time.strftime("%Y-%m-%d", now)
    then        = list(now)
    then[1]    -= 1
    then[2]    += 1
    then        = time.localtime(time.mktime(then))
    fromDateNew = time.strftime("%Y-%m-%d", then)
    toDate      = toDate or toDateNew
    fromDate    = fromDate or fromDateNew

    form        = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
    <fieldset>
     <legend>&nbsp;Select Date Range&nbsp;</legend>

    <table class="tablecenter" border="0">
     <tr>
      <td align="right">
       <label for="FromDate">Start Date: </label>
      </td>
      <td>
       <input id="FromDate" name="FromDate" 
                value="2010-03-01"
                class="CdrDateField">
      </td>
     </tr>
     <tr>
      <td align="right">
       <label for="ToDate">End Date: </label>
      </td>
      <td>
       <input id="ToDate" name="ToDate" 
                value="%s"
                class="CdrDateField">
      </td>
     </tr>
    </table>
    </fieldset>

    <p/>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session, toDateNew)
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
    def __init__(self, cursor, docId, docTitle, encoding):
        self.docId         = docId
        self.docTitle      = docTitle
        self.encoding      = encoding
        self.title         = None
        self.comment       = None
        self.dateCreated   = None
        self.dateVersioned = None
        self.statuses  = []

        # Get the date the document was first saved (this can be different
        # then the date of the first version)
        # ----------------------------------------------------------------
        cursor.execute("""\
            SELECT at.dt 
              FROM audit_trail at
              JOIN action ac
                ON at.action = ac.id
               AND name = 'Add Document'
             WHERE document = ?""", docId)

        rows = cursor.fetchall()
        self.dateCreated = rows and rows[0][0] and str(rows[0][0])[:10] or None

        # Get the date the document was last versioned
        # ----------------------------------------------------------------
        cursor.execute("""\
            SELECT id, MAX(num), dt, publishable
              FROM doc_version
             WHERE id = ?
             GROUP BY id, dt, publishable""", docId)

        rows = cursor.fetchall()
        self.dateVersioned = rows and rows[0][2] \
                                  and str(rows[0][2])[:10] or None
        self.flag = rows and rows[0][3] and str(rows[0][3]) or None

        # Get the XML of the document to select additional data elements
        # --------------------------------------------------------------
        cursor.execute("""\
            SELECT xml 
              FROM document 
             WHERE id = ?""", docId)

        docXml = cursor.fetchall()[0][0]
        dom = xml.dom.minidom.parseString(docXml.encode('utf-8'))
        for node in dom.documentElement.childNodes:
            if node.nodeName == 'ProcessingStatuses':
                for child in node.childNodes:
                    if child.nodeName == 'ProcessingStatus':
                        self.statuses.append(Status(child))
            elif node.nodeName == 'MediaTitle':
                self.title = cdr.getTextContent(node)
            elif node.nodeName == 'Comment':
                self.comment = cdr.getTextContent(node)

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
# Create/display the report.
# ---------------------------------------------------------------------
cursor.execute("""\
         SELECT d.id, d.title, r.value, MAX(v.dt)
           -- Several Meeting Recording documents are blocked.
           -- FROM active_doc d
           FROM document d
           JOIN doc_type t
             ON t.id = d.doc_type
           JOIN doc_version v
             ON v.id = d.id
           JOIN query_term c
             ON d.id = c.doc_id
            AND c.path = '/Media/MediaContent/Categories/Category'
           JOIN query_term r
             ON d.id = r.doc_id
            AND r.path = '/Media/PhysicalMedia/SoundData/SoundEncoding'
          WHERE t.name = 'Media'
            AND c.value = 'Meeting Recording'
       GROUP BY d.id, d.title, r.value
         HAVING MAX(v.dt) BETWEEN '%s' AND DATEADD(s, -1, DATEADD(d, 1, '%s'))
       ORDER BY d.title
""" % (fromDate, toDate), timeout = 300)

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
ws.addCol(2, 200)
ws.addCol(3,  50)
ws.addCol(4,  55)
ws.addCol(5,  70)
ws.addCol(6,  55)
ws.addCol(7, 200)
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
name = 'RecordingTrackingReport-%s.xls' % time.strftime("%Y%m%d%H%M%S")
if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=%s" % name
print
wb.write(sys.stdout, True)
