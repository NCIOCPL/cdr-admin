#----------------------------------------------------------------------
#
# $Id: DevSA.py,v 1.2 2004-08-10 15:39:26 bkline Exp $
#
# Main menu for Developers and System Administrators.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2003/12/16 16:09:20  bkline
# Main menu for Developers and System Administrators.
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
           ('EditCSSs.py',             'Manage CSS Stylesheets'        ),
           ('EditQueryTermDefs.py',    'Manage Query Term Definitions' ),
           ('EditLinkControl.py',      'Manage Linking Tables'         ),
           ('EditFilters.py',          'Manage Filters'                ),
           ('EditFilterSets.py',       'Manage Filter Sets'            ),
           ('Publishing.py',           'Publishing'                    ),
           ('Reports.py',              'Reports'                       ),
           ('Mailers.py',              'Mailers'                       ),
           ('MergeProt.py',            'Protocol Merge'                ),
           ('GlobalChange.py',         'Global Changes'                ),
           ('getBatchStatus.py',       'Batch Job Status'              ),
           ('MessageLoggedInUsers.py', 'Send Email to Users Currently '
                                       'Logged in to the CDR'          ),
           ('CTGov.py',                'CTGov Protocols'               ),
           ('EditExternMap.py',        'Update Mapping Table'          ),
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
