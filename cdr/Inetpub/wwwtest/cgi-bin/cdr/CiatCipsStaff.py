#----------------------------------------------------------------------
#
# $Id: CiatCipsStaff.py,v 1.3 2004-11-01 21:27:00 venglisc Exp $
#
# Main menu for CIAT/CIPS staff.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2004/08/10 15:39:26  bkline
# Plugged in new menu items for editing the external mapping values.
#
# Revision 1.1  2003/12/16 16:06:08  bkline
# Main menu for CIAT/CIPS staff.
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
section = "CIAT/CIPS Staff"
buttons = []
html    = cdrcgi.header(title, title, section, "", buttons) + """\
   <ol>
"""
items   = (('AdvancedSearch.py', 'Advanced Search'      ),
           ('getBatchStatus.py', 'Batch Job Status'     ),
           ('CTGov.py',          'CTGov Protocols'      ),
           ('GlobalChange.py',   'Global Changes'       ),
	   ('FtpImages.py',      'Images Download'      ),
           ('Mailers.py',        'Mailers'              ),
           ('MergeProt.py',      'Protocol Merge'       ),
           ('Reports.py',        'Reports'              ),
           ('EditExternMap.py',  'Update Mapping Table' )
           )
#items   = (('AdvancedSearch.py', 'Advanced Search'      ),
#           ('Reports.py',        'Reports'              ),
#           ('MergeProt.py',      'Protocol Merge'       ),
#           ('CTGov.py',          'CTGov Protocols'      ),
#           ('EditExternMap.py',  'Update Mapping Table' ),
#           ('Mailers.py',        'Mailers'              ),
#           ('GlobalChange.py',   'Global Changes'       ),
#           ('getBatchStatus.py', 'Batch Job Status'     )
#           )
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
