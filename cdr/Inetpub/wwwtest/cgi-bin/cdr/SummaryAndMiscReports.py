#----------------------------------------------------------------------
#
# $Id: SummaryAndMiscReports.py,v 1.9 2003-08-01 21:02:49 bkline Exp $
#
# Submenu for summary and miscellanous document reports.
#
# $Log: not supported by cvs2svn $
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
                        buttons)

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
    <H4>Health Professional/Old Format Patient Summaries</H4>
    <OL>
""" % (cdrcgi.SESSION, session)
reports = [
           ('QcReport.py?DocType=Summary&ReportType=bu&', 
            'Bold/Underline QC Report'),
           ('QcReport.py?DocType=Summary&ReportType=nm&', 
            'No Markup QC Report'),
           ('QcReport.py?DocType=Summary&ReportType=rs&', 
            'Redline/Strikeout QC Report')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """\
    </OL>
    <H4>New Format Patient Summaries</H4>
    <OL>
"""
reports = [
           ('QcReport.py?DocType=Summary&ReportType=rs&', 
            'Redline/Strikeout QC Report'),
           ('QcReport.py?DocType=Summary&ReportType=nm&', 
            'No Markup QC Report')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """\
    </OL>
    <H4>Miscellaneous Documents</H4>
    <OL>
"""
reports = [
           ('MiscSearch.py?', 'Miscellaneous Documents QC Report')
          ]
for r in reports:
    # Careful!  The pattern in the HREF='...' below is intentionally
    # different from the patterns above; there's a '?' included here.
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """\
    </OL>
    <H4>Management Reports</H4>
    <OL>
"""
reports = [
           # ('Stub.py?', 'Changes to Summaries'),
           ('SummaryChanges.py?', 'History of Changes to Summary'),
           ('PdqBoards.py?', 'PDQ Board Listings'),
           ('SummaryCitations.py?', 'Summaries Citation'),
           ('SummaryDateLastModified.py?', 'Summaries Date Last Modified'),
           ('SummaryMetaData.py?', 'Summary Metadata'),
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])


cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
