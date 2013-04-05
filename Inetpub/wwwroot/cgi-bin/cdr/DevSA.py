#----------------------------------------------------------------------
#
# $Id$
#
# Main menu for Developers and System Administrators.
#
# BZIssue::5296
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
section = "Developers/System Administrators"
buttons = []
html    = cdrcgi.header(title, title, section, "", buttons) + """\
   <ol>
"""
items   = (('EditGroups.py',           'Manage Groups'                 ),
           ('EditUsers.py',            'Manage Users'                  ),
           ('EditActions.py',          'Manage Actions'                ),
           ('EditDoctypes.py',         'Manage Document Types'         ),
           ('EditQueryTermDefs.py',    'Manage Query Term Definitions' ),
           ('EditLinkControl.py',      'Manage Linking Tables'         ),
           ('EditFilters.py',          'Manage Filters'                ),
           ('EditFilterSets.py',       'Manage Filter Sets'            ),
           ('Publishing.py',           'Publishing'                    ),
           ('ReverifyJob.py',          'Reverify Push Job'             ),
           ('Republish.py',            'Re-Publishing'                 ),
           ('FailBatchJob.py',         'Fail Publishing or Batch Job'  ),
           ('Reports.py',              'Reports'                       ),
           ('Mailers.py',              'Mailers'                       ),
           ('GlobalChangeMenu.py',     'Global Changes'                ),
           ('getBatchStatus.py',       'Batch Job Status'              ),
           ('MessageLoggedInUsers.py', 'Send Email to Users Currently '
                                       'Logged in to the CDR'          ),
           ('CTGov.py',                'CTGov Protocols'               ),
           ('UnblockDoc.py',           'Unblock Documents'             ),
           ('EditExternMap.py',        'Update Mapping Table'          ),
           ('Request1931.py',
            'Guess ExpectedEnrollment from ProjectedAccrual'),
           ('ReplaceCWDwithVersion.py','Replace CWD with Older Version'),
           ('del-some-docs.py',        'Delete CDR Documents'          ),
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
