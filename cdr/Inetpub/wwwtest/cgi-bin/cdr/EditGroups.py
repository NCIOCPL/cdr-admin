#----------------------------------------------------------------------
#
# $Id: EditGroups.py,v 1.2 2002-02-20 23:59:44 bkline Exp $
#
# Prototype for editing CDR groups.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2001/06/13 22:16:32  bkline
# Initial revision
#
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, sys, urllib

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
title   = "CDR Administration"
section = "Manage Groups"
buttons = ["Return to Admin Main Menu"]
header  = cdrcgi.header(title, title, section, "EditGroups.py", buttons)

#----------------------------------------------------------------------
# Make sure the login was successful.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Return to the main menu if requested.
#----------------------------------------------------------------------
if action == "Return to Admin Main Menu":
    where = "http://%s%s/Admin.py?%s=%s" % (cdrcgi.WEBSERVER,
                                            cdrcgi.BASE,
                                            cdrcgi.SESSION,
                                            session)
    #cdrcgi.bail(where)
    print "Location:%s\n" % where
    sys.exit(0)

#----------------------------------------------------------------------
# Retrieve the list of groups from the server.
#----------------------------------------------------------------------
groups = cdr.getGroups(session)
if type(groups) == type("") or type(groups) == type(u""): cdrcgi.bail(groups)

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
menu += "<INPUT TYPE='hidden' NAME='%s' VALUE='%s'>" % (cdrcgi.SESSION,
                                                       session)
cdrcgi.sendPage(header + menu + "</FORM></BODY></HTML>")
