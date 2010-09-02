#----------------------------------------------------------------------
#
# $Id$
#
# Main menu for CIAT/CIPS staff.
#
# BZIssue::4700
#
# Revision 1.10  2009/07/22 01:25:13  ameyer
# Added GlobalChangeSimpleLink.py.
#
# Revision 1.9  2009/04/28 17:57:26  ameyer
# Renamed Global Changes label for clearer explanation of what it does.
#
# Revision 1.8  2008/09/26 00:19:06  ameyer
# Added functions to replace doc with new doc, replace CWD with older ver.
#
# Revision 1.7  2008/04/17 18:55:40  bkline
# Re-arrangement of CIAT menus at Sheri's request (#4009).
#
# Revision 1.6  2007/10/22 16:02:15  bkline
# Added Oncore report.
#
# Revision 1.5  2007/06/14 20:08:54  bkline
# Plugged in command to upload GENETICSPROFESSIONAL documents.
#
# Revision 1.4  2006/11/29 16:18:43  bkline
# Added new command for reviewing new CTS trials.
#
# Revision 1.3  2004/11/01 21:27:00  venglisc
# Added menu item to ftp images from CIPSFTP.  Alphabetized list. (Bug 1365)
#
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
section = "CIAT/OCCM Staff"
buttons = []
html    = cdrcgi.header(title, title, section, "", buttons) + """\
   <ol>
"""
items   = (('AdvancedSearch.py', 'Advanced Search',       ''               ),
           ('getBatchStatus.py', 'Batch Job Status',      ''               ),
           ('CTGov.py',          'CTGov Protocols',       ''               ),
           ('GlobalChange.py',   'Global Change Protocol Links', ''        ),
           ('GlobalChangeZipCode.py', 'Global Change Zip Codes', ''        ),
           ('FtpImages.py',      'Images Download',       ''               ),
           ('Mailers.py',        'Mailers',               ''               ),
           ('NewTrialsSubmission.py', 'New Trials Submission', '' ),
           ('MergeProt.py',      'Protocol Merge',        ''               ),
           ('Reports.py',        'Reports',               ''               ),
           ('EditExternMap.py',  'Update Mapping Table', '' ),
           ('ReplaceDocWithNewDoc.py', 'Replace Doc with New Doc',       ''),
           ('UploadGPSet.py',    'Upload GENETICSPROFESSIONAL Document Set', '')
           )
for item in items:
    html += """\
    <li><a href='%s/%s%s%s'>%s</a></li>
""" % (cdrcgi.BASE, item[0], session, item[2], item[1])

cdrcgi.sendPage(html + """\
   </ol>
  </form>
 </body>
</html>
""")
