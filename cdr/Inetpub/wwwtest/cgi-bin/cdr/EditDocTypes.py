#----------------------------------------------------------------------
#
# $Id: EditDocTypes.py,v 1.1 2001-06-13 22:16:32 bkline Exp $
#
# Prototype for editing CDR groups.
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
title   = "CDR Administration"
section = "Manage Document Types"
buttons = []
header  = cdrcgi.header(title, title, section, "", buttons)

#----------------------------------------------------------------------
# Make sure the login was successful.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

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
""" % (cdrcgi.BASE, cdrcgi.SESSION, session,
       cdrcgi.BASE, cdrcgi.SESSION, session)
cdrcgi.sendPage(header + menu + "</BODY></HTML>")
