#----------------------------------------------------------------------
# Menu for Global changes.
# BZIssue::5239 (JIRA::OCECDR-3543)
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
#----------------------------------------------------------------------
session = "?%s=%s" % (cdrcgi.SESSION, session)
title   = "CDR Administration"
section = "Global Change Menu"
buttons = []
html    = cdrcgi.header(title, title, section, "", buttons) + """\
  <ol>
"""
items   = (
           ('ShowGlobalChangeTestResults.py','Global Change Test Results'),
           ('Logout.py',               'Log Out'                       )
           )
for item in items:
    html += """\
   <li><a href='%s/%s%s'>%s</a></li>
""" % (cdrcgi.BASE, item[0], session, item[1])

cdrcgi.sendPage(html + """\
  </ol>
 </body>
</html>
""")
