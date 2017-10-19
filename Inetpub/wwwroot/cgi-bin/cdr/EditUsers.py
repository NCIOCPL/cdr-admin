#----------------------------------------------------------------------
# Interface for managing CDR user accounts
#----------------------------------------------------------------------
import cgi
import cdr
import cdrdb
import cdrcgi

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
# Retrieve the list of users from the server.
#----------------------------------------------------------------------
query = cdrdb.Query("open_usr", "name", "fullname")
query.where("expired IS NULL OR expired > GETDATE()")
rows = query.order("name").execute().fetchall()

#----------------------------------------------------------------------
# Put up the list of users.
#----------------------------------------------------------------------
nUsers = 0
USERS_PER_ROW = 5
menu = "<INPUT TYPE='hidden' NAME='%s' VALUE='%s'><TABLE>\n" % (cdrcgi.SESSION,
                                                                session)
padding = "<TD>&nbsp;&nbsp;</TD>"

for user, fullname in rows:
    if fullname == "Alan Meyer":
        colors = "red", "green", "blue", "violet", "white", "yellow", "orange"
        letters = ['<span style="color: {}">{}</span>'
                   .format(colors[i % len(colors)], fullname[i])
                   for i in range(len(fullname))]
        fullname = "".join(letters)
    if nUsers % USERS_PER_ROW == 0:
        menu += "<TR>%s" % padding
    menu += """\
  <TD><A HREF="%s/EditUser.py?%s=%s&usr=%s"><B>%s</B></A><br>%s</TD>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session, cgi.escape(user, 1),
       user, fullname)
    nUsers += 1
    if nUsers % USERS_PER_ROW == 0: menu += "</TR>\n"
if nUsers % USERS_PER_ROW > 0: menu += "</TR>\n"
menu += """\
<TR><TD COLSPAN="3">&nbsp;</TD></TR>
<TR>%s<TD COLSPAN='3'><A HREF="%s/EditUser.py?%s=%s"><B>%s</B></A> %s</TD></TR>
<TR>%s<TD COLSPAN='3'><A HREF="%s/Logout.py?%s=%s"><B>%s</B></A></TD></TR>
""" % (padding, cdrcgi.BASE, cdrcgi.SESSION, session, "ADD NEW USER",
       "(Use same ID as NIH user ID)",
       padding, cdrcgi.BASE, cdrcgi.SESSION, session, "LOG OUT")
menu += "</TABLE>\n"

cdrcgi.sendPage(header + menu + "</FORM></BODY></HTML>")
