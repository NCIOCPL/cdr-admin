#----------------------------------------------------------------------
#
# $Id$
#
# "We need a simple 'Documents Modified' Report to be generated in an Excel 
# spreadsheet, which verifies what documents were changed within a given time 
# frame."
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2005/05/25 14:07:09  bkline
# Report of documents modified within a specified time range.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, time, ExcelWriter, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
docType   = fields and fields.getvalue("doctype")   or "0"
startDate = fields and fields.getvalue("startdate") or None
endDate   = fields and fields.getvalue("enddate")   or None
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
title     = "Documents Modified Report"
instr     = "Documents Modified Report"
script    = "DocumentsModified.py"
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
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect("CdrGuest")
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Build a picklist for document types.
#----------------------------------------------------------------------
def getDoctypePicklist():
    picklist = ("<SELECT NAME='doctype'>\n"
                "<OPTION SELECTED value='0'>All Types</OPTION>\n")
    try:
        cursor.execute("""\
         SELECT id, name
           FROM doc_type
          WHERE xml_schema IS NOT NULL
            AND active = 'Y'
       ORDER BY name""")
        for id, name in cursor.fetchall():
            picklist += "<OPTION value='%d'>%s</OPTION>\n" % (id, name)
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])
    return picklist + "</SELECT>\n"

#----------------------------------------------------------------------
# If we don't have the required parameters, ask for them.
#----------------------------------------------------------------------
if not startDate or not endDate:
    form   = u"""\
      <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
      <TABLE>
       <TR>
        <TD><B>Document Type:&nbsp;</B></TD>
        <TD>%s</TD>
       </TR>
       <TR>
        <TD ALIGN='right'><b>Start Date:&nbsp;</b></TD>
        <TD><INPUT NAME='startdate'>
         (use format YYYY-MM-DD for dates, e.g. 2005-01-01)
        </TD>
       <TR>
        <TD ALIGN='right'><b>End Date:&nbsp;</b></TD>
        <TD><INPUT NAME='enddate'></TD>
       </TR>
       </TABLE>
      </FORM>
     </BODY>
    </HTML>
""" % (cdrcgi.SESSION, session, getDoctypePicklist())
    cdrcgi.sendPage(header + form)

# ---------------------------------------------------------------
# Create the report.
# ---------------------------------------------------------------
docType = int(docType)
where = docType and ("AND doc_type = %d" % docType) or ""
cursor.execute("CREATE TABLE #t (id INTEGER, ver INTEGER)")
conn.commit()
cursor.execute("""\
INSERT INTO #t
    SELECT id, MAX(num)
      FROM doc_version
     WHERE dt BETWEEN '%s' AND DATEADD(s, -1, DATEADD(d, 1, '%s'))
       %s
   GROUP BY id""" % (startDate, endDate, where))
conn.commit()
cursor.execute("""\
    SELECT t.id, t.ver, v.title, v.publishable
      FROM #t t
      JOIN doc_version v
        ON v.id = t.id
       AND v.num = t.ver
  ORDER BY t.id""")
rows = cursor.fetchall()

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    
t = time.strftime("%Y%m%d%H%M%S")
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=DocumentsModified-%s.xls" % t
print
workbook = ExcelWriter.Workbook()
worksheet = workbook.addWorksheet("Modified Documents")
align = ExcelWriter.Alignment('Center')
font = ExcelWriter.Font('white', bold=True)
interior = ExcelWriter.Interior('blue')
headerStyle = workbook.addStyle(alignment=align, font=font, interior=interior)
centerStyle = workbook.addStyle(alignment=align)
worksheet.addCol(1, 45)
worksheet.addCol(2, 300)
worksheet.addCol(3, 70)
worksheet.addCol(4, 70)
row = worksheet.addRow(1, headerStyle)
row.addCell(1, "Doc ID")
row.addCell(2, "Doc Title")
row.addCell(3, "Last Version")
row.addCell(4, "Publishable")
rowNumber = 2

for docId, docVer, docTitle, publishable in rows:
    row = worksheet.addRow(rowNumber)
    row.addCell(1, "%d" % docId, style=centerStyle)
    row.addCell(2, docTitle)
    row.addCell(3, "%d" % docVer, style=centerStyle)
    row.addCell(4, publishable, style=centerStyle)
    rowNumber += 1
workbook.write(sys.stdout, True)
