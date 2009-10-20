#----------------------------------------------------------------------
#
# $Id$
#
# Report identifying previously published protocols that should be 
# included in a hotfix.
#
# $Log: not supported by cvs2svn $
# Revision 1.8  2005/08/17 20:00:59  venglisc
# Removed the commented out sections since the new code has been approved
# and is running in production. (Bug 1718)
#
# Revision 1.7  2005/08/02 20:28:02  bkline
# Version approved by users for issue #1718.
#
# Revision 1.6  2005/07/14 09:57:35  bkline
# Changes made for issue #1718.
#
# Revision 1.5  2005/03/16 17:20:11  venglisc
# Corrected some problems in the queries to eliminate incorrect hits.
# Added another worksheet to include new CTGovProtocols.
# Modified the output file from HotFixReport to InterimUpdateReport.
# Added the prtocol type to the list of removed protocols. (Bugs 1396, 1538)
#
# Revision 1.4  2004/07/13 17:48:44  bkline
# Modified query to use only publishing jobs sent to Cancer.gov.
#
# Revision 1.3  2004/06/02 14:59:10  bkline
# Logic changes requested by Sheri (comment #18 in request #1183).
#
# Revision 1.2  2004/05/17 14:29:30  bkline
# Bumped up timeout values; fixed typo in column header; added extra
# blank worksheet; removed dead code.
#
# Revision 1.1  2004/05/11 17:49:27  bkline
# Report identifying previously published protocols that should be
# included in a hotfix.
#
#----------------------------------------------------------------------
import cdrdb, pyXLWriter, sys, time, cdrcgi

def addWorksheet(workbook, title, headers, widths, headerFormat, rows):
    worksheet = workbook.add_worksheet(title)
    for col in range(len(headers)):
        worksheet.set_column(col, widths[col])
        worksheet.write([0, col], headers[col], headerFormat)
    #worksheet.set_column(3, 70)
    #worksheet.write([0, 3], "URL", headerFormat)
    r = 1
    for row in rows:
        c = 0
        for col in row:
            if type(col) == type(9):
                col = `col`
            elif type(col) == type(u""):
                col = col.encode('latin-1', 'replace')
            if 0 and c == 2:
                worksheet.write([r, c], col, datefmt)
            elif c == 1:
                url = ("http://%s/cgi-bin/cdr/PublishPreview.py"
                       "?DocId=CDR%d&Session=guest" % (cdrcgi.WEBSERVER,
                                                       row[0]))
                worksheet.write_url([r, c], url, col)
            else:
                worksheet.write([r, c], col)
            c += 1
        #worksheet.write([r, c], url)
        r += 1
    #sys.stderr.write("Created worksheet %s\n" % title)

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

conn = cdrdb.connect('CdrGuest')
conn.setAutoCommit()
cursor = conn.cursor()

# Creating table of all InScopeProtocol and CTGovProtocol documents
# that have been published (and pushed to Cancer.gov)
# We start looking from the last successfull pushing job of the 
# full data set since there may be documents that were dropped
# because of that and did not have a removal record in the 
# pub_proc_doc table
# ------------------------------------------------------------------
cursor.execute("""\
    CREATE TABLE #t0
             (id INTEGER     NOT NULL,
             job INTEGER     NOT NULL,
        doc_type VARCHAR(32) NOT NULL,
   active_status CHAR        NOT NULL)""")

cursor.execute("""\
    INSERT INTO #t0
         SELECT a.id, MAX(p.id), t.name, a.active_status
           FROM all_docs a
           JOIN doc_type t
             ON a.doc_type = t.id
           JOIN pub_proc_doc d
             ON d.doc_id = a.id
           JOIN pub_proc p
             ON p.id = d.pub_proc
          WHERE t.name IN ('InScopeProtocol', 'CTGovProtocol')
            AND (d.failure IS NULL OR d.failure <> 'Y')
            AND p.status = 'Success'
            AND p.pub_subset LIKE 'Push_Documents_To_Cancer.Gov%'
            AND P.id >= (SELECT max(id)
                           FROM pub_proc
                          WHERE pub_subset = 'Push_Documents_to_Cancer.Gov_Full-Load'
                            AND status = 'Success'
                        )
       GROUP BY a.id, t.name, a.active_status""", timeout = 300)

# Create a temp table listing all documents created under #t0 along
# with it's published version number
# -----------------------------------------------------------------
cursor.execute("""\
    CREATE TABLE #t1
             (id INTEGER     NOT NULL,
             ver INTEGER     NOT NULL,
             job INTEGER     NOT NULL,
        doc_type VARCHAR(32) NOT NULL,
   active_status CHAR        NOT NULL,
         removed CHAR        NOT NULL)
""")

cursor.execute("""\
    INSERT INTO #t1
         SELECT p.doc_id, p.doc_version, t.job, 
                t.doc_type, t.active_status, p.removed
           FROM pub_proc_doc p
           JOIN #t0 t
             ON p.doc_id = t.id
            AND p.pub_proc = t.job""", timeout = 300)

# Create a temp table with all the existing latest valid versions
# These are either the same version numbers as the ones created under
# #t1 because no other publishable version has been saved since the last
# publishing or the version numbers are different in which case they 
# may need to be published.
# ----------------------------------------------------------------------
cursor.execute("CREATE TABLE #t2 (id INTEGER, ver INTEGER)")

cursor.execute("""\
    INSERT INTO #t2
         SELECT v.id, MAX(v.num)
           FROM doc_version v
           JOIN #t1
             ON v.id = #t1.id
          WHERE v.publishable = 'Y'
            AND v.val_status = 'V'
       GROUP BY v.id""", timeout = 300)

#----------------------------------------------------------------------
# New code, RMK 2005-06-15.
#----------------------------------------------------------------------

#----------------------------------------------------------------------
# Find last full publication to Cancer.gov.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT MAX(id)
      FROM pub_proc
     WHERE pub_subset = 'Push_Documents_to_Cancer.Gov_Full-Load'
       AND status = 'Success'""")
rows = cursor.fetchall()
if not rows:
    cdrcgi.bail("failure finding last full push")
lastFullPush = rows[0][0]

#----------------------------------------------------------------------
# Find the last version we published for the protocols.
#----------------------------------------------------------------------
cursor.execute("CREATE TABLE #last_published (id INTEGER, ver INTEGER)")
cursor.execute("""\
    INSERT INTO #last_published
         SELECT d.doc_id, MAX(d.doc_version)
           FROM primary_pub_doc d
           JOIN active_doc a
             ON a.id = d.doc_id
           JOIN doc_type t
             ON a.doc_type = t.id
          WHERE t.name IN ('InScopeProtocol', 'CTGovProtocol')
            AND d.pub_proc >= ?
       GROUP BY d.doc_id""", lastFullPush, timeout = 300)

#----------------------------------------------------------------------
# Get the last publishable versions for these documents.
#----------------------------------------------------------------------
cursor.execute("CREATE TABLE #last_publishable (id INTEGER, ver INTEGER)")
cursor.execute("""\
    INSERT INTO #last_publishable
         SELECT v.id, MAX(v.num)
           FROM doc_version v
           JOIN #last_published p
             ON p.id = v.id
          WHERE v.publishable = 'Y'
            AND v.val_status = 'V'
       GROUP BY v.id""", timeout = 300)

#----------------------------------------------------------------------
# Find InScopeProtocol documents with newer publishable versions.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT v2.id, i.value, v3.dt
      FROM #last_published v1
      JOIN #last_publishable v2
        ON v1.id = v2.id
      JOIN doc_version v3
        ON v3.id = v2.id
       AND v3.num = v2.ver
      JOIN query_term i
        ON i.doc_id = v3.id
     WHERE i.path = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
       AND v2.ver > v1.ver
  ORDER BY v3.dt""", timeout = 300)
rows = cursor.fetchall()


t = time.strftime("%Y%m%d%H%M%S")
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=InterimUpdateReport-%s.xls" % t
print 

workbook = pyXLWriter.Writer(sys.stdout)

format = workbook.add_format()
format.set_bold();
format.set_color('white')
format.set_bg_color('blue')
format.set_align('center')

# Create worksheet listing all updated InScopeProtocols
# -----------------------------------------------------
titles  = ('Updated InScopeProtocols', 'Updated CTGov Protocols',
           'New CTGov Protocols',
           'Removed Protocols (All)', 'Updated Summaries')
headers = ['DocID', 'Primary Protocol ID','Latest Publishable Version Date']
widths  = (8, 35, 40)
addWorksheet(workbook, titles[0], headers, widths, format, rows)

#----------------------------------------------------------------------
# Find InScopeProtocol documents with newer publishable versions.
# [New code 2005-06-15.]
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT v2.id, i.value, v3.dt
      FROM #last_published v1
      JOIN #last_publishable v2
        ON v1.id = v2.id
      JOIN doc_version v3
        ON v3.id = v2.id
       AND v3.num = v2.ver
      JOIN query_term i
        ON i.doc_id = v3.id
     WHERE i.path = '/CTGovProtocol/IDInfo/OrgStudyID'
       AND v2.ver > v1.ver
  ORDER BY v3.dt""", timeout = 300)
rows = cursor.fetchall()

addWorksheet(workbook, titles[1], headers, widths, format, rows)

# Create Worksheet for new CTGov Protocol
# Note: These queries are taken from the program 
#       NewlyPublishableTrials.py
#       CIAT requested to include a modified form of the output to this
#       Interim Update report.
# ---------------------------------------
# Create table listing all CTGov Protocols that are publishable
# -------------------------------------------------------------
cursor.execute("""\
    CREATE TABLE #publishable
             (id INTEGER      NOT NULL,
             ver INTEGER      NOT NULL,
        doc_type VARCHAR(32)  NOT NULL,
          status VARCHAR(255) NOT NULL,
        ver_date DATETIME         NULL)""")

cursor.execute("""\
    INSERT INTO #publishable (id, ver, doc_type, status)
SELECT DISTINCT d.id, MAX(v.num), t.name, s.value
           FROM active_doc d
           JOIN doc_type t  
             ON d.doc_type = t.id
           JOIN doc_version v    
             ON v.id = d.id      
           JOIN query_term s     
             ON s.doc_id = d.id  
          WHERE t.name IN ('CTGovProtocol')
            AND v.publishable = 'Y'
            AND s.path IN ('/CTGovProtocol/OverallStatus')
            AND s.value <> 'Withdrawn'
       GROUP BY d.id, t.name, s.value""", timeout = 300)

# Update the #publishable table to add the publication date
# ---------------------------------------------------------
cursor.execute("""\
    UPDATE #publishable
       SET ver_date = v.dt
      FROM #publishable d   
      JOIN doc_version v    
        ON d.id = v.id      
       AND d.ver = v.num""")

# Create table listing all protocol documents already published.
# --------------------------------------------------------------
cursor.execute("""\
         CREATE TABLE #published (id INTEGER NOT NULL)""")

cursor.execute("""\
    INSERT INTO #published
SELECT DISTINCT d.doc_id  
           FROM pub_proc_doc d
           JOIN #publishable t
             ON t.id = d.doc_id
           JOIN pub_proc p
             ON p.id = d.pub_proc
          WHERE p.pub_subset LIKE 'Push_Documents_To_Cancer.Gov_%'
            AND p.pub_subset <> 'Push_Documents_To_Cancer.Gov_Hotfix-Remove'
            AND p.status = 'Success'
            AND p.completed IS NOT NULL
            AND (d.failure IS NULL OR d.failure <> 'Y')""", timeout = 300)

# Create table listing the diff between published and publishable 
# documents.  These will be all documents that are still unpublished.
# -------------------------------------------------------------------
cursor.execute("""\
         CREATE TABLE #unpublished (id INTEGER NOT NULL)""")

cursor.execute("""\
    INSERT INTO #unpublished
         SELECT id
           FROM #publishable
          WHERE id NOT IN (SELECT id FROM #published)""", timeout = 300)

# Create worksheet listing all to-be published CTGov Protocols
# ------------------------------------------------------------
cursor.execute("""\
         SELECT p.id, q.value, p.ver_date
           FROM #publishable p
           JOIN #unpublished u
             ON u.id = p.id
           JOIN query_term q
             ON p.id = q.doc_id
          WHERE q.path = '/CTGovProtocol/IDInfo/OrgStudyID'
          ORDER BY p.ver_date""", timeout = 300)
rows = cursor.fetchall()

addWorksheet(workbook, titles[2], headers, widths, format, rows)

# Create worksheet listing all removed protocols
# ----------------------------------------------
cursor.execute("""\
    SELECT #t1.id, q.value, v.dt, 
           CASE q.path 
                WHEN '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
                THEN 'InScopeProtocol'
                ELSE 'CTGovProtocol'
           END
      FROM #t1
      JOIN #t2
        ON #t1.id = #t2.id
      JOIN query_term q
        ON q.doc_id = #t1.id
      JOIN doc_version v
        ON v.id = #t2.id
       AND v.num = #t2.ver
     WHERE q.path IN ('/InScopeProtocol/ProtocolIDs/PrimaryID/IDString',
                      '/CTGovProtocol/IDInfo/OrgStudyID')
       AND #t1.active_status <> 'A'
       AND (#t1.removed IS NULL OR #t1.removed <> 'Y')
     ORDER BY q.path, v.dt""", timeout = 300)
rows = cursor.fetchall()
addWorksheet(workbook, titles[3], headers, widths, format, rows)

# Create empty Summary worksheet
# ------------------------------
headers[1] = 'Summary Title'
addWorksheet(workbook, titles[4], headers, widths, format, [])

workbook.close()
