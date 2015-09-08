#----------------------------------------------------------------------
#
# $Id$
#
# Reports submenu for CDR administrative system.
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
           ('CdrDocumentation.py',    'Documentation'),
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
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</A></LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
