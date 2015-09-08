#----------------------------------------------------------------------
#
# $Id$
#
# Submenu for protocol reports.
#
# BZIssue::5239 (JIRA::OCECDR-3543) - menu cleanup
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
for r in (('CTGovEntryDate.py',
           'CTGovProtocols vs. Early EntryDate', ''),
          ('Request3935.py',
           "Non-Drug/Agent Protocol Interventions", ''),
          ('PreferredProtOrgs.py', 
           'Preferred Protocol Organizations', ''),
          ('ProtocolsLinkedToTerms.py',
           'Protocols Linked to Terms', ''),
          ):
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
           'Newly Published Trials', '')):
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
