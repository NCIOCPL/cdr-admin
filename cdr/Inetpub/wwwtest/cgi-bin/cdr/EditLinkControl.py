#----------------------------------------------------------------------
#
# $Id: EditLinkControl.py,v 1.1 2001-06-13 22:16:32 bkline Exp $
#
# Prototype for editing CDR linking tables.
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
section = "Manage Linking Tables"
buttons = []
header  = cdrcgi.header(title, title, section, "", buttons)

#----------------------------------------------------------------------
# Put up a stub page for now.
#----------------------------------------------------------------------
form = "<OL>\n"
types = cdr.getLinkTypes(session)
if type(types) == type(""): cdrcgi.bail(types)

for t in types:
    form += "<LI><A HREF='%s/EditLinkType.py?name=%s&%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, t, cdrcgi.SESSION, session, t)

form += """\
<LI><A HREF="%s/EditLinkType.py?%s=%s">%s</LI>
<LI><A HREF="%s/ShowAllLinkTypes.py?%s=%s">%s</LI>
<LI><A HREF="%s/Logout.py?%s=%s">%s</LI>
</OL>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session, "Add New Link Type",
       cdrcgi.BASE, cdrcgi.SESSION, session, "Show All Link Types",
       cdrcgi.BASE, cdrcgi.SESSION, session, "Log Out")
cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")
