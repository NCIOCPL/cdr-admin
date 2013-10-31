#----------------------------------------------------------------------
#
# $Id$
#
# Submenu for summary and miscellanous document reports.
#
# BZIssue::545      - menu reorganization
# BZIssue::1059     - plugged in additions requested by Margaret
# BZIssue::1231     - added SummariesTocReport; fixed CSS list & header rules
# BZIssue::1329     - match entries between CIAT and CIPS summary menus
# BZIssue::1531     - added Publish Preview menu option
# BZIssue::1537     - replaced the Stub.py to run the BoardRoster report
# BZIssue::3666     - added Summaries with Non-Journal Article Citations report
# JIRA::OCECDR-3650 - added Summary Internal Links report
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
section = "Summary and Miscellaneous Document Reports"
SUBMENU = "Reports Menu"
buttons = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header  = cdrcgi.header(title, title, section, "SummaryAndMiscReports.py", 
                        buttons, stylesheet = """\
  <style type='text/css'>   
   H2 { font-family: Arial; font-size: 14pt; font-weight: bold }
   LI { font-family: Arial; font-size: 12pt; font-weight: bold }
  </style>
""")

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
form = """\
    <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
    <H3>QC Reports</H3>
    <H2>Summary QC Reports</H2>
    <OL>
""" % (cdrcgi.SESSION, session)
reports = [
           # ('Stub.py?', 'Changes to Summaries')
           ('QcReport.py?DocType=Summary&ReportType=bu&', 
            'Bold/Underline (HP/Old Patient)'),
           ('QcReport.py?DocType=Summary&ReportType=rs&', 
            'Redline/Strikeout (HP/Old Patient)'),
           ('QcReport.py?DocType=Summary&ReportType=pat&', 
            'New Patient'),
           ('QcReport.py?DocType=Summary&ReportType=pp&', 
            'Publish Preview')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s%s=%s'>%s</A></LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """\
    </OL>
    <H2>Management QC Reports</H2>
    <OL>
"""
reports = [
           ('ChangesToSummaries.py?',      'Changes to Summaries'),
           ('SummaryChanges.py?',          'History of Changes to Summary'),
           ('PdqBoards.py?',               'PDQ Board Listings'),
           ('SummaryCitations.py?',        'Summaries Citations'),
           ('SummaryDateLastModified.py?', 'Summaries Date Last Modified'),
           ('SummariesLists.py?',          'Summaries Lists'),
           ('SummaryMetaData.py?',         'Summaries Metadata'),
           ('SummariesTocReport.py?',      'Summaries TOC Lists'),
           ('SummariesWithProtocolLinks.py?',      'Summaries with Protocols Links/Refs Report'),
           ('SummariesWithNonJournalArticleCitations.py?',      'Summaries with Non-Journal Article Citations Report'),
           ('ocecdr-3650.py?',             'Summary Internal Links'),
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s%s=%s'>%s</A></LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])


form += """\
   </OL>
   <H2>Board Member Information Reports</H2>
   <OL>
"""

for choice in (
    ('QcReport.py',         'Board Member Information QC Report' ),
    ('BoardRoster.py',      'Board Roster Reports'               )
    ):
    form += """\
    <LI><A href='%s/%s?DocType=PDQBoardMemberInfo&Session=%s'>%s</A></LI>
""" % (cdrcgi.BASE, choice[0], session, choice[1])
session = "%s=%s" % (cdrcgi.SESSION, session)
form += """\
   </OL>
   <H2>Miscellaneous Document QC Report</H2>
   <OL>
    <LI><A HREF='%s/MiscSearch.py?%s'>Miscellaneous Documents</A></LI>
    <LI><A HREF='%s/SummaryMailerReport.py?flavor=4259&%s'
        >Summary Mailer History Report</A></LI>
    <LI><A HREF='%s/SummaryMailerReport.py?flavor=4258&%s'
        >Summary Mailer Report</A></LI>
""" % (cdrcgi.BASE, session, cdrcgi.BASE, session, cdrcgi.BASE, session)

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
