#----------------------------------------------------------------------
# Submenu for protocol reports.
# BZIssue::5239 (JIRA::OCECDR-3543) - menu cleanup
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
title   = "CDR Administration"
section = "Protocol Reports"
SUBMENU = "Reports Menu"
buttons = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header  = cdrcgi.header(title, title, section, "Reports.py", buttons)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if action == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Display available report choices.
#----------------------------------------------------------------------
form = ["""\
    <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
    <H3>Other Reports</H3>
    <OL>
""" % (cdrcgi.SESSION, session)]
for r in [
    ('WarehouseBoxNumberReport.py', 'Warehouse Box Number Report', '')
]:
    form.append("<LI><A HREF='%s/%s?%s=%s%s'>%s</A></LI>\n" %
                (cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[2], r[1]))

cdrcgi.sendPage(header + ''.join(form) + "</OL></FORM></BODY></HTML>")
