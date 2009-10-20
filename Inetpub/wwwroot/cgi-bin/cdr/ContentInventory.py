#----------------------------------------------------------------------
#
# $Id$
#
# Report listing all citations linked by a summary document.
# The output format is *.xml (Excel is able to import this)
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2009/07/29 16:32:23  venglisc
# Saving latest version which apparently wasn't under CVS yet.
#
# Revision 1.1  2009/03/24 15:16:50  venglisc
# Initial report to list summary, media, drug summary inventory. (Bug 4533)
#
#
#----------------------------------------------------------------------
import cdr, cdrdb, sys, time, cdrcgi, ExcelWriter

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

# ----------------------------------------------------------------------
# Document class to identify the keywords for the individual document
# types.  The keywords to be selected are as follows:
#   Summary:  main topic, section diagnosis, section intervention,
#             section type
#   DrugInfo: approved indication
#   Media:    label name, category element, diagnosis
# ----------------------------------------------------------------------
class Document:
    def __init__(self, id, docType, cursor):
        self.cdrId         = id
        self.type          = docType
        self.mainTopics    = []
        self.sDiagnoses    = []
        self.mDiagnoses    = []
        self.interventions = []
        self.sectionTypes  = []
        self.indications   = []
        self.labelNames    = []
        self.categories    = []

        termQuery = """
            SELECT t.value 
              FROM query_term d
              JOIN query_term t
                ON t.doc_id = d.int_val
               AND t.path = '/Term/PreferredName'
             WHERE d.path LIKE '%s'
               AND d.doc_id = %d 
             ORDER BY t.value"""
        termPaths = {'DIS':    {'Indication':
                                '/%%/DrugInfoMetaData' +
                                '/ApprovedIndication/@cdr:ref'},
                     'Summary':{'MainTopic':
                                '/%%/SummaryMetaData/MainTopics'  +
                                '/Term/@cdr:ref',
                                'Diagnosis':
                                '/Summary/%%/SectMetaData' +
                                '/Diagnosis/@cdr:ref',
                                'Intervention':
                                '/Summary/%%/SectMetaData' +
                                '/Intervention/@cdr:ref'},
                     'Media':  {'Diagnosis':
                                '/Media/%%/Diagnosis/@cdr:ref'}}

        valueQuery = """
            SELECT d.value 
              FROM query_term d
             WHERE d.path LIKE '%s'
               AND d.doc_id = %d
             ORDER BY d.value"""
        valuePaths = {'Summary':{'SectType':
                                 '/Summary/%%/SectMetaData/SectionType'},
                      'Media'  :{'Category':
                                 '/Media/MediaContent/Categories/Category',
                                 'Label':
                                 '/Media/PhysicalMedia/ImageData/LabelName'}}

        if self.type == 'DrugInformationSummary':
            # Selecting approved indication for DIS
            # -------------------------------------
            cursor.execute(termQuery % (termPaths['DIS']['Indication'], 
                                        self.cdrId))
            rows = cursor.fetchall()
            for row in rows:
                self.indications.append(row[0])
        elif self.type == 'Summary':
            # Selecting main topic for summaries
            # ----------------------------------
            cursor.execute(termQuery % (termPaths['Summary']['MainTopic'], 
                                        self.cdrId))
            rows = cursor.fetchall()
            for row in rows:
                self.mainTopics.append(row[0])

            # Selecting section diagnosis for summaries
            # ------------------------------ ----------
            cursor.execute(termQuery % (termPaths['Summary']['Diagnosis'], 
                                        self.cdrId))
            rows = cursor.fetchall()
            for row in rows:
                self.sDiagnoses.append(row[0])

            # Selecting section intervention for summaries
            # --------------------------------------------
            cursor.execute(termQuery % (termPaths['Summary']['Intervention'], 
                                        self.cdrId))
            rows = cursor.fetchall()
            for row in rows:
                self.interventions.append(row[0])

            # Selecting section type for summaries
            # ------------------------------------
            cursor.execute(valueQuery % (valuePaths['Summary']['SectType'], 
                                        self.cdrId))
            rows = cursor.fetchall()
            for row in rows:
                self.sectionTypes.append(row[0])
        elif self.type == 'Media':
            # Selecting main topic for summaries
            # ----------------------------------
            cursor.execute(termQuery % (termPaths['Media']['Diagnosis'], 
                                        self.cdrId))
            rows = cursor.fetchall()
            for row in rows:
                self.mDiagnoses.append(row[0])

            # Selecting main topic for summaries
            # ----------------------------------
            cursor.execute(valueQuery % (valuePaths['Media']['Category'], 
                                        self.cdrId))
            rows = cursor.fetchall()
            for row in rows:
                self.categories.append(row[0])

            # Selecting main topic for summaries
            # ----------------------------------
            cursor.execute(valueQuery % (valuePaths['Media']['Label'], 
                                        self.cdrId))
            rows = cursor.fetchall()
            for row in rows:
                self.labelNames.append(row[0])



# ----------------------------------------------------------------------
# Function to combine all of the Document lists into a single keyword
# list
# ----------------------------------------------------------------------
def combineAll(doc):
    allKeywords = []

    for attr in doc.__dict__:
        if not attr == 'cdrId' and not attr == 'type':
            allKeywords.extend(doc.__dict__[attr])

    return allKeywords


#-----------------------------------------------------------------------
# Query to list the Summary, DrugSummary, and Media documents
# (include only published documents)
#-----------------------------------------------------------------------
cursor.execute("""\
SELECT DISTINCT dt.name as "DocType", d.id as "Id", t.value as "Title", 
                u.value as "URL", 
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
  -- Get the URL (fake entry for Media to be set NULL later)
  JOIN query_term_pub u
    ON u.doc_id = l.doc_id
   AND u.path in ('/Summary/SummaryMetaData/SummaryURL/@cdr:xref',
                  '/DrugInformationSummary/DrugInfoMetaData/URL/@cdr:xref', 
                  '/Media/MediaTitle')
 WHERE dt.name IN ('Summary', 
                   'DrugInformationSummary', 
                   'Media')
   AND t.path IN  ('/Summary/SummaryTitle',
                   '/DrugInformationSummary/Title',
                   '/Media/MediaTitle')
   AND d.active_status = 'A'
 ORDER BY dt.name, d.id
""", timeout = 300)

# A media URL doesn't exist - setting it to an empty string
# ----------------------------------------------------------
cursor.execute("""
           UPDATE #inventory set URL = ''
            WHERE DocType = 'Media'""")

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
            GROUP BY docType, i.id, title, url, type, audience, language
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
ws.addCol( 3, 200)
ws.addCol( 4, 150)
ws.addCol( 5, 200)
ws.addCol( 6, 100)
ws.addCol( 7, 100)
ws.addCol( 8,  55)
ws.addCol( 9,  65)

# Create the Header row
# ---------------------
exRow = ws.addRow(1, styleH)
exRow.addCell(1, 'Document Type')
exRow.addCell(2, 'CDR-ID')
exRow.addCell(3, 'Title')
exRow.addCell(4, 'URL')
exRow.addCell(5, 'Keywords')
exRow.addCell(6, 'Type')
exRow.addCell(7, 'Audience')
exRow.addCell(8, 'Language')
exRow.addCell(9, 'Date Last Modified / Last Processed')

# Add the protocol data one record at a time beginning after 
# the header row
# ----------------------------------------------------------
rowNum = 1
for row in rows:
    rowNum += 1
    exRow = ws.addRow(rowNum, style1, 40)
    exRow.addCell(1, row[0])
    exRow.addCell(2, row[1])

    doc = Document(row[1], row[0], cursor)

    keywords = combineAll(doc)

    #print keywords
    #print ", ".join([x for x in keywords])
    #sys.exit(1)
    
    if row[0] == 'Media':
        url = '%s/cgi-bin/cdr/GetCdrImage.py?id=CDR%s.jpg' % (
                                                  cdr.getHostName()[2], row[1])
        exRow.addCell(3, " %s" % row[2], href = url, style = style4)
    else:
        exRow.addCell(3, " %s" % row[2], href = row[3], style = style4)
    exRow.addCell(4, row[3])
    exRow.addCell(5, ", ".join([x for x in keywords]))
    exRow.addCell(6, row[4])
    exRow.addCell(7, row[5])
    exRow.addCell(8, row[6])
    exRow.addCell(9, row[7])

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
