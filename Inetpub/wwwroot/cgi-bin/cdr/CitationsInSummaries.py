#----------------------------------------------------------------------
# Report listing all citations linked by a summary document.
# The output format is an Excel workbook.
# BZIssue-2040
#----------------------------------------------------------------------
import sys
import time
import cdrcgi
from cdrapi import db
from cdrapi.settings import Tier

ROW_HEIGHT = 40 # in point size

#if sys.platform == "win32":
#    import os, msvcrt
#    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

conn = db.connect(user="CdrGuest")
cursor = conn.cursor()

#----------------------------------------------------------------------
# Identify the Citation documents for the report.
#----------------------------------------------------------------------
cursor.execute("""\
SELECT distinct d.id CDRID, d.title
  FROM query_term q
  JOIN active_doc d
    ON d.id = q.int_val
  JOIN active_doc s
    ON s.id = q.doc_id
 WHERE path like '/Summary/%CitationLink/@cdr:ref'
 ORDER BY d.id desc
""")
rows = cursor.fetchall()

# Create the spreadsheet and define default style, etc.
# -----------------------------------------------------
styles = cdrcgi.ExcelStyles()
sheet = styles.add_sheet("Citations in Summaries")

# Set the colum widths
# -------------------
sheet.col(0).width = styles.chars_to_width(10)
sheet.col(1).width = styles.chars_to_width(100)

# Create the Header row
# ---------------------
styles.set_row_height(sheet.row(0), ROW_HEIGHT)
sheet.write(0, 0, "CDR-ID", styles.header)
sheet.write(0, 1, "Citation Title", styles.header)

# Add the protocol data one record at a time beginning after
# the header row. Link to the production server.
# ----------------------------------------------------------
row = 1
base = f"https://{Tier('PROD').hosts['APPC']}{cdrcgi.BASE}/QcReport.py"
#"%s?Session=guest" % db.h.makeCdrCgiUrl("PROD", "QCReport.py")
for doc_id, doc_title in rows:
    styles.set_row_height(sheet.row(row), ROW_HEIGHT)
    url = f"{base}?Session=guest&DocId={doc_id:d}"
    link = styles.link(url, doc_id)
    sheet.write(row, 0, link, styles.url)
    sheet.write(row, 1, doc_title, styles.left)
    row += 1

name = "CitationsInSummaries-%s.xls" % time.strftime("%Y%m%d%H%M%S")
sys.stdout.buffer.write(f"""\
Content-type: application/vnd.ms-excel
Content-Disposition: attachment; filename={name}

""".encode("utf-8"))
styles.book.save(sys.stdout.buffer)
