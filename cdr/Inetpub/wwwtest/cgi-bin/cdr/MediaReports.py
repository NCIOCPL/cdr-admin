#----------------------------------------------------------------------
#
# $Id: MediaReports.py,v 1.3 2006-05-08 18:18:40 bkline Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2006/05/04 14:04:56  bkline
# Added MediaSearcy.py.
#
# Revision 1.1  2005/05/04 18:14:01  venglisc
# Inintial version of Media Reports Menu page of the Admin interface.
# (Bug 1653)
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
section = "Media Reports"
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
# Display available menu choices.
#----------------------------------------------------------------------
session = "%s=%s" % (cdrcgi.SESSION, session)
#    <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
form = """\
    <H3>QC Reports</H3>
    <OL>
    <LI><a href='MediaSearch.py?%s'>Advanced Search</a></LI>
""" % session
for choice in (
    ('img',  'Media Doc QC Report'   ),
    ):
    form += """\
    <LI><a href='%s/QcReport.py?DocType=Media&ReportType=%s&%s'>%s</a></LI>
""" % (cdrcgi.BASE, choice[0], session, choice[1])
form += "</OL>\n<H3>Management Reports</H3><OL>\n"
for choice in(
    ('MediaTrackingReport.py', 'Media Tracking Report'),
    ):
    form += "<LI><a href='%s/%s?%s'>%s</a></LI>\n" % (cdrcgi.BASE, choice[0],
                                                      session, choice[1])
cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
