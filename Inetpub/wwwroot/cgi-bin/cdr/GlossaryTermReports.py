#----------------------------------------------------------------------
# Submenu for glossary term reports.
#
# BZIssue::1447 - rearrange menu for Margaret
# BZIssue::1531 - add menu option for publish preview reports
# BZIssue::3948 - add new menu item for glossary term full report
# BZIssue::4467 - implement new menu structure requested by William
# BZIssue::4478 - add glossary term name with concept QC report
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
