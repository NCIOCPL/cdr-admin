#----------------------------------------------------------------------
#
# $Id: ProtocolReports.py,v 1.25 2006-05-10 16:35:06 venglisc Exp $
#
# Submenu for protocol reports.
#
# $Log: not supported by cvs2svn $
# Revision 1.24  2006/05/04 14:26:33  bkline
# Three new reports added.
#
# Revision 1.22  2005/11/18 03:48:54  bkline
# Plugged in Alan's new CTGov protocols.
#
# Revision 1.21  2005/11/18 03:46:07  bkline
# Plugged in COG import report and two new OSP reports.
#
# Revision 1.20  2005/07/07 15:42:32  venglisc
# Added menu item for protocols with published results report. (Bug 1735)
#
# Revision 1.19  2005/06/30 21:55:39  bkline
# Changed string for NCI Clinical Trials Statistics report.
#
# Revision 1.18  2005/06/07 15:49:54  bkline
# Two new reports plugged in: CTEP orgs without phones and NCI trials.
#
# Revision 1.17  2005/05/12 14:49:38  bkline
# New report for Sheri (request #1684).
#
# Revision 1.16  2005/05/11 20:57:24  bkline
# Report created for Sheri (request #1669).
#
# Revision 1.15  2005/04/21 21:27:25  venglisc
# Added menu option to allow Publish Preview QC report. (Bug 1531)
#
# Revision 1.14  2005/03/16 17:20:11  venglisc
# Corrected some problems in the queries to eliminate incorrect hits.
# Added another worksheet to include new CTGovProtocols.
# Modified the output file from HotFixReport to InterimUpdateReport.
# Added the prtocol type to the list of removed protocols. (Bugs 1396, 1538)
#
# Revision 1.13  2004/09/17 14:06:50  venglisc
# Fixed list items to properly teminate the anker link.
#
# Revision 1.12  2004/07/13 17:59:21  bkline
# Replaced Newly Published Trials with Newly Publishable Trials.
#
# Revision 1.11  2004/05/11 17:38:36  bkline
# Plugged in protocol hotfix report.
#
# Revision 1.10  2004/02/17 19:13:33  venglisc
# Removed unused Menu entries and alphabetized remaining entries.
#
# Revision 1.9  2003/05/08 20:24:01  bkline
# New report for Office of Science Policy.
#
# Revision 1.8  2003/03/06 20:55:04  bkline
# Fixed typo (Orrice -> Office).
#
# Revision 1.7  2003/03/06 20:54:03  bkline
# Added back in two menu items which had disappeared.
#
# Revision 1.6  2003/03/04 22:46:58  bkline
# Modifications for CDR enhancement request #301.
#
# Revision 1.5  2003/01/29 18:46:25  bkline
# New report on protocols with status change entered in a given date range.
#
# Revision 1.4  2003/01/22 23:28:30  bkline
# New report for issue #560.
#
# Revision 1.3  2002/09/23 17:36:40  bkline
# New report for European protocols.
#
# Revision 1.2  2002/05/25 02:39:13  bkline
# Removed extra blank lines from HTML output.
#
# Revision 1.1  2002/05/24 20:37:31  bkline
# New Report Menu structure implemented.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, time

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
form = """\
    <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
    <H3>QC Reports</H3>
    <OL>
""" % (cdrcgi.SESSION, session)
reports = [('ProtSearch.py?', 
            'Protocol QC Reports'),
           ('QcReport.py?DocType=InScopeProtocol&ReportType=pp&',   
            'Publish Preview - InScopeProtocol'),
           ('QcReport.py?DocType=CTGovProtocol&ReportType=pp&',   
            'Publish Preview - CTGovProtocol')]
for r in reports:
    form += "<LI><A HREF='%s/%s%s=%s'>%s</LI></A>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """\
    </OL>
    <H3>Management Reports</H3>
    <OL>
"""
filename = time.strftime('InterimUpdateReport-%Y%m%d%H%M%S.xls')
reports = [
           ('ApprovedNotYetActive.py',
            'Approved Not Yet Active Report', ''),
           ('RssImportReport.py', 'COG Import/Update Statistics Report',
            '&source=COG'),
           ('Request1687.py',
            'CTEP Orgs Without Phones', ''),
           ('CTGovEntryDate.py',
            'CTGovProtocols vs. Early EntryDate', ''),
           ('Request2113.py', 
            'NCI Cancer Centers', ''),
           ('LiaisonReport.py', 
            'NCI Liaison Office/Brussels Protocol Report', ''),
           ('NewlyPublishableTrials.py', 
            'Newly Publishable Trials', ''),
           ('PreferredProtOrgs.py', 
            'Preferred Protocol Organizations', ''),
           ('NciClinicalTrialsStats.py', 
            'Profile of NCI Sponsored Clinical Trials', ''),
           ('TrialsCitationStats.py',
            'Protocol Citation Statistics', ''),
           ('HotfixReport.py',
            'Protocol Interim Update Report',
            '&filename=%s' % filename),
           ('Request1855.py',
            'Protocol Interventions', '&cols=2'),
           ('Request1855.py',
            'Protocol Interventions by Protocol Title', ''),
           ('ProtSitesWithoutPhone.py',
            'Protocol Sites Without Phone Numbers', ''),
           ('ProtocolStatusChange.py',
            'Protocol Status Change Report', ''),
           ('BogusActiveLeadOrgs.py',
            'Protocols with Active Lead Orgs But No Active Sites', ''),
           ('ProtocolINDReport.py',
            'Protocols with FDA IND Information (Excell)', ''),
           ('ProtProcReport.py',
            'Protocol Processing Status Report', ''),
           ('OSPReport.py',
            'Report for Office of Science Policy', ''),
           ('RssImportReport.py', 'RSS Import/Update Statistics Report', ''),
           ('RssDocsNoSites.py', 'RSS Imports With No External Sites', '')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s%s'>%s</LI></A>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[2], r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
