#----------------------------------------------------------------------
#
# $Id$
#
# Report of unpublished CTGov trials by Phase.
# The query originated from the AdHoc query interface.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2006/04/26 17:19:59  venglisc
# Initial copy of report listing unpublished CTGov protocols by phase.
# (Bug 2048)
#
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
SELECT d.id CDRID, q.value Phase, min(a.dt) DateCreated, t.value
  FROM document d
  JOIN query_term q
    ON d.id = q.doc_id
  JOIN audit_trail a
    ON d.id = a.document
  LEFT OUTER JOIN query_term t
    ON d.id = t.doc_id
   AND t.path = '/CTGovProtocol/IDInfo/OrgStudyID'
 WHERE d.doc_type = 34  -- CTGovProtocol
   AND d.active_status = 'A'
   AND q.path = '/CTGovProtocol/Phase'
   AND q.doc_id NOT IN (SELECT DISTINCT id
                          FROM doc_version
                         WHERE publishable = 'Y'
                       )
 GROUP BY d.id, q.value, t.value
 ORDER BY q.value desc, d.id""")
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
