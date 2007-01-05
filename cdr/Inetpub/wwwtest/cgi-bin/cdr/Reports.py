#----------------------------------------------------------------------
#
# $Id: Reports.py,v 1.24 2007-01-05 23:23:11 venglisc Exp $
#
# Prototype for editing CDR linking tables.
#
# $Log: not supported by cvs2svn $
# Revision 1.23  2006/09/28 23:08:52  ameyer
# Changed date and message for Documentation link.
#
# Revision 1.22  2006/05/04 14:34:13  bkline
# Added Drug information reports.
#
# Revision 1.21  2005/05/04 18:11:33  venglisc
# Added menu option for Media QC Reports. (Bug 1653)
#
# Revision 1.20  2004/09/20 20:31:11  venglisc
# Added CdrDocumentation.py menu item for PDF formatted CDR documentation.
# (Bug 1338).
#
# Revision 1.19  2003/02/13 23:03:01  pzhang
# Added Publishling item.
#
# Revision 1.18  2002/05/24 20:40:38  bkline
# Fixed misnamed variable (request changed to action).
#
# Revision 1.17  2002/05/24 20:37:31  bkline
# New Report Menu structure implemented.
#
# Revision 1.16  2002/05/24 18:02:38  bkline
# Added Person Protocol Review report.
#
# Revision 1.15  2002/05/16 14:34:42  bkline
# Added future entry for newly published trials.
#
# Revision 1.14  2002/05/03 20:28:54  bkline
# New Mailer reports.
#
# Revision 1.13  2002/04/25 02:58:53  bkline
# New report for mailer checkin.
#
# Revision 1.12  2002/04/22 22:15:45  bkline
# New report (Generic Date Last Modified).
#
# Revision 1.11  2002/04/10 20:07:55  bkline
# Added Publishing Job Queue report.
#
# Revision 1.10  2002/03/21 20:01:15  bkline
# Added Glossary Term Links report and Persons at Org report.
#
# Revision 1.9  2002/03/14 04:01:10  bkline
# Added New Doc Report.
#
# Revision 1.8  2002/03/13 16:58:25  bkline
# Added dated actions report.
#
# Revision 1.7  2002/03/09 03:27:40  bkline
# Added report for unverified citations.
#
# Revision 1.6  2002/03/02 13:50:31  bkline
# Added report for checked-out documents.
#
# Revision 1.5  2002/02/26 18:55:29  bkline
# Sorted report menu alphabetically.
#
# Revision 1.4  2002/02/21 15:22:03  bkline
# Added navigation buttons.
#
# Revision 1.3  2002/01/22 21:32:01  bkline
# Added three new reports.
#
# Revision 1.2  2001/12/01 18:07:34  bkline
# Added some new reports.
#
# Revision 1.1  2001/06/13 22:16:32  bkline
# Initial revision
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
section = "Reports"
buttons = [cdrcgi.MAINMENU, "Log Out"]
header  = cdrcgi.header(title, title, section, "Reports.py", buttons)

#----------------------------------------------------------------------
# Return to the main menu if requested.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if action == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Display available report choices.
#----------------------------------------------------------------------
form = "<INPUT TYPE='hidden' NAME='%s' VALUE='%s'><OL>\n" % (cdrcgi.SESSION,
                                                             session)
reports = [
           ('GeneralReports.py',      'General Reports'),
           ('CitationReports.py',     'Citations'),
           ('CdrDocumentation.py',    'Documentation (as of 2004-09-08)'),
           ('DrugInfoReports.py',     'Drug Information'),
           ('GeographicReports.py',   'Geographic'),
           ('GlossaryTermReports.py', 'Glossary Terms'),
           ('MailerReports.py',       'Mailers'),
           ('MediaReports.py',        'Media'),
           ('PublishReports.py',      'Publishing'),
           ('PersonAndOrgReports.py', 'Persons and Organizations'),
           ('ProtocolReports.py',     'Protocols'),
           ('SummaryAndMiscReports.py', 
                                      'Summaries and Miscellaneous Documents'),
           ('TerminologyReports.py',  'Terminology')
          ]

for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
