#----------------------------------------------------------------------
#
# $Id: DevSA.py,v 1.10 2009-07-15 01:42:07 ameyer Exp $
#
# Main menu for Developers and System Administrators.
#
# $Log: not supported by cvs2svn $
# Revision 1.9  2009/04/28 17:53:17  ameyer
# Added another global change task.  Renamed old one for more explanatory name.
#
# Revision 1.8  2008/09/26 00:20:53  ameyer
# Removed Replace Doc with New Doc.  Now in CiatCipsStaff.py menu.
#
# Revision 1.7  2008/07/04 02:57:21  ameyer
# Added menu entries for saving old version as CWD, replacing Summary.
#
# Revision 1.6  2007/10/31 16:03:33  bkline
# Added republish command.
#
# Revision 1.5  2006/01/19 21:12:24  ameyer
# Added ProjectedAccrual processing to menu.  May remove it later.
#
# Revision 1.4  2005/07/07 22:26:35  venglisc
# Removed menu item to update CSS Stylesheets. (Bug 1747)
#
# Revision 1.3  2004/08/26 14:05:52  bkline
# Added unblock page.
#
# Revision 1.2  2004/08/10 15:39:26  bkline
# Plugged in new menu items for editing the external mapping values.
#
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
           ('EditQueryTermDefs.py',    'Manage Query Term Definitions' ),
           ('EditLinkControl.py',      'Manage Linking Tables'         ),
           ('EditFilters.py',          'Manage Filters'                ),
           ('EditFilterSets.py',       'Manage Filter Sets'            ),
           ('Publishing.py',           'Publishing'                    ),
           ('Republish.py',            'Re-Publishing'                 ),
           ('Reports.py',              'Reports'                       ),
           ('Mailers.py',              'Mailers'                       ),
           ('MergeProt.py',            'Protocol Merge'                ),
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
