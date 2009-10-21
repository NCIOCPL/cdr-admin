#----------------------------------------------------------------------
#
# $Id: TerminologyReports.py,v 1.15 2008-12-09 13:33:30 bkline Exp $
#
# Submenu for terminology reports.
#
# BZIssue::4653 CTRO Access to CDR Admin Interface
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
userPair = cdr.idSessionUser(session, session)

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
roReports = [
             ('TermUsage.py',                           'Term Usage'),
             ('TermSearch.py',               'Terminology QC Report')
            ]
updates   = [
             ('TermNCITDrugUpdateAll.py',
                    'Update all Drug/Agent Terms from NCI Thesaurus'),
             ('TermNCITDiseaseUpdateAll.py',
                       'Update all Disease Terms from NCI Thesaurus')
            ]

# Determining the menus to adjust for Guest users
# -----------------------------------------------
userInfo = cdr.getUser((userPair[0], userPair[1]), userPair[0])
if 'GUEST' in userInfo.groups and len(userInfo.groups) < 2:
    reports = roReports
else:
    reports = roReports + updates

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
            'Intervention or Procedure Terms (without Alternate Names)',
            '&IncludeAlternateNames=False'),
           ('DrugAgentReport.py', 'Drug/Agent Report', ''),
           ('DrugAgentReport2.py', 'Drug/Agent Report - All', '&alldrugs=true'),
           ('DrugReviewReport.py', 'Drug Review Report', ''),
           ('SemanticTypeReport.py', 'Semantic Type Report', ''),
           ('TermHierarchyTree.py', 'Term Hierarchy Tree', ''),
           ('TermHierarchyTree.py',
            'Terms with No Parent Term and Not a Semantic Type',
            '&SemanticTerms=False')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s%s'>%s</LI></A>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[2], r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
