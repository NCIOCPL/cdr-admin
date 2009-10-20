#----------------------------------------------------------------------
#
# $Id$
#
# Prototype for CSS stylesheet menu page.
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
section = "Manage CSS Stylesheets"
buttons = [cdrcgi.MAINMENU]
header  = cdrcgi.header(title, title, section, "EditCSSs.py", buttons)

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
styleSheets = cdr.search(session, "CdrCtl/DocType = 'css'")
if type(styleSheets) == type(""): cdrcgi.bail(styleSheets)

#----------------------------------------------------------------------
# Put up the main menu.
#----------------------------------------------------------------------
menu = "<OL>\n"
for styleSheet in styleSheets:
    menu += """\
  <LI><A HREF="%s/EditCSS.py?%s=%s&DocId=%s&%s=Fetch">%s</A></LI>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session, 
       styleSheet.docId, cdrcgi.REQUEST, styleSheet.docTitle)
menu += """\
  <LI><A HREF="%s/EditCSS.py?%s=%s&%s=New">Add New CSS Stylesheet</A></LI>
  <LI><A HREF="%s/Logout.py?%s=%s">Log Out</A></LI>
 </OL>
 <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session, cdrcgi.REQUEST,
       cdrcgi.BASE, cdrcgi.SESSION, session,
       cdrcgi.SESSION, session)
cdrcgi.sendPage(header + menu + "</BODY></HTML>")
