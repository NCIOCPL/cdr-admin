#----------------------------------------------------------------------
#
# $Id$
#
# Prototype for editing CDR groups.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2001/06/13 22:16:32  bkline
# Initial revision
#
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
title   = "CDR Administration"
section = "Manage Users"
buttons = [cdrcgi.MAINMENU]
header  = cdrcgi.header(title, title, section, "EditUsers.py", buttons)

#----------------------------------------------------------------------
# Make sure the login was successful.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Return to the main menu if requested.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# Retrieve the list of groups from the server.
#----------------------------------------------------------------------
users = cdr.getUsers(session)
if type(users) == type(""): cdrcgi.bail(users)

#----------------------------------------------------------------------
# Put up the list of users.
#----------------------------------------------------------------------
nUsers = 0
USERS_PER_ROW = 7
menu = "<INPUT TYPE='hidden' NAME='%s' VALUE='%s'><TABLE>\n" % (cdrcgi.SESSION,
                                                                session)
padding = "<TD>&nbsp;&nbsp;</TD>"

for user in users:
    if nUsers % USERS_PER_ROW == 0:
        menu += "<TR>%s" % padding
    menu += """\
  <TD><A HREF="%s/EditUser.py?%s=%s&usr=%s"><B>%s</B></A></TD>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session, cgi.escape(user, 1), user)
    nUsers += 1
    if nUsers % USERS_PER_ROW == 0: menu += "</TR>\n"
if nUsers % USERS_PER_ROW > 0: menu += "</TR>\n"
menu += """\
<TR>%s<TD COLSPAN='3'><A HREF="%s/EditUser.py?%s=%s"><B>%s</B></A></TD></TR>
<TR>%s<TD COLSPAN='3'><A HREF="%s/Logout.py?%s=%s"><B>%s</B></A></TD></TR>
""" % (padding, cdrcgi.BASE, cdrcgi.SESSION, session, "ADD NEW USER",
       padding, cdrcgi.BASE, cdrcgi.SESSION, session, "LOG OUT")
menu += "</TABLE>\n"

cdrcgi.sendPage(header + menu + "</FORM></BODY></HTML>")
