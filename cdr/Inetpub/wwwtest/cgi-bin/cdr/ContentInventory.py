#----------------------------------------------------------------------
#
# $Id: ContentInventory.py,v 1.1 2009-03-24 15:16:50 venglisc Exp $
#
# Report listing all citations linked by a summary document.
# The output format is *.xml (Excel is able to import this)
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------
import cdrdb, sys, time, cdrcgi, ExcelWriter

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

conn = cdrdb.connect('CdrGuest')
#conn.setAutoCommit()
cursor = conn.cursor()

# Excel is able to read XML files so that's what we create here
# -------------------------------------------------------------
quickTitle = "Content Inventory Report"
t = time.strftime("%Y%m%d%H%M%S")
REPORTS_BASE = 'd:/cdr/tmp'
name = '/ContentInventory.xml'
fullname = REPORTS_BASE + name

#-----------------------------------------------------------------------
# Query to list the Summary, DrugSummary, and Media documents
# (include only published documents)
#-----------------------------------------------------------------------
cursor.execute("""\
SELECT DISTINCT dt.name as "DocType", d.id as "Id", t.value as "Title", 
                ty.value as "Type", a.value as "Audience",  
                Language = CASE l.value
                                WHEN 'Patients' THEN 'English'
                                WHEN 'es'       THEN 'Spanish'
                                WHEN 'en'       THEN 'English'
                                ELSE l.value
                           END
  INTO #inventory 
  FROM query_term_pub t
  -- Get the Document Type/Name
  JOIN document d
    ON t.doc_id = d.id
  JOIN doc_type dt
    ON d.doc_type = dt.id
  -- Get the Type
  JOIN query_term_pub ty
    ON t.doc_id = ty.doc_id
   AND ty.path IN ('/Summary/SummaryMetaData/SummaryType',
                   '/DrugInformationSummary/DrugInfoMetaData/DrugInfoType',
                   '/Media/PhysicalMedia/ImageData/ImageType')
  -- Get the Audience
  JOIN query_term_pub a
    ON a.doc_id = t.doc_id
   AND a.path IN  ('/Summary/SummaryMetaData/SummaryAudience',
                   '/DrugInformationSummary/DrugInfoMetaData/Audience',
                   '/Media/MediaContent/Captions/MediaCaption/@audience')
  -- Get the Language
  JOIN query_term_pub l
    ON l.doc_id = t.doc_id
   AND l.path IN  ('/Summary/SummaryMetaData/SummaryLanguage',
                   '/DrugInformationSummary/DrugInfoMetaData/Audience',
                   '/Media/MediaContent/Captions/MediaCaption/@language')
 WHERE dt.name IN ('Summary', 
                   'DrugInformationSummary', 
                   'Media')
   AND t.path IN  ('/Summary/SummaryTitle',
                   '/DrugInformationSummary/Title',
                   '/Media/MediaTitle')
   AND d.active_status = 'A'
 ORDER BY dt.name, d.id
""", timeout = 300)

#-----------------------------------------------------------------------
# Select all records from the temp table and add the latest 
# LastDateModified where it exists.
#-----------------------------------------------------------------------
cursor.execute("""\
           SELECT i.*, MAX(p.value) 
             FROM #inventory i
  LEFT OUTER JOIN query_term_pub p
               ON i.id = p.doc_id
              AND p.path IN ('/Summary/DateLastModified',
                             '/DrugInformationSummary/DateLastModified',
                             '/Media/ProcessingStatuses/ProcessingStatus' + 
                               '/ProcessingStatusDate')
             JOIN pub_proc_cg c
               ON c.id = i.id
            GROUP BY docType, i.id, title, type, audience, language
            ORDER BY i.DocType, i.Type, i.Audience
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
ws      = wb.addWorksheet(quickTitle, style1, 45, 1)
style2  = wb.addStyle(alignment = align, font = font, 
                         numFormat = 'YYYY-mm-dd')
alignH  = ExcelWriter.Alignment('Left', 'Bottom', wrap = True)
headFont= ExcelWriter.Font(bold=True, name = 'Times New Roman', size = 12)
styleH  = wb.addStyle(alignment = alignH, font = headFont)
    
# Set the colum width
# -------------------
ws.addCol( 1, 130)
ws.addCol( 2,  40)
ws.addCol( 3, 300)
ws.addCol( 4, 100)
ws.addCol( 5, 100)
ws.addCol( 6,  55)
ws.addCol( 7,  65)

# Create the Header row
# ---------------------
exRow = ws.addRow(1, styleH)
exRow.addCell(1, 'Document Type')
exRow.addCell(2, 'CDR-ID')
exRow.addCell(3, 'Title')
exRow.addCell(4, 'Type')
exRow.addCell(5, 'Audience')
exRow.addCell(6, 'Language')
exRow.addCell(7, 'Processing Date')

# Add the protocol data one record at a time beginning after 
# the header row
# ----------------------------------------------------------
rowNum = 1
for row in rows:
    rowNum += 1
    exRow = ws.addRow(rowNum, style1, 40)
    exRow.addCell(1, row[0])
    exRow.addCell(2, row[1])
    exRow.addCell(3, row[2])
    exRow.addCell(4, row[3])
    exRow.addCell(5, row[4])
    exRow.addCell(6, row[5])
    exRow.addCell(7, row[6])

t = time.strftime("%Y%m%d%H%M%S")                                               
print "Content-type: application/vnd.ms-excel"                                  
print "Content-Disposition: attachment; filename=ContentInventory-%s.xls" % t
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
