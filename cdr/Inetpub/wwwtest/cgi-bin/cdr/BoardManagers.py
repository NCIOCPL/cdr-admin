#----------------------------------------------------------------------
#
# $Id: BoardManagers.py,v 1.4 2004-04-08 20:31:10 bkline Exp $
#
# Main menu for board managers.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2003/12/19 18:29:08  bkline
# Plugged in new Summaries LIsts report.
#
# Revision 1.2  2003/12/18 22:16:41  bkline
# Alphabetized first section at Volker's request (with Lakshmi's
# concurrence).
#
# Revision 1.1  2003/12/16 16:02:14  bkline
# Main menu for board managers.
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
section = "Board Managers"
buttons = []
header  = cdrcgi.header(title, title, section, "BoardManagers.py", buttons,
                        numBreaks = 1, stylesheet = """\
  <style type='text/css'>
   h2 { font-family: Arial; font-size: 14pt; font-weight: bold }
   li { font-family: Arial; font-size: 12pt; font-weight: bold }
  </style>
""")

#----------------------------------------------------------------------
# Display available menu choices.
#----------------------------------------------------------------------
session = "%s=%s" % (cdrcgi.SESSION, session)
form = """\
   <h2>General Use Reports</h2>
   <ol>
"""
for choice in (
    ('GeneralReports.py', 'All General Reports'         ),
    ('CheckedOutDocs.py', 'Checked Out Documents Report'),
    ('ActivityReport.py', 'Document Activity Report'    ),
    ('LinkedDocs.py',     'Linked Documents Report'     ),
    ('UnchangedDocs.py',  'Unchanged Documents Report'  )
    ):
    form += """\
    <li><a href='%s/%s?%s'>%s</a></li>
""" % (cdrcgi.BASE, choice[0], session, choice[1])

form += """\
   </ol>
   <h2>Summary QC Reports</h2>
   <ol>
"""
for choice in (
    ('bu',  'Bold/Underline (HP/Old Patient)'   ),
    ('rs',  'Redline/Strikeout (HP/Old Patient)'),
    ('pat', 'New Patient'                       )
    ):
    form += """\
    <li><a href='%s/QcReport.py?DocType=Summary&ReportType=%s&%s'>%s</a></li>
""" % (cdrcgi.BASE, choice[0], session, choice[1])

form += """\
   </ol>
   <h2>Management Reports</h2>
   <ol>
"""

for choice in (
    ('SummaryChanges.py',          'History of Changes'          ),
    ('PdqBoards.py',               'PDQ Board Listings'          ),
    ('SummaryCitations.py',        'Summaries Citations'         ),
    ('SummaryDateLastModified.py', 'Summaries Date Last Modified'),
    ('SummariesLists.py',          'Summaries Lists'             ),
    ('SummaryMetaData.py',         'Summaries Metadata'         )
    ):
    form += """\
    <li><a href='%s/%s?%s'>%s</a></li>
""" % (cdrcgi.BASE, choice[0], session, choice[1])
    
form += """\
   </ol>
   <h2>Board Member Information Reports</h2>
   <ol>
"""

for choice in (
    ('Stub.py',          'Board Member Information QC Report' ),
    ('Stub.py',               'Board Roster Reports'               )
    ):
    form += """\
    <li><a href='%s/%s?%s'>%s</a></li>
""" % (cdrcgi.BASE, choice[0], session, choice[1])
    
cdrcgi.sendPage(header + form + """\
   </ol>
   <h2>Miscellaneous Document QC Report</h2>
   <ol>
    <li><a href='%s/MiscSearch.py?%s'>Miscellaneous Documents</a></li>
   </ol>
  </form>
 </body>
</html>""" % (cdrcgi.BASE, session))
