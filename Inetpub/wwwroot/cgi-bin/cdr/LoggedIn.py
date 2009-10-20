#----------------------------------------------------------------------
#
# $Id$
#
# Display of users currently logged in to the CDR Server.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, cdrcgi

conn = cdrdb.connect('CdrGuest')
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
class User:
    def __init__(self, sessionId, lastLoggedOn, lastActivity, name, fullname,
                 email, phone):
        self.sessionId    = sessionId
        self.lastLoggedOn = lastLoggedOn
        self.lastActivity = lastActivity
        self.name         = name
        self.fullname     = fullname
        self.email        = email
        self.phone        = phone

users = {}
for row in cursor.fetchall():
    user = User(row[0], row[1], row[2], row[3], row[4], row[5], row[6])
    if users.has_key(user.name):
        if user.lastLoggedOn > users[user.name].lastLoggedOn:
            users[user.name] = user
    else:
        users[user.name] = user
html = """\
<html>
 <head>
  <title>Users Currently Logged on to CDR</title>
 </head>
 <body>
  <h3>%d Users Currently Logged on to CDR</h3>
  <table border=1 cellspacing=0 cellpadding=2>
   <tr>
    <th nowrap=1>ID of Most Recent Session</th>
    <th>Started</th>
    <th nowrap=1>Last Activity</th>
    <th nowrap=1>User ID</th>
    <th nowrap=1>User Name</th>
    <th nowrap=1>User Email</th>
    <th nowrap=1>User Phone</th>
   </tr>
""" % len(users)
keys = users.keys()
keys.sort()
for key in keys:
    user = users[key]
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
""" % (user.sessionId, user.lastLoggedOn, user.lastActivity, user.name,
       user.fullname, user.email, user.phone)
cdrcgi.sendPage( html + """\
  </table>
 </body>
</html>""")
