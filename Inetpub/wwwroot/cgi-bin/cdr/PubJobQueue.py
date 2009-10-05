#----------------------------------------------------------------------
#
# $Id: PubJobQueue.py,v 1.1 2002-04-10 20:09:11 bkline Exp $
#
# Lists incomplete jobs in the publishing queue, with links to the
# status pages for each.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------

import cdr, cdrdb, cdrcgi, cgi, re, string, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
SUBMENU = "Report Menu"
buttons = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "PubJobQueue.py"
title   = "CDR Administration"
section = "Publishing Job Queue"
header  = cdrcgi.header(title, title, section, script, buttons)
now     = time.localtime(time.time())

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
# Close the form and start the html for the list.
#----------------------------------------------------------------------
html = """\
  </FORM>
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  <TABLE BORDER='0'>
   <TR>
    <TD><B>Job ID&nbsp;</B></TD>
    <TD><B>Started&nbsp;</B></TD>
    <TD><B>Status&nbsp;</B></TD>
   </TR>
""" % (cdrcgi.SESSION, session)

try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
    cursor.execute("""\
        SELECT id,
               started,
               status
          FROM pub_proc
         WHERE status NOT IN ('Success', 'Failure')
      ORDER BY id""")
    for row in cursor.fetchall():
        html += """\
   <TR>
    <TD ALIGN='right'>
     <A HREF='%s/PubStatus.py?id=%d&%s=%s'>%d</A>
    </TD>
    <TD>%s</TD>
    <TD>%s</TD>
   </TR>
""" % (cdrcgi.BASE, row[0], cdrcgi.SESSION, session, row[0], row[1], row[2])
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

cdrcgi.sendPage(header + html + """\
   </TABLE>
  </FORM>
 </BODY>
</HTML>
""")
