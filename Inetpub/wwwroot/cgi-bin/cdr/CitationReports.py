#----------------------------------------------------------------------
#
# $Id$
#
# Submenu for citation reports.
#
# JIRA::OCECDR-3800
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
section = "Citation Reports"
SUBMENU = "Reports Menu"
buttons = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]

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
page = cdrcgi.Page(title, subtitle=section, action="Reports.py",
                   buttons=buttons, session=session, body_classes="admin-menu")
page.add(page.B.H3("QC Reports"))
page.add("<ol>")
page.add_menu_link("CiteSearch.py", "Citation QC Report", session)
page.add("</ol>")
page.add(page.B.H3("Other Reports"))
page.add("<ol>")
page.add_menu_link("UnverifiedCitations.py", "Unverified Citations", session)
page.add("</ol>")
page.add(page.B.H3("Management Reports"))
page.add("<ol>")
for script, display in (
    ('CitationsAddedToProtocols.py', 'Citations Added to Protocols'),
    ('CitationsInSummaries.py',      'Citations Linked to Summaries'),
    ('ModifiedPubMedDocs.py',        'Modified PubMed Documents'),
    ('NewCitations.py',              'New Citations Report'),
):
    page.add_menu_link(script, display, session)
page.add("</ol>")
page.send()
