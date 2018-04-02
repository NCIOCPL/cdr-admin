#----------------------------------------------------------------------
# Main menu for Developers and System Administrators.
# BZIssue::5296
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)

#----------------------------------------------------------------------
# Make sure the user is allow to use this menu.
#----------------------------------------------------------------------
if not cdr.member_of_group(session, "Developer/SysAdmin Menu Users"):
    cdrcgi.bail("User not authorized for this menu")

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
           ('set-ctl-value.py',        'Manage Control Values'         ),
           ('EditDocTypes.py',         'Manage Document Types'         ),
           ('EditQueryTermDefs.py',    'Manage Query Term Definitions' ),
           ('EditLinkControl.py',      'Manage Linking Tables'         ),
           ('EditFilters.py',          'Manage Filters'                ),
           ('EditFilterSets.py',       'Manage Filter Sets'            ),
           ("manage-pdq-data-partners.py",
            "Manage PDQ Data Partners"),
           ("edit-value-table.py",     "Manage Value Tables"           ),
           ('getBatchStatus.py',       'Batch Job Status'              ),
           ('FailBatchJob.py',         'Fail Publishing or Batch Job'  ),
           ('GlobalChangeMenu.py',     'Global Changes'                ),
           ('Mailers.py',              'Mailers'                       ),
           ('GetSchema.py',            'Show Schema'                   ),
           ('post-schema.py',          'Post Schema'                   ),
           ('Publishing.py',           'Publishing'                    ),
           ('Reports.py',              'Reports'                       ),
           ('ReverifyJob.py',          'Reverify Push Job'             ),
           ('Republish.py',            'Re-Publishing'                 ),
           ('../scheduler/',           'Scheduled Jobs'                ),
           ('MessageLoggedInUsers.py', 'Send Email to Users Currently '
                                       'Logged in to the CDR'          ),
           ('SetNextJobId.py',         'Set Next Job-ID'               ),
           ('UnblockDoc.py',           'Unblock Documents'             ),
           ('EditExternMap.py',        'Update Mapping Table'          ),
           ('upload-zip-code-file.py', 'Update ZIP Codes'              ),
           ('ReplaceCWDwithVersion.py','Replace CWD with Older Version'),
           ('clear-filesweeper-lockfile.py',
            'Clear FileSweeper Lock File'),
           ('del-some-docs.py',        'Delete CDR Documents'          ),
           ('fetch-tier-settings.py',  'Fetch Tier Settings'           ),
           ('log-tail.py',             'View Logs'                     ),
           ('Logout.py',               'Log Out'                       )
           )
for item in items:
    if cdr.isProdHost() and item[0] == 'SetNextJobId.py':
        continue
    html += """\
    <li><a href='%s/%s%s'>%s</a></li>
""" % (cdrcgi.BASE, item[0], session, item[1])

cdrcgi.sendPage(html + """\
   </ol>
  </form>
 </body>
</html>
""")
