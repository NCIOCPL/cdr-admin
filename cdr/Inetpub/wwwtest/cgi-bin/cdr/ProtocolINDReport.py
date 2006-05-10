#----------------------------------------------------------------------
#
# $Id: ProtocolINDReport.py,v 1.1 2006-05-10 17:39:52 venglisc Exp $
#
# Report to list protocol information for trials with an IND number
#
# $Log: not supported by cvs2svn $
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
filename = 'ProtocolINDReport-%s.xls' % t

REPORT_BASE = 'd:/cdr/tmp/'
fullname = REPORT_BASE + filename

# Creating table of all InScopeProtocol documents that have and
# INDNumber element
# ------------------------------------------------------------------
cursor.execute("""\
    CREATE TABLE #t0
             (doc_id     INTEGER      NOT NULL,
              primary_id VARCHAR(100) NOT NULL,
              ctgov_id   VARCHAR(100) NULL,
              otitle     VARCHAR(500) NOT NULL,
              hptitle    VARCHAR(500) NOT NULL,
              ind_num    VARCHAR(50)  NOT NULL,
              ind_sn     VARCHAR(50)  NULL,
              pub_date   CHAR(10)     NULL,
              pub_status VARCHAR(50)  NULL)""")

# Into this temp table we are inserting everything except for the current
# document status (coming from the document table) and the date the 
# document was first published on Cancer.gov.
# -----------------------------------------------------------------------
cursor.execute("""\
    INSERT INTO #t0
SELECT q.doc_id CDRID, pid.value ProtID, ct.value CTGovID, 
       q.value OTitle, tt.value HPTitle, 
       q2.value IND#,  isn.value ISN, NULL, NULL
  FROM query_term q
  JOIN query_term q1
    ON q.doc_id = q1.doc_id
   AND q1.path  = '/InScopeProtocol/ProtocolTitle/@Type'
   AND q1.value = 'Original'
   AND left(q.node_loc, 4) = left(q1.node_loc, 4)
  JOIN query_term tt
    ON q.doc_id = tt.doc_id
   AND tt.path = '/InScopeProtocol/ProtocolTitle'
  JOIN query_term hpt
    ON q.doc_id  = hpt.doc_id
   AND hpt.path  = '/InScopeProtocol/ProtocolTitle/@Type'
   AND hpt.value = 'Professional'
   AND left(tt.node_loc, 4) = left(hpt.node_loc, 4)
  JOIN query_term q2
    ON q.doc_id = q2.doc_id
   AND q2.path  = '/InScopeProtocol/FDAINDInfo/INDNumber' 
  LEFT OUTER JOIN query_term isn
    ON q.doc_id = isn.doc_id
   AND isn.path = '/InScopeProtocol/FDAINDInfo/INDSerialNumber'
  JOIN query_term pid
    ON q.doc_id = pid.doc_id
   AND pid.path = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
  LEFT OUTER JOIN query_term ct
    ON q.doc_id = ct.doc_id
   AND ct.path  = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
  JOIN query_term ctt
    ON q.doc_id = ctt.doc_id
   AND ctt.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
   AND ctt.value= 'ClinicalTrials.gov ID'
   AND left(ct.node_loc, 8) = left(ctt.node_loc, 8)
 WHERE q.path = '/InScopeProtocol/ProtocolTitle'
--   AND q.doc_id = 63881
  """, timeout = 300)

#-----------------------------------------------------------------------
# Updating the temp table with the date the document was first published
#-----------------------------------------------------------------------
cursor.execute("""\
update #t0
  SET pub_date = (select convert(char(10), min(started), 121)
from pub_proc pp
join pub_proc_doc ppd
  on ppd.pub_proc = pp.id
join doc_version dv
  on ppd.doc_id = dv.id
 and ppd.doc_version = dv.num
where #t0.doc_id = dv.id
  and pp.status = 'Success'
  and pp.pub_subset like 'Push_Documents_To_Cancer.Gov%'
  and dv.val_status = 'V'
  and publishable = 'Y'
 group by dv.id)""", timeout = 300)

#----------------------------------------------------------------------
# Updating the temp table with the current document status.
#----------------------------------------------------------------------
cursor.execute("""\
UPDATE #t0
   SET pub_status = s.name
  FROM #t0
  JOIN document d
    ON #t0.doc_id = d.id
  JOIN active_status s
    ON s.id = d.active_status""", timeout = 300)

#----------------------------------------------------------------------
# Select the entire content of the temp table to write to a spreadsheet
#----------------------------------------------------------------------
cursor.execute("""\
SELECT *
  FROM #t0
""", timeout = 300)

rows = cursor.fetchall()

# Create the spreadsheet and define default style, etc.
# -----------------------------------------------------
wb      = ExcelWriter.Workbook()
b       = ExcelWriter.Border()
borders = ExcelWriter.Borders(b, b, b, b)
font    = ExcelWriter.Font(name = 'Arial', size = 11)
align   = ExcelWriter.Alignment('Left', 'Top', wrap = True)
urlFont = ExcelWriter.Font('blue', None, 'Arial', size = 11)
hdrFont = ExcelWriter.Font(name = 'Arial', size = 12, bold = 1)

# style1  = wb.addStyle(alignment = align, font = font, borders = borders)
style1  = wb.addStyle(alignment = align, font = font)
ws      = wb.addWorksheet("Protocols with IND", style1, 45, 1)

style2  = wb.addStyle(alignment = align, font = font)
style3  = wb.addStyle(alignment = align, font = hdrFont)
style4  = wb.addStyle(alignment = align, font = urlFont)
    
# Set the colum width
# -------------------
ws.addCol( 1, 50)
ws.addCol( 2, 150)
ws.addCol( 3, 150)
ws.addCol( 4, 550)
ws.addCol( 5, 550)
ws.addCol( 6, 70)
ws.addCol( 7, 50)
ws.addCol( 8, 70)
ws.addCol( 9, 50)

# Create the Header row
# ---------------------
exRow = ws.addRow(1, style3)
exRow.addCell(1, 'CDR-ID')
exRow.addCell(2, 'Protocol ID')
exRow.addCell(3, 'CTGov ID')
exRow.addCell(4, 'Official Title')
exRow.addCell(5, 'HP Title')
exRow.addCell(6, 'IND Num')
exRow.addCell(7, 'IND SN')
exRow.addCell(8, 'Pub Date')
exRow.addCell(9, 'Status')

# Add the protocol data one record at a time beginning after 
# the header row
# ----------------------------------------------------------
rowNum = 1
for row in rows:
    rowNum += 1
    exRow = ws.addRow(rowNum, style1, 40)
    url = ("http://www.cancer.gov/clinicaltrials/"
           "view_clinicaltrials.aspx?version=healthprofessional&"
           "cdrid=%d" % row[0])
    exRow.addCell(1, row[0], href = url, style = style4)
    exRow.addCell(2, row[1], style = style2)
    exRow.addCell(3, row[2], style = style2)
    exRow.addCell(4, row[3], style = style2)
    exRow.addCell(5, row[4], style = style2)
    exRow.addCell(6, row[5], style = style2)
    exRow.addCell(7, row[6], style = style2)
    exRow.addCell(8, row[7], style = style2)
    exRow.addCell(9, row[8], style = style2)

print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=%s" % filename
print

wb.write(sys.stdout)

# # Save the Report
# # ---------------
# fobj = file(fullname, "w")
# wb.write(fobj)
# print ""
# print "  Report written to %s" % fullname
# fobj.close() 
