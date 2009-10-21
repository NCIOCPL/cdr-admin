#----------------------------------------------------------------------
#
# $Id$
#
# Report of unpublished CTGov trials by Phase.
# The query originated from the AdHoc query interface.
# Original script written by Volker.
#
# BZIssue::2048
# BZIssue::4666
#
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
    SELECT DISTINCT v.id
               INTO #p
               FROM doc_version v
               JOIN doc_type t
                 ON t.id = v.doc_type
              WHERE t.name = 'CTGovProtocol'
                AND v.publishable = 'Y'""")
cursor.execute("""\
    SELECT v.id, MIN(v.dt) AS dt
      INTO #c
      FROM doc_version v
      JOIN doc_type t
        ON t.id = v.doc_type
     WHERE t.name = 'CTGovProtocol'
  GROUP BY v.id""")
cursor.execute("""\
         SELECT a.id, p.value, #c.dt, i.value
           FROM active_doc a
           JOIN query_term p
             ON p.doc_id = a.id
           JOIN #c
             ON #c.id = a.id
LEFT OUTER JOIN query_term i
             ON i.doc_id = a.id
            AND i.path = '/CTGovProtocol/IDInfo/OrgStudyID'
          WHERE p.path = '/CTGovProtocol/Phase'
            AND a.id NOT IN (SELECT id FROM #p)
       ORDER BY p.value, a.id""")
rows = cursor.fetchall()

#----------------------------------------------------------------------
# Generate the report.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Unpublished ClinicalTrials.gov Trials Report %s</title>
  <style type='text/css'>
   body         { font-family: Arial }
   h1           { font-size: 14pt; font-weight: bold }
   h2           { font-size: 12pt; font-weight: bold }
   .transferred { color: red; font-weight: bold; }
   .normal      { font-weight: normal; }
  </style>
 </head>
 <body>
  <center>
   <h1>Unpublished ClinicalTrials.gov Trials by Phase</h1>
   <h2>%s</h2>
   <br><br>
  </center>
  <h2>Number of unpublished Trials: %d</h2>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th align='left'>CDRID</th>
    <th align='left'>Phase</th>
    <th align='left'>Date Created</th>
   </tr>
""" % (time.strftime("%H:%M:%S"), time.strftime("%Y-%m-%d"), len(rows))

for row in rows:
    cdrid = row[0] or "&nbsp;"
    phase = row[1] or "&nbsp;"
    dateCreated = row[2] and row[2][:10] or "&nbsp;"
    html += """\
   <tr class="%s">
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
   </tr>
""" % (row[3][:3] == 'CDR' and 'transferred' or 'normal',
       cdrid, phase, dateCreated)

cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>""")
