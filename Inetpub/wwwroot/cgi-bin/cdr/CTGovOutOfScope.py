#----------------------------------------------------------------------
# List of ClinicalTrials.gov documents which are out of scope.
#----------------------------------------------------------------------
import cdr, cdrdb, time, cgi, cdrcgi

#----------------------------------------------------------------------
# Establish a database connection.
#----------------------------------------------------------------------
conn = cdrdb.connect()
cursor = conn.cursor()

#----------------------------------------------------------------------
# Gather the report data.
#----------------------------------------------------------------------
cursor.execute("""\
  SELECT i.nlm_id, i.title, i.cdr_id, i.dt
    FROM ctgov_import i
    JOIN ctgov_disposition d
      ON d.id = i.disposition
   WHERE d.name = 'out of scope'
ORDER BY i.nlm_id""")
rows = cursor.fetchall()

#----------------------------------------------------------------------
# Generate the report.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>ClinicalTrials.gov Out of Scope Trials Report %s</title>
  <style type='text/css'>
   body { font-family: Arial }
   h1   { font-size: 14pt; font-weight: bold }
   h2   { font-size: 12pt; font-weight: bold }
  </style>
 </head>
 <body>
  <center>
   <h1>ClinicalTrials.gov Out of Scope Trials Report</h1>
   <h2>%s</h2>
   <br><br>
  </center>
  <h2>Trials marked as out of scope - %d</h2>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th align='left'>NCTID</th>
    <th align='left'>Date Reviewed</th>
    <th align='left'>DocTitle</th>
   </tr>
""" % (time.strftime("%H:%M:%S"), time.strftime("%Y-%m-%d"), len(rows))
for row in rows:
    docTitle = "&nbsp;"
    if row[1]:
        docTitle = row[1]
    elif row[2]:
        cursor.execute("SELECT title FROM document WHERE id = ?", row[2])
        titleRows = cursor.fetchall()
        if titleRows:
            docTitle = titleRows[0][0]
    dateReviewed = row[3] and row[3][:10] or "&nbsp;"
    nctid = row[0] or "&nbsp;"
    html += """\
   <tr>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
   </tr>
""" % (nctid, dateReviewed, docTitle)
cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>""")
