#----------------------------------------------------------------------
#
# $Id: EditGroups.py,v 1.1 2001-06-13 22:16:32 bkline Exp $
#
# Prototype for editing CDR groups.
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, urllib

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
title   = "CDR Administration"
section = "Manage Groups"
buttons = []
header  = cdrcgi.header(title, title, section, "", buttons)

#----------------------------------------------------------------------
# Make sure the login was successful.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Retrieve the list of groups from the server.
#----------------------------------------------------------------------
groups = cdr.getGroups(session)
if type(groups) == type(""): cdrcgi.bail(groups)

#----------------------------------------------------------------------
# Put up the main menu.
#----------------------------------------------------------------------
SESSION = "?%s=%s" % (cdrcgi.SESSION, session)

menu = "<OL>\n"
for group in groups:
    menu += """\
  <LI><A HREF="%s/EditGroup.py?%s=%s&grp=%s">%s</A></LI>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session, urllib.quote_plus(group), group)
menu += """\
  <LI><A HREF="%s/EditGroup.py?%s=%s">%s</A></LI>
  <LI><A HREF="%s/Logout.py?%s=%s">%s</A></LI>
 </OL>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session, "ADD NEW GROUP",
       cdrcgi.BASE, cdrcgi.SESSION, session, "LOG OUT")
menu += "</OL>"

cdrcgi.sendPage(header + menu + "</BODY></HTML>")
