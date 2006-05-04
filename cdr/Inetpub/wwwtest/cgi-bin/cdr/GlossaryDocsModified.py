#----------------------------------------------------------------------
#
# $Id: GlossaryDocsModified.py,v 1.1 2006-05-04 14:58:32 bkline Exp $
#
# "The Glossary Documents Modified Report will serve as a QC report to
# verify which documents were changed within a given time frame, which
# will help with Spanish Glossary term processing."
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, time, ExcelWriter, xml.dom.minidom, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
startDate = fields and fields.getvalue("startdate") or None
endDate   = fields and fields.getvalue("enddate")   or None
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
title     = "Glossary Documents Modified Report"
instr     = "Glossary Documents Modified Report"
script    = "GlossaryDocsModified.py"
SUBMENU   = "Report Menu"
buttons   = ("Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out")
header    = cdrcgi.header(title, title, instr, script, buttons)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# If we don't have the required parameters, ask for them.
#----------------------------------------------------------------------
if not startDate or not endDate:
    form   = u"""\
      <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
      <TABLE>
       <TR>
        <TD ALIGN='right'>Start Date:&nbsp;</TD>
        <TD><INPUT NAME='startdate'>
         (use format YYYY-MM-DD for dates, e.g. 2005-01-01)
        </TD>
       <TR>
        <TD ALIGN='right'>End Date:&nbsp;</TD>
        <TD><INPUT NAME='enddate'></TD>
       </TR>
       </TABLE>
      </FORM>
     </BODY>
    </HTML>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

def fix(title):
    return title.encode('latin-1', 'replace')
    #return title.split(';')[0].encode('latin-1', 'replace')

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect("CdrGuest")
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Object for GlossaryTerm document info we need.
#----------------------------------------------------------------------
class GlossaryTerm:
    def __init__(self, cdrId, cursor):
        versions = cdr.lastVersions('guest', 'CDR%010d' % cdrId)
        cursor.execute("SELECT title, xml FROM document WHERE id = ?", cdrId)
        rows = cursor.fetchall()
        dom  = xml.dom.minidom.parseString(rows[0][1].encode('utf-8'))
        self.cdrId              = cdrId
        self.lastVerPublishable = versions[0] == versions[1]
        self.lastVersion        = versions[0]
        self.title              = rows[0][0]
        self.comment            = None
        self.dateLastModified   = None
        for node in dom.documentElement.childNodes:
            if node.nodeName == 'Comment':
                self.comment = cdr.getTextContent(node)
            elif node.nodeName == 'DateLastModified':
                self.dateLastModified = cdr.getTextContent(node)

#----------------------------------------------------------------------
# Create the report.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT DISTINCT v.id
      FROM doc_version v
      JOIN doc_type t
        ON t.id = v.doc_type
     WHERE t.name = 'GlossaryTerm'
       AND v.publishable = 'Y'
       AND v.dt BETWEEN '%s' AND DATEADD(s, -1, DATEADD(d, 1, '%s'))""" %
               (startDate, endDate), timeout = 300)
rows = cursor.fetchall()
terms = []
for row in rows:
    terms.append(GlossaryTerm(row[0], cursor))
terms.sort(lambda a,b: cmp(a.title, b.title))
book   = ExcelWriter.Workbook('CDR', 'NCI')
align  = ExcelWriter.Alignment(vertical = 'Top', wrap = True)
normal = book.addStyle(alignment = align)
align  = ExcelWriter.Alignment(vertical = 'Top', horizontal = 'Center')
center = book.addStyle(alignment = align)
sheet  = book.addWorksheet('GlossaryTerm')
font   = ExcelWriter.Font('#FFFFFF', bold = True)
bkgrd  = ExcelWriter.Interior('#0000FF')
align  = ExcelWriter.Alignment('Center', 'Center', True)
hdrs   = book.addStyle(alignment = align, font = font, interior = bkgrd)
row    = sheet.addRow(1, hdrs)
sheet.addCol(1, 50)
sheet.addCol(2, 200)
sheet.addCol(3, 50)
sheet.addCol(4, 70)
sheet.addCol(5, 60)
sheet.addCol(6, 200)
row.addCell(1, u'DocId')
row.addCell(2, u'DocTitle')
row.addCell(3, u'Last Version')
row.addCell(4, u'Publishable?')
row.addCell(5, u'Date Last Modified')
row.addCell(6, u'Comment')
rowNum = 2
for term in terms:
    row = sheet.addRow(rowNum, normal)
    row.addCell(1, term.cdrId, 'Number', center)
    row.addCell(2, term.title)
    row.addCell(3, term.lastVersion, 'Number', center)
    row.addCell(4, term.lastVerPublishable and u'Y' or u'N', style = center)
    row.addCell(5, term.dateLastModified or u'', style = center)
    row.addCell(6, term.comment or u'')
    rowNum += 1

name = 'GlossaryDocumentsModified-%s.xml' % time.strftime("%Y%m%d%H%M%S")
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=%s" % name
print
book.write(sys.stdout)
