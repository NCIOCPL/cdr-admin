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
section = "Manage Document Types"
buttons = [cdrcgi.MAINMENU]
header  = cdrcgi.header(title, title, section, "EditDocTypes.py", buttons)

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
doctypes = cdr.getDoctypes(session)
if type(doctypes) == type(""): cdrcgi.bail(doctypes)

#----------------------------------------------------------------------
# Put up the main menu.
#----------------------------------------------------------------------
menu = "<OL>\n"
for doctype in doctypes:
    if doctype == "ProtocolSourceDoc": continue
    menu += """\
  <LI><A HREF="%s/EditDoctype.py?%s=%s&doctype=%s&%s">%s</A></LI>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session, cgi.escape(doctype, 1),
       "request=Fetch", doctype)
menu += """\
  <LI><A HREF="%s/EditDoctype.py?%s=%s">Add New Doctype</A></LI>
  <LI><A HREF="%s/Logout.py?%s=%s">Log Out</A></LI>
 </OL>
 <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session,
       cdrcgi.BASE, cdrcgi.SESSION, session,
       cdrcgi.SESSION, session)
cdrcgi.sendPage(header + menu + "</BODY></HTML>")
