#----------------------------------------------------------------------
#
# $Id: EditActions.py,v 1.2 2002-02-21 15:22:02 bkline Exp $
#
# Prototype for editing CDR groups.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2001/06/13 22:16:32  bkline
# Initial revision
#
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, urllib

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
title   = "CDR Administration"
section = "Manage Actions"
buttons = [cdrcgi.MAINMENU]
header  = cdrcgi.header(title, title, section, "EditActions.py", buttons)

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
actions = cdr.getActions(session)
if type(actions) == type(""): cdrcgi.bail(actions)

#----------------------------------------------------------------------
# Put up the list of actions.
#----------------------------------------------------------------------
nActions = 0
ACTIONS_PER_ROW = 3
menu = "<TABLE>\n"
padding = "<TD>&nbsp;&nbsp;</TD>"

actions = list(actions.keys())
actions.sort()
for action in actions:
    if nActions % ACTIONS_PER_ROW == 0:
        menu += "<TR>%s" % padding
    menu += """\
  <TD><A HREF="%s/EditAction.py?%s=%s&action=%s"><B>%s</B></A></TD>%s%s
""" % (cdrcgi.BASE, cdrcgi.SESSION, session, urllib.quote_plus(action), 
       action, padding, padding)
    nActions += 1
    if nActions % ACTIONS_PER_ROW == 0: menu += "</TR>\n"
menu += """\
</TABLE>
<HR>
<TABLE>
<TR>%s<TD COLSPAN='3'><A HREF="%s/EditAction.py?%s=%s"><B>%s</B></A></TD></TR>
<TR>%s<TD COLSPAN='3'><A HREF="%s/Logout.py?%s=%s"><B>%s</B></A></TD></TR>
</TABLE>
<INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
""" % (padding, cdrcgi.BASE, cdrcgi.SESSION, session, "ADD NEW ACTION",
       padding, cdrcgi.BASE, cdrcgi.SESSION, session, "LOG OUT",
       cdrcgi.SESSION, session)

cdrcgi.sendPage(header + menu + "</FORM></BODY></HTML>")
