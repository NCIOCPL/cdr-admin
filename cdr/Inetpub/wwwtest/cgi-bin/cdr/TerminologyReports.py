#----------------------------------------------------------------------
#
# $Id: TerminologyReports.py,v 1.14 2008-01-25 17:49:44 kidderc Exp $
#
# Submenu for terminology reports.
#
# $Log: not supported by cvs2svn $
# Revision 1.12  2007/06/15 17:55:07  kidderc
# 3316 added Term Hierarchy Report.
#
# Revision 1.11  2007/06/15 04:03:21  ameyer
# Added menu item for Drug Review Report.
#
# Revision 1.10  2007/06/13 11:26:49  kidderc
# 3309. Add a Semantic Type Report.
#
# Revision 1.9  2005/03/24 21:19:58  bkline
# Plugged in Drug/Agent Other Names Report.
#
# Revision 1.8  2004/09/17 14:06:50  venglisc
# Fixed list items to properly teminate the anker link.
#
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
           ('TermSearch.py', 'Terminology QC Report'),
           ('TermNCITDrugUpdateAll.py', 'Update all Drug/Agent Terms from NCI Thesaurus'),
           ('TermNCITDiseaseUpdateAll.py', 'Update all Disease Terms from NCI Thesaurus')
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
            'Intervention or Procedure Terms', '&IncludeAlternateNames=True'),
           ('InterventionAndProcedureTerms.py',
            'Intervention or Procedure Terms (without Alternate Names)', '&IncludeAlternateNames=False'),
           ('DrugAgentReport.py', 'Drug/Agent Report', ''),
           ('DrugAgentReport2.py', 'Drug/Agent Other Names Report', ''),
           ('DrugReviewReport.py', 'Drug Review Report', ''),
           ('SemanticTypeReport.py', 'Semantic Type Report', ''),
           ('TermHierarchyTree.py', 'Term Hierarchy Tree', ''),
           ('TermHierarchyTree.py', 'Terms with No Parent Term and Not a Semantic Type', '&SemanticTerms=False')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s%s'>%s</LI></A>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[2], r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
