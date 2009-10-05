#----------------------------------------------------------------------
#
# $Id: ProtocolReports.py,v 1.39 2009-09-16 16:34:19 venglisc Exp $
#
# Submenu for protocol reports.
#
# $Log: not supported by cvs2svn $
# Revision 1.38  2008/09/02 20:09:10  bkline
# Added Protocols Linked to Terms report (#4263).
#
# Revision 1.37  2008/08/13 19:52:59  bkline
# Fixed typo (leftover from cut/paste of oncore report); added report
# of Protocols with Regulatory Info Block.
#
# Revision 1.36  2008/07/21 20:20:40  bkline
# Added new Oncore reports at Kim's request (#4141).
#
# Revision 1.35  2008/07/21 17:26:18  bkline
# Added CTEP reports.
#
# Revision 1.34  2008/04/17 18:43:25  bkline
# Added Non-Drug/Agent Protocol Interventions report.
#
# Revision 1.33  2007/10/22 15:58:10  bkline
# Restructuring for Sheri (request 3700).
#
# Revision 1.32  2007/07/31 12:12:52  bkline
# Added NCIC import report.
#
# Revision 1.31  2007/06/12 16:53:10  kidderc
# 3306. Create a Warehouse Box Number Report.
#
# Revision 1.29  2006/11/29 16:04:36  bkline
# Plugged in two new reports (for requests #2443 and #2513).
#
# Revision 1.28  2006/08/31 14:39:39  venglisc
# Replaced report 'Active Lead Orgs without Active Sites' with the new report
# 'Active Status without Sites'. (Bug 2379)
#
# Revision 1.27  2006/07/11 13:41:50  bkline
# Added flavor showing title.
#
# Revision 1.26  2006/05/10 16:36:32  venglisc
# I can't spell MS-Excel.  That's fixed now.
#
# Revision 1.25  2006/05/10 16:35:06  venglisc
# Added menu item for Protocols with FDA IND information report. (Bug 2028)
#
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
form = ["""\
    <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
<!--
    <H3>QC Reports</H3>
    <OL>
""" % (cdrcgi.SESSION, session)]
reports = (('ProtSearch.py?', 
            'Protocol QC Reports'),
           ('QcReport.py?DocType=InScopeProtocol&ReportType=pp&',   
            'Publish Preview - InScopeProtocol'),
           ('QcReport.py?DocType=CTGovProtocol&ReportType=pp&',   
            'Publish Preview - CTGovProtocol'))
for r in reports:
    form.append("<LI><A HREF='%s/%s%s=%s'>%s</LI></A>\n" %
                (cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1]))

form.append("""\
    </OL>
-->
    <H3>Management Reports</H3>
    <OL>
""")
for r in (('ApprovedNotYetActive.py',
           'Approved Not Yet Active Report', ''),
          ('Request1687.py',
           'CTEP Orgs Without Phones', ''),
          ('CTGovEntryDate.py',
           'CTGovProtocols vs. Early EntryDate', ''),
          ('Request2113.py', 
           'NCI Cancer Centers', ''),
          ('LiaisonReport.py', 
           'NCI Liaison Office/Brussels Protocol Report', ''),
          ('Request2862.py', 
           'NCI Liaison Office Trial Contacts for Abstract Review', ''),
          ('Request3935.py',
           "Non-Drug/Agent Protocol Interventions", ''),
          ('PreferredProtOrgs.py', 
           'Preferred Protocol Organizations', ''),
          ('NciClinicalTrialsStats.py', 
           'Profile of NCI Sponsored Clinical Trials', ''),
          ('TrialsCitationStats.py',
           'Protocol Citation Statistics', ''),
          ('Request1855.py',
           'Protocol Interventions', '&cols=2'),
          ('Request1855.py',
           'Protocol Interventions by Protocol Title', ''),
          ('ProtSitesWithoutPhone.py',
           'Protocol Sites Without Phone Numbers', ''),
          ('ProtOwnershipTransfer.py',
           'Protocol Transfer of Ownership Responses', ''),
          ('ProtocolsLinkedToTerms.py',
           'Protocols Linked to Terms', ''),
          ('ProtocolActiveNoSites.py',
           'Protocols with Active Status But No Active Sites', ''),
          ('ProtocolINDReport.py',
           'Protocols with FDA IND Information (Excel)', ''),
          ('Request4176.py',
           'Protocols with Regulatory Info Block', ''),
          ('OutcomeMeasuresCodingReport.py',
           'Protocols without Outcomes', '&onlyMissing=Y')):
    form.append("<LI><A HREF='%s/%s?%s=%s%s'>%s</A></LI>\n" %
                (cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[2], r[1]))
form.append("""\
    </OL>
    <H3>Processing/Publishing Reports</H3>
    <OL>
""")
filename = time.strftime('InterimUpdateReport-%Y%m%d%H%M%S.xls')
for r in (('NewlyPublishableTrials.py', 
           'Newly Publishable Trials', ''),
          ('NewlyPublishedTrials2.py', 
           'Newly Published Trials', ''),
          ('HotfixReport.py',
           'Protocol Interim Update Report',
           '&filename=%s' % filename),
          ('ProtocolStatusChange.py',
           'Protocol Status Change Report', ''),
          ('ProtProcReport.py',
           'Protocol Processing Status Report', ''),
          ('ProtProcReport.py',
           'Protocol Processing Status Report with Protocol Title',
           '&include-title=true'),
          ('Request3654.py', 'Scientific Protocol Tracking Report', '')):
    form.append("<LI><A HREF='%s/%s?%s=%s%s'>%s</A></LI>\n" %
                (cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[2], r[1]))

form.append("""\
    </OL>
    <H3>Data Import Reports</H3>
    <OL>
""")
for r in (('RssImportReport.py', 'COG Import/Update Statistics Report',
           '&source=COG'),
          ('Request4064.py',
           'CTEP Institutions with Address Information (XML)',
           '&output=xml'),
          ('Request4064.py',
           'CTEP Institutions with Address Information (Excel)',
           '&output=xls'),
          ('RssImportReport.py', 'NCIC Import/Update Statistics Report',
           '&source=NCIC')):
    form.append("<LI><A HREF='%s/%s?%s=%s%s'>%s</A></LI>\n" %
                (cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[2], r[1]))
form.append("""\
    <li><a href='%s/oncore-id-mappings'
        >Oncore ID Mappings</a></li>
    <li><a href='%s/RssImportReport.py?%s=%s&source=Oncore'
        >Oncore Import/Update Statistics Report</a></li>
    <li><a href='%s/OncoreTrialsWithoutNctIds.py?all=true'
        >Oncore Submissions With No NCT ID - Full List</a></li>
    <li><a href='%s/OncoreTrialsWithoutNctIds.py'
        >Oncore Submissions With No NCT ID - Disposition Needed</a></li>
    <li><a href='%s/Request3472.py?%s=%s'
        >PDQ Submission Portal Statistics Summary Report</a></li>
""" % (cdr.emailerCgi(), cdrcgi.BASE, cdrcgi.SESSION, session,
       cdr.emailerCgi(), cdr.emailerCgi(),
       cdrcgi.BASE, cdrcgi.SESSION, session))
title = "PDQ Submission Portal Submission Details Report"
host  = cdr.emailerHost()
form.append("<LI><A HREF='http://%s/u/showcts.py'>%s</A></LI>\n" %
            (host, title))
for r in (('RssImportReport.py', 'RSS Import/Update Statistics Report', ''),
          ('RssDocsNoSites.py', 'RSS Imports With No External Sites', '')):
    form.append("<LI><A HREF='%s/%s?%s=%s%s'>%s</A></LI>\n" %
                (cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[2], r[1]))
form.append("""\
    </OL>
    <H3>Other Reports</H3>
    <OL>
""")

for r in (('WarehouseBoxNumberReport.py', 'Warehouse Box Number Report', ''),
          ('OSPReport.py', 'Report for Office of Science Policy', '')):
    form.append("<LI><A HREF='%s/%s?%s=%s%s'>%s</A></LI>\n" %
                (cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[2], r[1]))

cdrcgi.sendPage(header + ''.join(form) + "</OL></FORM></BODY></HTML>")
