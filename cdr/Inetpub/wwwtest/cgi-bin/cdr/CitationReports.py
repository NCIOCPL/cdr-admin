#----------------------------------------------------------------------
#
# $Id: CitationReports.py,v 1.4 2004-03-30 20:28:05 bkline Exp $
#
# Submenu for citation reports.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2004/02/17 19:37:52  venglisc
# Removed unused menu items
#
# Revision 1.2  2002/05/25 02:39:12  bkline
# Removed extra blank lines from HTML output.
#
# Revision 1.1  2002/05/24 20:37:29  bkline
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
section = "Citation Reports"
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
           ('CiteSearch.py', 'Citation QC Report')
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
           ('UnverifiedCitations.py', 'Unverified Citations')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])
    
form += """\
    </OL>
    <H3>Management Reports</H3>
    <OL>
"""
reports = [
           ('ModifiedPubMedDocs.py', 'Modified PubMed Documents'),
           ('NewCitations.py', 'New Citations Report')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
