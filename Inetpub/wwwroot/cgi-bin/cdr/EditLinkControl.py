#----------------------------------------------------------------------
# Interface for editing CDR linking tables.
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
