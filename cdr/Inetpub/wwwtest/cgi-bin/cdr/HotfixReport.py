#----------------------------------------------------------------------
#
# $Id: HotfixReport.py,v 1.2 2004-05-17 14:29:30 bkline Exp $
#
# Report identifying previously published protocols that should be 
# included in a hotfix.
#
# $Log: not supported by cvs2svn $
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
cursor.execute("""\
    CREATE TABLE #t1
             (id INTEGER     NOT NULL,
             ver INTEGER     NOT NULL,
        doc_type VARCHAR(32) NOT NULL,
   active_status CHAR        NOT NULL,
         removed CHAR        NOT NULL)
""")
cursor.execute("""\
    INSERT INTO #t1
         SELECT d.doc_id, MAX(d.doc_version), t.name, all_docs.active_status,
                d.removed
           FROM pub_proc_doc d
           JOIN pub_proc p
             ON p.id = d.pub_proc
           JOIN document pub_system
             ON pub_system.id = p.pub_system
           JOIN all_docs
             ON all_docs.id = d.doc_id
           JOIN doc_type t
             ON t.id = all_docs.doc_type
          WHERE t.name IN ('InScopeProtocol', 'CTGovProtocol')
            AND pub_system.title = 'Primary'
            AND (d.failure IS NULL
             OR  d.failure <> 'Y')
            AND p.status = 'Success'
       GROUP BY d.doc_id, t.name, all_docs.active_status, d.removed""",
               timeout = 300)
cursor.execute("CREATE TABLE #t2 (id INTEGER, ver INTEGER)")
cursor.execute("""\
    INSERT INTO #t2
         SELECT v.id, MAX(v.num)
           FROM doc_version v
           JOIN #t1
             ON v.id = #t1.id
          WHERE v.publishable = 'Y'
       GROUP BY v.id""", timeout = 300)
cursor.execute("""\
    SELECT #t1.id, q.value, v.dt
      FROM #t1
      JOIN #t2
        ON #t1.id = #t2.id
      JOIN query_term q
        ON q.doc_id = #t1.id
      JOIN doc_version v
        ON v.id = #t2.id
       AND v.num = #t2.ver
     WHERE q.path = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
       AND #t2.ver > #t1.ver
       AND #t1.active_status = 'A'
       AND #t1.doc_type = 'InScopeProtocol'""", timeout = 300)
rows = cursor.fetchall()

       
t = time.strftime("%Y%m%d%H%M%S")
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=HotfixReport-%s.xls" % t
print 

workbook = pyXLWriter.Writer(sys.stdout)

format = workbook.add_format()
format.set_bold();
format.set_color('white')
format.set_bg_color('blue')
format.set_align('center')
titles  = ('Updated In-Scope Protocols', 'Updated CTGov Protocols',
           'Removed Protocols', 'Updated Summaries')
headers = ['DocID', 'Primary Protocol ID','Latest Publishable Version Date']
widths  = (8, 35, 40)
addWorksheet(workbook, titles[0], headers, widths, format, rows)
cursor.execute("""\
    SELECT #t1.id, q.value, v.dt
      FROM #t1
      JOIN #t2
        ON #t1.id = #t2.id
      JOIN query_term q
        ON q.doc_id = #t1.id
      JOIN doc_version v
        ON v.id = #t2.id
       AND v.num = #t2.ver
     WHERE q.path = '/CTGovProtocol/IDInfo/SecondaryID'
       AND #t2.ver > #t1.ver
       AND #t1.active_status = 'A'
       AND #t1.doc_type = 'CTGovProtocol'""", timeout = 300)
rows = cursor.fetchall()
addWorksheet(workbook, titles[1], headers, widths, format, rows)
cursor.execute("""\
    SELECT #t1.id, q.value, v.dt
      FROM #t1
      JOIN #t2
        ON #t1.id = #t2.id
      JOIN query_term q
        ON q.doc_id = #t1.id
      JOIN doc_version v
        ON v.id = #t2.id
       AND v.num = #t2.ver
     WHERE q.path IN ('/InScopeProtocol/ProtocolIDs/PrimaryID/IDString',
                      '/CTGovProtocol/IDInfo/SecondaryID')
       AND #t1.active_status <> 'A'
       AND (#t1.removed IS NULL OR #t1.removed <> 'Y')""", timeout = 300)
rows = cursor.fetchall()
addWorksheet(workbook, titles[2], headers, widths, format, rows)
headers[1] = 'Summary Title'
addWorksheet(workbook, titles[3], headers, widths, format, [])
workbook.close()
