#----------------------------------------------------------------------
#
# $Id: TerminologyReports.py,v 1.8 2004-09-17 14:06:50 venglisc Exp $
#
# Submenu for terminology reports.
#
# $Log: not supported by cvs2svn $
# Revision 1.7  2004/05/11 17:40:11  bkline
# Plugged in Drug/Agent report.
#
# Revision 1.6  2003/06/13 20:32:43  bkline
# Plugged in a couple of new reports for Cancer diagnosis hierarchy.
#
# Revision 1.5  2003/05/08 20:27:27  bkline
# New terminology report for menu information.
#
# Revision 1.4  2002/12/11 17:27:54  bkline
# Plugged in the new Intervention/Procedure terminology report.
#
# Revision 1.3  2002/07/01 14:00:56  bkline
# Plugged in stub for Term by Type report.
#
# Revision 1.2  2002/05/25 02:39:14  bkline
# Removed extra blank lines from HTML output.
#
# Revision 1.1  2002/05/24 20:37:32  bkline
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
section = "Terminology Reports"
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
           ('TermUsage.py', 'Term Usage'),
           ('TermSearch.py', 'Terminology QC Report')
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
           ('MenuHierarchy.py', 'Menu Hierarchy Report', ''),
           ('Stub.py', 'Term By Type', ''),
           ('DiseaseDiagnosisTerms.py',
            'Cancer Diagnosis Hierarchy', ''),
           ('DiseaseDiagnosisTerms.py',
            'Cancer Diagnosis Hierarchy (Without Alternate Names)',
            '&flavor=short'),
           ('InterventionAndProcedureTerms.py',
            'Intervention/Procedure Terms', ''),
           ('DrugAgentReport.py', 'Drug/Agent Report', '')
            
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s%s'>%s</LI></A>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[2], r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
