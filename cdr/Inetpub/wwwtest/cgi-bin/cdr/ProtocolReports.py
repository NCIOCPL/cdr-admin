#----------------------------------------------------------------------
#
# $Id: ProtocolReports.py,v 1.9 2003-05-08 20:24:01 bkline Exp $
#
# Submenu for protocol reports.
#
# $Log: not supported by cvs2svn $
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
import cgi, cdr, cdrcgi, re, string

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
reports = [('ProtSearch.py', 'Protocol QC Reports')]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """\
    </OL>
    <H3>Management Reports</H3>
    <OL>
"""
reports = [
           ('Stub.py', 'Approved Protocols'),
           ('NewlyPublishedTrials.py', 'Newly Published Protocols'),
           ('Stub.py', 'Published Protocol Count'),
           ('LiaisonReport.py', 'NCI Liaison Office/Brussels Protocol Report'),
           ('PreMailerProtReport.py',
            'Pre-Mailer Protocol Check'),
           ('ApprovedNotYetActive.py',
            'Approved Not Yet Active Report'),
           ('ProtocolStatusChange.py',
            'Protocol Status Change Report'),
           ('BogusActiveLeadOrgs.py',
            'Protocols with Active Lead Orgs But No Active Sites'),
           ('ProtSitesWithoutPhone.py',
            'Protocol Sites Without Phone Numbers'),
           ('OSPReport.py',
            'Report for Office of Science Policy')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
