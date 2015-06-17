#----------------------------------------------------------------------
#
# $Id$
#
# Main menu for CIAT/CIPS staff.
#
# BZIssue::1365
# BZIssue::4009
# BZIssue::4700
# BZIssue::5013 - [Glossary Audio] Create Audio Download Tool
# BZIssue::4942 - CTRP mapping gaps
# BZIssue::5239 (JIRA::OCECDR-3543) - menu cleanup
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)

#----------------------------------------------------------------------
# Make sure the login was successful.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown user id or password.')

#----------------------------------------------------------------------
# Put up the menu.
session = "?%s=%s" % (cdrcgi.SESSION, session)
title   = "CDR Administration"
section = "CIAT/OCCM Staff"
buttons = []
html    = cdrcgi.header(title, title, section, "", buttons) + """\
   <ol>
"""
items   = (('AdvancedSearch.py', 'Advanced Search',       ''               ),
           ('FtpAudio.py',       'Audio Download',        ''               ),
           ('ocecdr-3373.py',    'Audio Import',          ''               ),
           ('ocecdr-3606.py',
            'Audio Request Spreadsheet (clicking this writes to the database)',
            ' title="Don\'t click this if you\'re not ready to generate\n'
            'a spreadsheet for pronunciation audio requests)"'),
           ('GlossaryTermAudioReview.py', 'Audio Review Glossary Term',  ''),
           ('getBatchStatus.py', 'Batch Job Status',      ''               ),
           ('CTGov.py',          'CTGov Protocols',       ''               ),
           ('ctrp-mapping-gaps.py', 'CTRP Mapping Gaps',  ''               ),
           ('Mailers.py',        'Mailers',               ''               ),
           ('Reports.py',        'Reports',               ''               ),
           ('EditExternMap.py',  'Update Mapping Table', '' ),
           ('ReplaceCWDwithVersion.py','Replace CWD with Older Version', ''),
           ('ReplaceDocWithNewDoc.py', 'Replace Doc with New Doc',       ''),
           ('UpdatePreMedlineCitations.py', 'Update Pre-Medline Citations', ''),
           )
for item in items:
    html += """\
    <li><a href='%s/%s%s'%s>%s</a></li>
""" % (cdrcgi.BASE, item[0], session, item[2], item[1])

cdrcgi.sendPage(html + """\
   </ol>
  </form>
 </body>
</html>
""")
