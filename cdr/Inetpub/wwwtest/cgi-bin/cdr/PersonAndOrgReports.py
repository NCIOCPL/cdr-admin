#----------------------------------------------------------------------
#
# $Id: PersonAndOrgReports.py,v 1.7 2004-03-08 17:47:06 venglisc Exp $
#
# Submenu for person and organization reports.
#
# $Log: not supported by cvs2svn $
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
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
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
           ('OrgProtocolReview.py', 
            'Organization Protocol Review'),
           ('PersonProtocolReview.py', 
            'Person Protocol Review'),
           ('PersonsAtOrg.py', 
            'Persons Practicing at Organizations'),
           ('PreferredProtOrgs.py', 
            'Preferred Protocol Organizations')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
