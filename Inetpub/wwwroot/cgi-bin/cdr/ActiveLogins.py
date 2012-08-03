#----------------------------------------------------------------------
#
# $Id$
#
# Reports on current sessions.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, re, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
SUBMENU = "Report Menu"
buttons = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "ActiveLogins.py"
title   = "CDR Administration"
section = "Current Sessions"
header  = cdrcgi.header(title, title, section, script, buttons)

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Get the data.
#----------------------------------------------------------------------
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
    cursor.execute("""\
              SELECT u.name,
                     u.fullname,
                     u.office,
                     u.email,
                     u.phone,
                     s.initiated,
                     s.last_act
                FROM session s
                JOIN usr u
                  ON u.id = s.usr
               WHERE s.ended IS NULL
            ORDER BY s.last_act""")
###            ORDER BY s.initiated""") # original sort order changed - VE
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Create the report.
#----------------------------------------------------------------------
report = """\
  <input type='hidden' name='%s' value='%s'>
  <table border='1' cellspacing='0' cellpadding='2' width='100%%'>
   <tr>
    <td nowrap='1' align='center'>
     <b>
      <font size='3'>Started</font>
     </b>
    </td>
    <td nowrap='1' align='center'>
     <b>
      <font size='3'>User</font>
     </b>
    </td>
    <td nowrap='1' align='center'>
     <b>
      <font size='3'>Login</font>
     </b>
    </td>
    <td nowrap='1' align='center'>
     <b>
      <font size='3'>Office</font>
     </b>
    </td>
    <td nowrap='1' align='center'>
     <b>
      <font size='3'>Email</font>
     </b>
    </td>
    <td nowrap='1' align='center'>
     <b>
      <font size='3'>Phone</font>
     </b>
    </td>
    <td nowrap='1' align='center'>
     <b>
      <font size='3'>Last Activity</font>
     </b>
    </td>
   </tr>
""" % (cdrcgi.SESSION, session)
   
for row in rows:
    report += """\
   <tr>
    <td nowrap='1'>
     <font size='3'>%s</font>
    </td>
    <td nowrap='1'>
     <font size='3'>%s</font>
    </td>
    <td nowrap='1'>
     <font size='3'>%s</font>
    </td>
    <td nowrap='1'>
     <font size='3'>%s</font>
    </td>
    <td nowrap='1'>
     <font size='3'>%s</font>
    </td>
    <td nowrap='1'>
     <font size='3'>%s</font>
    </td>
    <td nowrap='1'>
     <font size='3'>%s</font>
    </td>
   </tr>
""" % (row[5], row[1], row[0], row[2], row[3], row[4], row[6])

cdrcgi.sendPage(header + report + """\
  </table>
 </body>
</html>
""")
