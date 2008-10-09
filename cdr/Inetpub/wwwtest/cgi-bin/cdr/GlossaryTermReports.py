#----------------------------------------------------------------------
#
# $Id: GlossaryTermReports.py,v 1.14 2008-10-09 21:00:45 bkline Exp $
#
# Submenu for glossary term reports.
#
# $Log: not supported by cvs2svn $
# Revision 1.13  2008/06/12 19:10:34  venglisc
# Adding new menu item for GlossaryTermFull report. (Bug 3948)
#
# Revision 1.12  2007/10/31 16:09:04  bkline
# Added Glossary Term Concept reports.
#
# Revision 1.11  2006/11/29 15:45:32  bkline
# Plugged in new glossary word stem report.
#
# Revision 1.10  2006/07/10 20:34:39  bkline
# Added new report on stale glossary terms.
#
# Revision 1.9  2006/05/17 13:16:08  bkline
# Switched Spanish Glossary Term By Status report to separate script.
#
# Revision 1.8  2006/05/04 13:44:29  bkline
# Changed URL formatting pattern so that it no longer includes the '?'
# starting the parameter list; added new menu items.
#
# Revision 1.7  2005/04/21 21:31:35  venglisc
# Added menu option to allow running Publish Preview reports. (Bug 1531)
#
# Revision 1.6  2004/11/27 00:01:52  bkline
# Menu rearranged at Margaret's request (#1447).
#
# Revision 1.5  2004/10/07 21:39:33  bkline
# Added new report for Sheri, for finding glossary terms created in a
# given date range, and having specified status.
#
# Revision 1.4  2004/09/17 14:06:50  venglisc
# Fixed list items to properly teminate the anker link.
#
# Revision 1.3  2004/08/10 15:44:20  bkline
# Plugged in Glossary Term Search report.
#
# Revision 1.2  2002/05/25 02:39:13  bkline
# Removed extra blank lines from HTML output.
#
# Revision 1.1  2002/05/24 20:37:30  bkline
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
section = "Glossary Term Reports"
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
           ('GlossaryTermSearch.py?', 
            'Glossary Term QC Report'),
           ('GlossaryConceptFull.py?', 
            'Glossary Concept QC Report - Full'),
           ('QcReport.py?DocType=GlossaryTerm&ReportType=pp&', 
            'Publish Preview'),
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s%s=%s'>%s</LI></A>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """\
    </OL>
    <H3>Management Reports</H3>
    <OL>
     <LI><A HREF='%s/PronunciationByWordStem.py?%s=%s'>%s</LI></A>
    </OL>
    <H3>Other Reports</H3>
    <OL>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session,
       "Pronunciation by Term Stem Report")
reports = [
           ('GlossaryTermLinks.py?',
            'Documents Linked to Glossary Term Report'),
           ('Request2010.py?',
            'Drug Definition Report'),
           ('GlossaryDocsModified.py?',
            'Glossary Documents Modified Report'),
           ('GlossaryTermPhrases.py?',
            'Glossary Term and Variant Search Report'),
           ('GlossaryTermsByStatus.py?', 'Glossary Term By Status Report'),
           ('GlossaryTermsByType.py?', 'Glossary Term By Type Report'),
           ('Request2565.aspx?', 'Glossary Term Concept Reports'),
           ('GlossaryConceptDocsModified.py?', 
           'Glossary Term Concept - Ducmnets Modified'),
           ('GlossaryNameDocsModified.py?', 
           'Glossary Term Name - Ducmnets Modified'),
           ('StaleGlossaryTerms.py?', 'Glossary Terms That Need Reviewed'),
           ('SpanishGlossaryTermsByStatus.py?',
            'Spanish Glossary Term By Status Report')
          ]
for r in reports:
    form += "<LI><A HREF='%s/%s%s=%s'>%s</LI></A>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
