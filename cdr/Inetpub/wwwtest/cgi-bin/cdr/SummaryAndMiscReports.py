#----------------------------------------------------------------------
#
# $Id: SummaryAndMiscReports.py,v 1.17 2005-03-24 21:12:36 bkline Exp $
#
# Submenu for summary and miscellanous document reports.
#
# $Log: not supported by cvs2svn $
# Revision 1.16  2005/02/16 19:12:35  venglisc
# Replaced the Stub.py to run the BoardRoster report. (Bug 1537)
#
# Revision 1.15  2004/09/09 19:19:44  venglisc
# Minor changes to menu entries to have menu items match between the
# CIAT and CIPS summary menu. (Bug 1329).
#
# Revision 1.14  2004/07/13 20:46:33  venglisc
# Added new menu item for SummariesTocReport. (Bug 1231)
# Added CSS code to display headers and list items properly.
#
# Revision 1.13  2004/04/16 21:50:48  venglisc
# Removed stub to link to proper page for Board Member QC report.
#
# Revision 1.12  2004/04/08 20:31:10  bkline
# Plugged in additions requested by Margaret (request #1059).
#
# Revision 1.11  2004/03/11 20:53:28  venglisc
# Minor change to one menu entry.
#
# Revision 1.10  2004/03/05 21:47:44  venglisc
# Modified the menu selection and added new SummariesLists menu item.
#
# Revision 1.9  2003/08/01 21:02:49  bkline
# Plugged in Summary Metadata report.
#
# Revision 1.8  2003/06/13 20:31:17  bkline
# Suppressed menu item for "Changes to Summaries" report at Margaret's
# request.
#
# Revision 1.7  2003/06/02 14:24:45  bkline
# Plugged in two new summary reports.
#
# Revision 1.6  2003/05/08 20:26:42  bkline
# New summary reports.
#
# Revision 1.5  2002/12/30 15:15:47  bkline
# Fixed a typo.
#
# Revision 1.4  2002/12/26 19:40:41  bkline
# Rearranged for issue #545.
#
# Revision 1.3  2002/06/06 12:01:09  bkline
# Custom handling for Person and Summary QC reports.
#
# Revision 1.2  2002/05/25 02:39:13  bkline
# Removed extra blank lines from HTML output.
#
# Revision 1.1  2002/05/24 20:37:32  bkline
# New Report Menu structure implemented.
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
            'New Patient')
           # ('QcReport.py?DocType=Summary&ReportType=nm&', 
           #  'No Markup QC Report')
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
    
form += """\
   </OL>
   <H2>Miscellaneous Document QC Report</H2>
   <OL>
    <LI><A HREF='%s/MiscSearch.py?%s'>Miscellaneous Documents</A></LI>
""" % (cdrcgi.BASE, session)

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
