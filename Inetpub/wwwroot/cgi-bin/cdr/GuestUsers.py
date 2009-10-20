#----------------------------------------------------------------------
#
# $Id: DevSA.py,v 1.10 2009-07-15 01:42:07 ameyer Exp $
#
# Main menu for Guest Users
# -------------------------
# We want to prevent that guest users might accidentally modify data
# or submit a publishing job.  Therefore, we're limiting the menu
# options to these users that are guest group members.
#
# BZIssue::4653
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
#----------------------------------------------------------------------
session = "?%s=%s" % (cdrcgi.SESSION, session)
title   = "CDR Administration"
section = "Guest Users"
buttons = []
html    = cdrcgi.header(title, title, section, "", buttons) + """\
   <ol>
"""
items   = (('AdvancedSearch.py',       'Advanced Search Menu'          ),
           ('TerminologyReports.py',   'Terminology Reports'),
           ('Logout.py',               'Log Out'                       )
           )
for item in items:
    html += """\
    <li><a href='%s/%s%s'>%s</a></li>
""" % (cdrcgi.BASE, item[0], session, item[1])

cdrcgi.sendPage(html + """\
   </ol>
  </form>
 </body>
</html>
""")
