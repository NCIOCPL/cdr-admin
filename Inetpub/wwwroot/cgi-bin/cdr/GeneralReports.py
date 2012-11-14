#----------------------------------------------------------------------
#
# $Id$
#
# Submenu for general reports.
#
# $Log: not supported by cvs2svn $
# Revision 1.20  2008/12/01 22:26:38  venglisc
# Adding back in the Ad-hoc SQL interface.
#
# Revision 1.19  2008/07/11 20:15:32  bkline
# Replaced old ad hoc query interface on menu with new one (at Lakshmi's
# request, #4126).
#
# Revision 1.18  2007/08/27 17:13:39  bkline
# Added report for invalid documents.
#
# Revision 1.17  2007/05/18 20:29:11  venglisc
# Minor HTML formatting changes.
#
# Revision 1.16  2007/05/04 23:42:24  venglisc
# Added new menu item for Linked Media Documents.
#
# Revision 1.15  2005/08/17 20:08:19  venglisc
# Added new menu option to display table names and columns.
#
# Revision 1.14  2005/08/17 19:14:24  venglisc
# Added new menu item under for the CdrFilter.html UI.
#
# Revision 1.13  2005/05/04 19:19:53  bkline
# Added Documents Modified report.
#
# Revision 1.12  2004/11/12 15:57:02  venglisc
# Added External Map Failures Report menu option. (Bug 1417)
#
# Revision 1.11  2004/11/04 21:40:45  venglisc
# Added menu option for access to Global Change Diff reports (Bug 1373).
#
# Revision 1.10  2004/02/17 20:01:01  venglisc
# Removed unused menu items.
#
# Revision 1.9  2003/12/18 22:19:53  bkline
# Alphabetized menu items at Volker's request (with Lakshmi's
# concurrence).
#
# Revision 1.8  2002/09/11 23:28:50  bkline
# Added report on documents modified since their most recent publishable
# version was created.
#
# Revision 1.7  2002/07/10 19:33:33  bkline
# New interface for ad hoc SQL queries.
#
# Revision 1.6  2002/07/02 13:47:55  bkline
# New report on new documents with publication status.
#
# Revision 1.5  2002/06/28 13:38:07  bkline
# New report for document version history added.
#
# Revision 1.4  2002/06/27 12:21:01  bkline
# Added new report for active sessions.
#
# Revision 1.3  2002/06/26 16:35:16  bkline
# Implmented report of audit_trail activity.
#
# Revision 1.2  2002/06/07 13:32:12  bkline
# Issue #255: changed report title at Margaret's request.
#
# Revision 1.1  2002/05/24 20:37:30  bkline
# New Report Menu structure implemented.
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
section = "General Reports"
SUBMENU = "Reports Menu"
buttons = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header  = cdrcgi.header(title, title, section, "Reports.py", buttons)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if action == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Display available report choices.
#----------------------------------------------------------------------
form = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <OL>""" % (cdrcgi.SESSION, session)

reports = [
           ('CdrQueries.py',
            'Ad-Hoc Reports'),
           ('AdHocQuery.py',
            'Ad-Hoc SQL'),
           ('CheckedOutDocs.py',
            'Checked Out Documents'),
           ('CdrReport.py',
            'Checked Out Documents With No Activity'),
           ('ContentInventory.py',
            'Content Inventory Report'),
           ('ActiveLogins.py',
            'Current Sessions'),
           ('db-tables.py',
            'Database Tables/Columns'),
           ('DateLastModified.py',
            'Date Last Modified'),
           ('DatedActions.py',
            'Dated Actions'),
           ('ActivityReport.py',
            'Document Activity Report'),
           ('DocVersionHistory.py',
            'Document Version History'),
           ('DocumentsModified.py',
            'Documents Modified'),
           ('ExternMapFailures.py',
            'External Map Failures Report'),
           ('CdrFilter',
            'Filter Document'),
           ('ShowGlobalChangeTestResults.py',
            'Global Change Test Results'),
           ('InvalidDocs.py',
            'Invalid Documents'),
           ('LinkedDocs.py',
            'Linked Documents'),
           ('MediaLinks.py',
            'Linked Media Documents'),
           ('NewDocsWithPubStatus.py',
            'List of New Documents with Publication Status'),
           ('NewDocReport.py',
            'New Document Count'),
           ('ModWithoutPubVersion.py',
            'Records Modified Since Last Publishable Version'),
           ('UnchangedDocs.py',
            'Unchanged Documents'),
           ('CheckUrls.py',
            'URL Check (Batch job - runs ~15 min)'),
           ('ReplaceCWDReport.py',
            'Versions that Replaced CWDs')
          ]

for r in reports:
    if r[0] != 'CdrFilter':
       form += """
    <LI><A HREF='%s/%s?%s=%s'>%s</A></LI>""" % (cdrcgi.BASE, r[0],
                                            cdrcgi.SESSION,
                                            session, r[1])
    else:
       form += """
    <LI><A HREF='/cdrFilter.html'>%s</A></LI>""" % (r[1])

footer = """
   </OL>
  </FORM>
 </BODY>
</HTML>"""

cdrcgi.sendPage(header + form + footer)
