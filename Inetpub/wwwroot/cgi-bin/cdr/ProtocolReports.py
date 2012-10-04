#----------------------------------------------------------------------
#
# $Id$
#
# Submenu for protocol reports.
#
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
           'Protocol Transfer of Ownership Responses (Batch Job)', ''),
          ('ProtOwnershipTransferOrg.py',
           'Protocol Transfer of Ownership Responses by Org/Status', ''),
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
for r in (('NewlyPublishableTrials.py', 
           'Newly Publishable Trials', ''),
          ('NewlyPublishedTrials2.py', 
           'Newly Published Trials', ''),
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
          ('RssImportReport.py', 'RSS Import/Update Statistics Report', ''),
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
