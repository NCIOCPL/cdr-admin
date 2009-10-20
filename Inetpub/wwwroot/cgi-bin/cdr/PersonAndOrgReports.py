#----------------------------------------------------------------------
#
# $Id$
#
# Submenu for person and organization reports.
#
# $Log: not supported by cvs2svn $
# Revision 1.13  2007/04/23 12:36:21  bkline
# Plugged in new Organization Protocols Spreadsheet report.
#
# Revision 1.12  2005/04/13 20:13:25  venglisc
# Added menu option for Member of AdHoc Group report.  (Bug 1630)
#
# Revision 1.11  2004/11/03 20:14:37  venglisc
# Added Organization Affiliations report ad Organization Acronym report as
# new menu items. (Bug 1378, 1380)
#
# Revision 1.10  2004/10/28 18:59:07  venglisc
# Added Organization Protocol Acronym menu option.
#
# Revision 1.9  2004/09/17 14:06:50  venglisc
# Fixed list items to properly teminate the anker link.
#
# Revision 1.8  2004/03/29 21:33:38  bkline
# Added CCOPOrgReport.py.
#
# Revision 1.7  2004/03/08 17:47:06  venglisc
# Modified Menu title and alphabetized entries. (Bug 1094)
#
# Revision 1.6  2003/11/05 14:49:13  bkline
# Added report for Preferred Protocol Organizations.
#
# Revision 1.5  2003/07/29 12:40:13  bkline
# Added Organization Protocol Review report.
#
# Revision 1.4  2002/07/16 15:39:37  bkline
# New report on inactive persons and orgs.
#
# Revision 1.3  2002/06/04 20:16:45  bkline
# New report for member orgs and PIs of cooperative groups.
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
section = "Person and Organization Reports"
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
reports = [
           ('OrgSearch2.py', 'Organization QC Report'),
           ('PersonSearch.py', 'Person QC Report')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI></A>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """\
    </OL>
    <H3>Other Reports</H3>
    <OL>
"""
reports = [
           ('CoopGroupMembers.py', 
            'Cooperative Group Member Orgs and Investigators'),
           ('InactivePersonsOrgs.py', 
            'Inactive Persons/Organizations Linked to Protocols'),
           ('CCOPOrgReport.py',
            'NCI Funded CCOP/MBCCOP Organization Report'),
           ('MemberOfAdhocGroup.py',
            'Member Of Adhoc Group Report'),
	       ('OrgAffiliations.py',
	        'Organization Affiliations Report'),
           ('Request3109.py', 
            'Organization Protocols Spreadsheet'),
           ('OrgProtocolReview.py', 
            'Organization Protocol Review'),
	       ('OrgProtocolAcronym.py',
	        'Organizations Protocol Acronym Report'),
           ('OrgsWithoutCTOs.py', 
            """Organizations (without CTO's) Linked to Protocols"""),
           ('PersonProtocolReview.py', 
            'Person Protocol Review'),
           ('PersonsAtOrg.py', 
            'Persons Practicing at Organizations'),
           ('PreferredProtOrgs.py', 
            'Preferred Protocol Organizations')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI></A>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
