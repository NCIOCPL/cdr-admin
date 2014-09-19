#----------------------------------------------------------------------
#
# $Id$
#
# Submenu for general reports.
#
# BZIssue::255
# BZIssue::1373
# BZIssue::1417
# BZIssue::4126
# JIRA::OCECDR-3800
#
#----------------------------------------------------------------------
import cdrcgi
import cgi

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
title   = "CDR Administration"
section = "General Reports"
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
reports = (
    ("CheckedOutDocs.py", "Checked Out Documents"),
    ("CdrReport.py", "Checked Out Documents With No Activity"),
    ("ContentInventory.py", "Content Inventory Report"),
    ("ActiveLogins.py", "Current Sessions"),
    ("db-tables.py", "Database Tables/Columns"),
    ("DateLastModified.py", "Date Last Modified"),
    ("DatedActions.py", "Dated Actions"),
    ("ActivityReport.py", "Document Activity Report"),
    ("DocVersionHistory.py", "Document Version History"),
    ("DocumentsModified.py", "Documents Modified"),
    ("ExternMapFailures.py", "External Map Failures Report"),
    ("/CdrFilter.html", "Filter Document"),
    ("ShowGlobalChangeTestResults.py", "Global Change Test Results"),
    ("InvalidDocs.py", "Invalid Documents"),
    ("LinkedDocs.py", "Linked Documents"),
    ("MediaLinks.py", "Linked Media Documents"),
    ("NewDocsWithPubStatus.py",
                        "List of New Documents with Publication Status"),
    ("NewDocReport.py", "New Document Count"),
    ("ModWithoutPubVersion.py",
                         "Records Modified Since Last Publishable Version"),
    ("UnchangedDocs.py", "Unchanged Documents"),
    ("CheckUrls.py", "URL Check (Batch job - runs ~15 min)"),
    ("ReplaceCWDReport.py", "Versions that Replaced CWDs"),
)
page = cdrcgi.Page(title, subtitle=section, action="GeneralReports.py",
                   buttons=buttons, session=session, body_classes="admin-menu")
page.add("<ol>")
for url, label in reports:
    page.add_menu_link(url, label, session)
page.add("</ol>")
page.send()
