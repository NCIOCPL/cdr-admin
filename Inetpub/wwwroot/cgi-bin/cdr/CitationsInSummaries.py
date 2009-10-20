#----------------------------------------------------------------------
#
# $Id$
#
# Report listing all citations linked by a summary document.
# The output format is *.xml (Excel is able to import this)
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2006/05/05 22:30:42  venglisc
# Initial copy of report listing Citation documents that are linked to a
# summary. (Bug 2040)
#
#
#----------------------------------------------------------------------
import cdrdb, sys, time, cdrcgi, ExcelWriter

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

conn = cdrdb.connect('CdrGuest')
conn.setAutoCommit()
cursor = conn.cursor()

# Excel is able to read XML files so that's what we create here
# -------------------------------------------------------------
t = time.strftime("%Y%m%d%H%M%S")
REPORTS_BASE = 'd:/cdr/tmp'
name = '/SummaryAllCitations.xml'
fullname = REPORTS_BASE + name

#----------------------------------------------------------------------
# Find InScopeProtocol documents with organization in France
#----------------------------------------------------------------------
cursor.execute("""\
SELECT distinct d.id CDRID, d.title
  FROM query_term q 
  JOIN document d
    ON d.id = q.int_val
  JOIN document s
    ON s.id = q.doc_id
 WHERE path like '/Summary/%CitationLink/@cdr:ref'
--   AND d.val_status = 'V'
   AND d.active_status = 'A' 
   AND s.active_status = 'A'
 ORDER BY d.id desc
""", timeout = 300)
rows = cursor.fetchall()

# Create the spreadsheet and define default style, etc.
# -----------------------------------------------------
wb      = ExcelWriter.Workbook()
b       = ExcelWriter.Border()
borders = ExcelWriter.Borders(b, b, b, b)
font    = ExcelWriter.Font(name = 'Times New Roman', size = 11)
align   = ExcelWriter.Alignment('Left', 'Top', wrap = True)
style1  = wb.addStyle(alignment = align, font = font)
# style1  = wb.addStyle(alignment = align, font = font, borders = borders)
urlFont = ExcelWriter.Font('blue', None, 'Times New Roman', size = 11)
style4  = wb.addStyle(alignment = align, font = urlFont)
ws      = wb.addWorksheet("Citations in Summaries", style1, 45, 1)
style2  = wb.addStyle(alignment = align, font = font, 
                         numFormat = 'YYYY-mm-dd')
    
# Set the colum width
# -------------------
ws.addCol( 1, 50)
ws.addCol( 2, 550)

# Create the Header row
# ---------------------
exRow = ws.addRow(1, style2)
exRow.addCell(1, 'CDR-ID')
exRow.addCell(2, 'Citation Title')

# Add the protocol data one record at a time beginning after 
# the header row
# ----------------------------------------------------------
rowNum = 1
for row in rows:
    rowNum += 1
    exRow = ws.addRow(rowNum, style1, 40)
    url = ("http://bach.nci.nih.gov/cgi-bin/cdr/"
           "QcReport.py?Session=guest&DocId=%d" % row[0])
    exRow.addCell(1, " %s" % row[0], href = url, style = style4)
    exRow.addCell(2, row[1], style = style2)

t = time.strftime("%Y%m%d%H%M%S")                                               
print "Content-type: application/vnd.ms-excel"                                  
print "Content-Disposition: attachment; filename=CitationsInSummaries-%s.xls" % t    
print                

wb.write(sys.stdout, True)

# # Save the Report
# # ---------------
# fobj = file(fullname, "w")
# wb.write(fobj)
# print ""
# print "  Report written to %s" % fullname
# fobj.close()
# 
