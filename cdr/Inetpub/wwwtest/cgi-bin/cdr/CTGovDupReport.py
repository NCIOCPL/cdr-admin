#----------------------------------------------------------------------
#
# $Id: CTGovDupReport.py,v 1.2 2003-12-18 13:56:32 bkline Exp $
#
# List of ClinicalTrials.gov documents which are duplicates of
# documents already in the CDR.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2003/12/16 16:07:02  bkline
# List of ClinicalTrials.gov documents which are duplicates of
# documents already in the CDR.
#
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
cursor.execute("""\
  SELECT i.nlm_id, i.title, i.dt
    FROM ctgov_import i
    JOIN ctgov_disposition d
      ON d.id = i.disposition
   WHERE d.name = 'duplicate'
     AND i.title IS NOT NULL
ORDER BY i.nlm_id""")
rows = cursor.fetchall()

#----------------------------------------------------------------------
# Generate the report.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>ClinicalTrials.gov Duplicate Trials Report %s</title>
  <style type='text/css'>
   body { font-family: Arial }
   h1   { font-size: 14pt; font-weight: bold }
   h2   { font-size: 12pt; font-weight: bold }
  </style>
 </head>
 <body>
  <center>
   <h1>ClinicalTrials.gov Duplicate Trials Report</h1>
   <h2>%s</h2>
   <br><br>
  </center>
  <h2>Trials marked as duplicates by CIAT: %d</h2>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th align='left'>NCTID</th>
    <th align='left'>Date Reviewed</th>
    <th align='left'>DocTitle</th>
   </tr>
""" % (time.strftime("%H:%M:%S"), time.strftime("%Y-%m-%d"), len(rows))

for row in rows:
    nctid = row[0] or "&nbsp;"
    docTitle = row[1] or "&nbsp;"
    dateReviewed = row[2] and row[2][:10] or "&nbsp;"
    html += """\
   <tr>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
   </tr>
""" % (nctid, dateReviewed, docTitle)

cursor.execute("""\
  SELECT i.nlm_id, i.cdr_id
    FROM ctgov_import i
    JOIN ctgov_disposition d
      ON d.id = i.disposition
   WHERE d.name = 'duplicate'
     AND i.title IS NULL
ORDER BY i.nlm_id""")
rows = cursor.fetchall()
if rows:
    html += """\
  </table>
  <br>
  <h2>Trials marked as duplicates prior to CTGOV imports: %d</h2>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th align='left'>NCTID</th>
    <th align='left'>DocTitle</th>
   </tr>
""" % len(rows)  
for row in rows:
    docTitle = "&nbsp;"
    if row[1]:
        cursor.execute("SELECT title FROM document WHERE id = ?", row[1])
        titleRows = cursor.fetchall()
        if titleRows:
            docTitle = titleRows[0][0]
    nctid = row[0] or "&nbsp;"
    html += """\
   <tr>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
   </tr>
""" % (nctid, docTitle)
cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>""")
