#----------------------------------------------------------------------
#
# $Id: 
#
# List of ClinicalTrials.gov documents which have a publishable version
# later than the latest published version.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, time, cgi, cdrcgi, re

#----------------------------------------------------------------------
# Establish a database connection.
#----------------------------------------------------------------------
conn = cdrdb.connect()
cursor = conn.cursor()

#----------------------------------------------------------------------
# Gather the report data.
#----------------------------------------------------------------------
cursor.execute("CREATE TABLE #t1 (id INTEGER, ver INTEGER)")
conn.commit()
cursor.execute("CREATE TABLE #t2 (id INTEGER, ver INTEGER)")
conn.commit()
cursor.execute("""\
    INSERT INTO #t1
         SELECT d.doc_id, MAX(d.doc_version)
           FROM pub_proc_doc d
           JOIN pub_proc p
             ON p.id = d.pub_proc
           JOIN document
             ON document.id = d.doc_id
           JOIN doc_type t
             ON t.id = document.doc_type
          WHERE t.name = 'CTGovProtocol'
            AND (d.failure IS NULL
             OR  d.failure <> 'Y')
            AND (d.removed IS NULL
             OR  d.removed <> 'Y')
            AND p.status = 'Success'
            AND document.active_status = 'A'
       GROUP BY d.doc_id""")
conn.commit()
cursor.execute("""\
    INSERT INTO #t2
         SELECT v.id, MAX(v.num)
           FROM doc_version v
           JOIN #t1
             ON v.id = #t1.id
          WHERE v.publishable = 'Y'
       GROUP BY v.id""")
conn.commit()
cursor.execute("""
         SELECT #t2.id, #t2.ver
           FROM #t2
           JOIN #t1
             ON #t1.id = #t2.id
          WHERE #t1.ver < #t2.ver
       ORDER BY #t2.id""")
rows = cursor.fetchall()

#----------------------------------------------------------------------
# Generate the report.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>CTGovProtocols New Publishable Version Report %s</title>
  <style type='text/css'>
   body { font-family: Arial }
   h1   { font-size: 14pt; font-weight: bold }
   h2   { font-size: 12pt; font-weight: bold }
  </style>
 </head>
 <body>
  <center>
   <h1>CTGovProtocols New Publishable Version Report</h1>
   <h2>%s</h2>
   <br><br>
  </center>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>DocId</th>
   </tr>
""" % (time.strftime("%Y-%m-%d"), time.strftime("%Y-%m-%d"))

for row in rows:
    html += """\
   <tr>
    <td align='right'>%d</td>
   </tr>
""" % (row[0],)

cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>""")
