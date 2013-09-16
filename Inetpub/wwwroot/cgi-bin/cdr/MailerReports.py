#----------------------------------------------------------------------
#
# $Id$
#
# Submenu for mailer reports.
#
# BZIssue::4630
# BZIssue::1572
# BZIssue::5239 (JIRA::OCECDR-3543) - menu cleanup
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
section = "Mailer Reports"
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
    <OL>
""" % (cdrcgi.SESSION, session)
form += "<LI><A HREF='%s/ListGPEmailers'>%s</LI></A>\n" % (
            cdr.emailerCgi(), 'GP Emailers List')
reports = [
           ('MailerActivityStatistics.py', 
            'Mailer Activity Counts'),
           ('MailerCheckinReport.py', 
            'Mailer Check-In Count'),
           ('MailerHistory.py', 
            'Mailer History'),
           ('Request4275.py', 'Mailers Received - Detailed')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI></A>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
