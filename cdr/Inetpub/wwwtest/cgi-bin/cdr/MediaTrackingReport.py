#----------------------------------------------------------------------
#
# $Id: MediaTrackingReport.py,v 1.2 2006-05-08 17:04:08 bkline Exp $
#
# We need a Media Tracking report.  This spreadsheet report will keep track of
# the development and processing statuses of the Media documents.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2006/05/04 14:07:43  bkline
# Spreadsheet report to track processing of CDR Media documents.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi, string, time, xml.dom.minidom, xml.sax.saxutils
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
   </TABLE>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session, fromDate, toDate)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Escape markup special characters.
#----------------------------------------------------------------------
def fix(me):
    if not me:
        return u"&nbsp;"
    return me # xml.sax.saxutils.escape(me)

#----------------------------------------------------------------------
# Prepare definitions for display.
#----------------------------------------------------------------------
def fixList(defs):
    if not defs:
        return u"&nbsp;"
    return fix(u"; ".join(defs))

class Summary:
    titles = {}
    def __init__(self, node):
        self.title = None
        self.docId = node.getAttribute('cdr:ref')
        #sys.stderr.write("Summary id=%s text=%s\n" % (self.docId,
        #                        cdr.getTextContent(node)))
        if self.docId:
            if self.docId in self.titles:
                self.title = self.titles[self.docId]
            else:
                path = '/Summary/SummaryTitle'
                values = cdr.getQueryTermValueForId(path, self.docId, conn)
                if values:
                    self.title = values[0]
                    self.titles[self.docId] = self.title
                    #sys.stderr.write("ti=%s\n" % self.title)

class GlossaryTerm:
    termNames = {}
    def __init__(self, node):
        self.termName = None
        self.docId = node.getAttribute('cdr:ref')
        #sys.stderr.write("GlossaryTerm id=%s text=%s\n" % (self.docId,
        #                        cdr.getTextContent(node)))
        if self.docId:
            if self.docId in self.termNames:
                self.termName = self.termNames[self.docId]
            else:
                path = '/GlossaryTerm/TermName'
                values = cdr.getQueryTermValueForId(path, self.docId, conn)
                if values:
                    self.termName = values[0]
                    self.termNames[self.docId]= self.termName
                    #sys.stderr.write("gt=%s\n" % self.termName)

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
            elif child.nodeName == 'Comment':
                self.comment = cdr.getTextContent(child)
    def addToRow(self, row, dateStyle):
        row.addCell(6, self.value)
        row.addCell(7, self.date)
        row.addCell(8, self.comment)

#----------------------------------------------------------------------
# Media document object definition.
#----------------------------------------------------------------------
class MediaDoc:
    def __init__(self, cursor, docId, docTitle):
        self.docId = docId
        self.docTitle = docTitle
        self.title = None
        self.sourceFilename = None
        self.summaries = []
        self.glossaryTerms = []
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
            elif node.nodeName == 'ProposedUse':
                for child in node.childNodes:
                    if child.nodeName == 'Summary':
                        self.summaries.append(Summary(child))
                    elif child.nodeName == 'Glossary':
                        self.glossaryTerms.append(GlossaryTerm(child))
            elif node.nodeName == 'MediaTitle':
                self.title = cdr.getTextContent(node)
            elif node.nodeName == 'MediaSource':
                for child in node.childNodes:
                    if child.nodeName == 'OriginalSource':
                        for grandchild in child.childNodes:
                            if grandchild.nodeName == 'SourceFilename':
                                value = cdr.getTextContent(grandchild)
                                self.sourceFilename = value.strip() or None

    def addToSheet(self, sheet, dateStyle, rowNum):
        summaries = []
        for s in self.summaries:
            if s.title:
                summaries.append(s.title)
        glossaryTerms = []
        for t in self.glossaryTerms:
            if t.termName:
                glossaryTerms.append(t.termName)
        flag = self.lastVersionPublishable and u'Y' or u'N'
        row = sheet.addRow(rowNum)
        mergeDown = len(self.statuses) - 1
        if mergeDown < 1:
            mergeDown = None
        row.addCell(1, self.docId, 'Number', mergeDown = mergeDown)
        row.addCell(2, self.title or u'', mergeDown = mergeDown)
        row.addCell(3, self.sourceFilename or u'', mergeDown = mergeDown)
        row.addCell(4, u', '.join(summaries), mergeDown = mergeDown)
        row.addCell(5, u', '.join(glossaryTerms), mergeDown = mergeDown)
        row.addCell(9, flag, mergeDown = mergeDown)
        row.addCell(10, self.published or u'', mergeDown = mergeDown,
                    style = dateStyle)
        if not self.statuses:
            for colNum in (6, 7, 8):
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
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
    SELECT d.id, d.title, MIN(a.dt)
      FROM document d
      JOIN doc_type t
        ON t.id = d.doc_type
      JOIN audit_trail a
        ON a.document = d.id
     WHERE t.name = 'Media'
  GROUP BY d.id, d.title
    HAVING MIN(a.dt) BETWEEN '%s' AND DATEADD(s, -1, DATEADD(d, 1, '%s'))
  ORDER BY d.title""" %
               (fromDate, toDate), timeout = 300)

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
ws.addCol( 1,  46.70)
ws.addCol( 2, 119.25)
ws.addCol( 3, 125.00)
ws.addCol( 4,  75.00)
ws.addCol( 5, 108.75)
ws.addCol( 6, 151.50)
ws.addCol( 7,  71.25)
ws.addCol( 8,  90.00)
ws.addCol( 9,  71.25)
ws.addCol(10,  53.25)
row      = ws.addRow(1, h1Style, 15.75)
title    = 'Media Tracking Report'
row.addCell(1, title, mergeAcross = 9, style = h1Style)
row      = ws.addRow(2, h2Style)
subtitle = 'From %s - %s' % (fromDate, toDate)
row.addCell(1, subtitle, mergeAcross = 9, style = h2Style)
row      = ws.addRow(3, thStyle, 27)
headings = (
    'CDRID',
    'Title',
    'Sourcefile Name',
    'Proposed Summaries',
    'Proposed Glossary Terms',
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
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=%s" % name
print
wb.write(sys.stdout)
