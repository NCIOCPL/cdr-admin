#----------------------------------------------------------------------
#
# $Id: ExternMapFailures.py,v 1.1 2003-11-10 18:01:15 bkline Exp $
#
# Report on values found in external systems (such as ClinicalTrials.gov)
# which have not yet been mapped to CDR documents.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, cdrcgi

#----------------------------------------------------------------------
# Establish a database connection.
#----------------------------------------------------------------------
conn = cdrdb.connect()
cursor = conn.cursor()

#----------------------------------------------------------------------
# Gather the report data.
#----------------------------------------------------------------------
cursor.execute("""\
  SELECT u.name, m.value, m.last_mod
    FROM external_map m
    JOIN external_map_usage u
      ON u.id = m.usage
   WHERE doc_id IS NULL
ORDER BY u.name, m.value""")
row = cursor.fetchone()
if not row:
    cdrcgi.bail("No unmapped values found")
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>External Map Failures</title>
  <style type='text/css'>
   body { font-family: Arial; }
  </style>
 </head>
 <body>
  <h2>External Map Failures</h2>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>Usage</th>
    <th>Value</th>
    <th>Recorded</th>
   </tr>
"""
while row:
    html += """\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (row[0], row[1].encode('utf-8'), row[2])
    row = cursor.fetchone()
cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>""")
