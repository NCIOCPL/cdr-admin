#----------------------------------------------------------------------
# Tools used for tracking down what really happened when a user
# reports anomalies in stored versions of CDR documents.
#----------------------------------------------------------------------
import cgi, cdr
from cdrapi import db

fields = cgi.FieldStorage()
start  = fields.getvalue('start') or str(cdr.calculateDateByOffset(-7))
end    = fields.getvalue('end')   or str(cdr.calculateDateByOffset(0))
user   = fields.getvalue('user')  or '%'
cursor = db.connect(user='CdrGuest').cursor()
sqlEnd = len(end) == 10 and ("%s 23:59:59" % end) or end

cursor.execute("""\
    SELECT u.name, u.fullname, c.event_time, c.event_desc, s.id, s.name
      FROM client_log c
      JOIN session s
        ON c.session = s.id
      JOIN usr u
        ON u.id = s.usr
     WHERE c.event_time BETWEEN '%s' AND '%s'
       AND u.name LIKE '%s'
  ORDER BY c.event_id""" % (start, sqlEnd, user))
html = [u"""\
<html>
 <head>
  <title>CDR Client Events</title>
  <style>* { font-family: Arial, sans-serif }</style>
 </head>
 <body>
  <h1>CDR Client Events %s &mdash; %s</h1>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>User ID</th>
    <th>User Name</th>
    <th>Event Time</th>
    <th>Event Description</th>
    <th>Session ID</th>
    <!--
    <th>Session Name</th>
    -->
   </tr>
""" % (start, end)]
for uId, uName, eTime, eDesc, sId, sName in cursor.fetchall():
    html.append(u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <!-- <td>%s</td> -->
   </tr>
""" % (cgi.escape(uId), cgi.escape(uName), eTime, cgi.escape(eDesc), sId,
       cgi.escape(sName)))
html.append(u"""\
  </table>
 </body>
</html>""")
html = u"".join(html)
print("Content-type: text/html; charset=utf-8")
print("")
print(html.encode('utf-8'))
