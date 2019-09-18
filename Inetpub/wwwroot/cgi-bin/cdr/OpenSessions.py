#----------------------------------------------------------------------
# Display of threads which are still running in the CDR Server (mostly
# a debugging tool).
#----------------------------------------------------------------------
import cdrcgi
from cdrapi import db

conn = db.connect()
cursor = conn.cursor()
cursor.execute("""\
        SELECT s.id,
               s.initiated,
               s.last_act,
               u.name,
               u.fullname,
               u.email,
               u.phone
          FROM session s
          JOIN usr u
            ON u.id = s.usr
         WHERE s.ended IS NULL
      ORDER BY s.initiated""")
rows = cursor.fetchall()
html = """\
<html>
 <head>
  <title>Open CDR Sessions</title>
 </head>
 <body>
  <h3>%d Open CDR Sessions</h3>
  <table border=1 cellspacing=0 cellpadding=2>
   <tr>
    <th nowrap=1>ID</th>
    <th>Started</th>
    <th nowrap=1>Last Activity</th>
    <th nowrap=1>User ID</th>
    <th nowrap=1>User Name</th>
    <th nowrap=1>User Email</th>
    <th nowrap=1>User Phone</th>
   </tr>
""" % len(rows)
for row in rows:
    html += """\
   <tr>
    <td align=right>%d</td>
    <td nowrap=1>%s</td>
    <td nowrap=1>%s</td>
    <td nowrap=1>%s</td>
    <td nowrap=1>%s</td>
    <td nowrap=1>%s</td>
    <td nowrap=1>%s</td>
   </tr>
""" % (row[0], row[1], row[2], row[3], row[4], row[5], row[6])
cdrcgi.sendPage( html + """\
  </table>
 </body>
</html>""")
