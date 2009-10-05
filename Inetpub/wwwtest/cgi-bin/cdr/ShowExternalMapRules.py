#----------------------------------------------------------------------
#
# $Id: ShowExternalMapRules.py,v 1.1 2006-05-04 15:19:04 bkline Exp $
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, cdrcgi, xml.sax.saxutils

def fix(me):
    return xml.sax.saxutils.escape(me)

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
    SELECT r.element, r.value, u.name, d.id, d.title, m.value
      FROM external_map_rule r
      JOIN external_map m
        ON m.id = r.map_id
      JOIN external_map_usage u
        ON u.id = m.usage
      JOIN document d
        ON d.id = m.doc_id
  ORDER BY u.name, r.value, r.element""")
html = u"""\
<html>
 <head>
  <title>External Map Rules</title>
 </head>
 <body>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>Usage</th>
    <th>External Value</th>
    <th>Doc ID</th>
    <th>Doc Title</th>
    <th>Element</th>
    <th>Rule Value</th>
   </tr>
"""
for row in cursor.fetchall():
    html += u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (row[2], fix(row[5]), row[3], fix(row[4]), row[0], fix(row[1]))
html += u"""\
  </table>
 </body>
</html>"""
cdrcgi.sendPage(html)
