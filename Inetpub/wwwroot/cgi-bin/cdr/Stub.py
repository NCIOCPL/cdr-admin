#----------------------------------------------------------------------
# Stub for report which hasn't been implemented yet.
# JIRA::OCECDR-3800 - Address security vulnerabilities
#----------------------------------------------------------------------
import cgi
import cdrcgi

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
title   = "CDR Administration"
section = "Reports"
SUBMENU = "Reports Menu"
buttons = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)
if action == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Display available report choices.
#----------------------------------------------------------------------
page = cdrcgi.Page(title, subtitle=section, action="Reports.py",
                   buttons=buttons, session=session)
instructions = u"""\
This report has not yet been implemented, either because
we don't yet have the specs, or because it's behind higher-priority
tasks in the development task queue."""
page.add(page.B.FIELDSET(page.B.P(instructions)))
page.send()
