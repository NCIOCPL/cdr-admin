#----------------------------------------------------------------------
#
# $Id: MailerReports.py,v 1.8 2004-09-17 14:06:50 venglisc Exp $
#
# Submenu for mailer reports.
#
# $Log: not supported by cvs2svn $
# Revision 1.7  2004/07/13 17:46:42  bkline
# Added web mailer reports.
#
# Revision 1.6  2004/02/17 19:46:39  venglisc
# Modified menu to remove unused menu items.
#
# Revision 1.5  2003/08/25 20:15:22  bkline
# Plugged in new report for Lead Org S&P Mailer history.
#
# Revision 1.4  2003/05/20 19:28:50  bkline
# Plugged in mailer non-respondents report.
#
# Revision 1.3  2002/05/24 20:37:30  bkline
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
reports = [
           ('LeadOrgStatusAndParticipantMailerHistory.py',
            'Lead Organization Status and Participant Mailer History'),
           ('MailerActivityStatistics.py', 
            'Mailer Activity Counts'),
           ('MailerCheckinReport.py', 
            'Mailer Check-In Count'),
           ('MailerHistory.py', 
            'Mailer History'),
           ('NonRespondents.py', 
            'Non-Respondents'),
           ('PreMailerProtReport.py',
            'Pre-Mailer Protocol Check'),
           ('EmailerReports.py',
            'Web Mailers')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI></A>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
