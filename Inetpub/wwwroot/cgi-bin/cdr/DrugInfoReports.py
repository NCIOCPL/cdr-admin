#----------------------------------------------------------------------
# Administrative menu for managing CDR DrugInformationSummary documents.
#
# BZIssue::4887 - New Drug Information Summary Report
# BZIssue::4922 - Enhancements to the Summaries with Markup Report
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
title   = "CDR Administration"
section = "Drug Information Reports"
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
# Display available menu choices.
#----------------------------------------------------------------------
form = """
    <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
    <H3>QC Reports</H3>
    <OL>
""" % (cdrcgi.SESSION, session)
QCReports = (('DISSearch.py?type=advanced', 'Advanced Search'),
             ('QcReport.py?DocType=DrugInformationSummary',
              'Drug Information QC Report'),
             ('QcReport.py?DocType=DrugInformationSummary&ReportType=pp&',
              'Publish Preview'))

for r in QCReports:
    form += "<LI><A HREF='%s/%s&%s=%s'>%s</LI></A>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """</OL><H3>Other Reports</H3><OL>"""

OtherReports = [
           ('DrugDescriptionReport.py?', 'Drug Description Report'),
           ('DrugIndicationsReport.py?', 'Drug Indications Report'),
           ('DISLists.py?',              'Drug Information Summaries Lists'),
           ('DISWithMarkup.py?',         'Drug Summaries with Markup Report')]

for r in OtherReports:
    form += "<LI><A HREF='%s/%s&%s=%s'>%s</LI></A>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
