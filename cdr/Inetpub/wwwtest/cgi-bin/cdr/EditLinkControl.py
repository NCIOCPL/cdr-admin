#----------------------------------------------------------------------
#
# $Id: EditLinkControl.py,v 1.3 2002-02-21 15:22:02 bkline Exp $
#
# Prototype for editing CDR linking tables.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2002/02/15 06:48:30  ameyer
# Added URL encoded variables to distinguish calls to EditLinkType.py
# as add or edit calls.
#
# Revision 1.1  2001/06/13 22:16:32  bkline
# Initial revision
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
section = "Manage Linking Tables"
buttons = [cdrcgi.MAINMENU]
header  = cdrcgi.header(title, title, section, "EditLinkControl.py", buttons)

#----------------------------------------------------------------------
# Return to the main menu if requested.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# Put up a stub page for now.
#----------------------------------------------------------------------
form = "<INPUT TYPE='hidden' NAME='%s' VALUE='%s'><OL>\n" % (cdrcgi.SESSION,
                                                             session)
types = cdr.getLinkTypes(session)
if type(types) == type(""): cdrcgi.bail(types)

for t in types:
    form += "<LI><A HREF='%s/EditLinkType.py?name=%s&linkact=modlink&%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, t, cdrcgi.SESSION, session, t)

form += """\
<LI><A HREF="%s/EditLinkType.py?linkact=addlink&%s=%s">%s</LI>
<LI><A HREF="%s/ShowAllLinkTypes.py?%s=%s">%s</LI>
<LI><A HREF="%s/Logout.py?%s=%s">%s</LI>
</OL>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session, "Add New Link Type",
       cdrcgi.BASE, cdrcgi.SESSION, session, "Show All Link Types",
       cdrcgi.BASE, cdrcgi.SESSION, session, "Log Out")
cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")
