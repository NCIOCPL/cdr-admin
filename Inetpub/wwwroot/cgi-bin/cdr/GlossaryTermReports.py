#----------------------------------------------------------------------
#
# $Id$
#
# Submenu for glossary term reports.
#
# $Log: not supported by cvs2svn $
# Revision 1.24  2009/02/24 16:39:34  bkline
# Updated Term Links report to match new glossary document structures.
#
# Revision 1.23  2009/02/10 22:40:45  bkline
# Added Glossary Term Name with Concept QC Report (request #4478).
#
# Revision 1.22  2009/02/10 21:18:20  bkline
# Changes for issue #4467 requested by William.
#
# Revision 1.21  2009/02/05 20:48:34  bkline
# Plugged in simplified interface for glossary name QC report.
#
# Revision 1.20  2009/02/05 20:26:24  bkline
# Rewritten to implement new menu structure requested by William (#4467).
#
# Revision 1.19  2009/01/08 21:56:26  bkline
# Added Processing Status Report.
#
# Revision 1.18  2008/11/24 14:49:10  bkline
# Added new glossary term definition status reports.
#
# Revision 1.17  2008/11/06 18:50:09  bkline
# Added report for newly published glossary terms.
#
# Revision 1.16  2008/11/04 21:15:32  venglisc
# Modified to run publish preview report for new document structure.
#
# Revision 1.15  2008/10/09 21:05:54  bkline
# Fixed typos in previous version.
#
# Revision 1.14  2008/10/09 21:00:45  bkline
# Added new documents modified reports.
#
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
nyi     = fields.getvalue('nyi')
title   = "CDR Administration"
section = "Glossary Term Reports"
SUBMENU = "Reports Menu"
buttons = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header  = cdrcgi.header(title, title, section, "Reports.py", buttons,
                        stylesheet = """\
  <style type='text/css'>
   ul > li { list-style-type: none }
   h4 { font-style: italic; }
   ol { margin-bottom: 1.25em; } /* workaround for IE bug */
  </style>
""")

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
# If the command behind the menu item hasn't been implemented yet, say so.
#----------------------------------------------------------------------
if nyi:
    cdrcgi.bail("This menu command has not yet been implemented")

#----------------------------------------------------------------------
# Display available report choices.
#----------------------------------------------------------------------
form = ["""\
   <input type='hidden' name='%s' value='%s' />
   <h3>QC Reports</h3>
   <ul>
    <li><h4>Glossary Term Name</h4>
     <ol>
""" % (cdrcgi.SESSION, session)]
for r in ( # was using GlossaryTermSearch.py
    ('QcReport.py?DocType=GlossaryTermName&', 'Glossary Term Name QC Report'),
):
    form.append("""\
    <li><a href='%s/%s%s=%s'>%s</a></li>
""" % (cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1]))
form.append("""\
     </ol>
    </li>
    <li><h4>Glossary Term Concept</h4>
     <ol>
""")
for r in (
    ('QcReport.py?DocType=GlossaryTermConcept&',
     'Glossary Term Concept QC Report'),
):
    form.append("""\
    <li><a href='%s/%s%s=%s'>%s</a></li>
""" % (cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1]))
form.append("""\
     </ol>
    </li>
    <li><h4>Combined QC Reports</h4>
     <ol>
""")
for r in (
    # replace GlossaryTermSearch.py with simpler version
    ('QcReport.py?DocType=GlossaryTermName&ReportType=gtnwc&',
     'Glossary Term Name with Concept QC Report'),
    ('GlossaryConceptFull.py?', 'Glossary Term Concept - Full QC Report')
):
    form.append("""\
      <li><a href='%s/%s%s=%s'>%s</a></li>
""" % (cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1]))
form.append("""\
     </ol>
    </li>
   </ul>
   <h3>Management Reports</h3>
   <ul>
    <li><h4>Linked or Related Document Reports</h4>
     <ol>
""")
for r in (
    (#'GlossaryTermReports.py?nyi=1&', # needs rewrite of GlossaryTermLinks.py
    'GlossaryTermLinks.py?',
     'Documents Linked to Glossary Term Name Report'),
    ('PronunciationByWordStem.py?',
     'Pronunciation by Glossary Term Stem Report'),
    ('Request4486.py?', 'Glossary Term Concept By Type Report'),
    ('GlossaryTermPhrases.py?', 'Glossary Term and Variant Search Report')
):
    form.append("""\
      <li><a href='%s/%s%s=%s'>%s</a></li>
""" % (cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1]))
form.append("""\
     </ol>
    </li>
    <li><h4>Processing Reports</h4>
     <ol>
""")
for r in (
    ('GlossaryProcessingStatusReport.py?', "Processing Status Report"),
    ('Request4344.py?report=4342&',
     'Glossary Term Concept by English Definition Status Report'),
    ('Request4344.py?report=4344&',
     'Glossary Term Concept by Spanish Definition Status Report'),
    ('GlossaryConceptDocsModified.py?', 
     'Glossary Term Concept Documents Modified Report'),
    ('GlossaryNameDocsModified.py?', 
     'Glossary Term Name Documents Modified Report')
):
    form.append("""\
      <li><a href='%s/%s%s=%s'>%s</a></li>
""" % (cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1]))
form.append("""\
     </ol>
    </li>
    <li><h4>Publication Reports</h4>
     <ol>
""")
for r in (
    ('QcReport.py?DocType=GlossaryTermName&ReportType=pp&', 'Publish Preview'),
    ('Request4333.py?', "New Published Glossary Terms")
):
    form.append("""\
      <li><a href='%s/%s%s=%s'>%s</a></li>
""" % (cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1]))
form.append("""\
     </ol>
    </li>
   </ul>
  </form>
 </body>
</html>
""")
form = "".join(form)
cdrcgi.sendPage(header + form)
