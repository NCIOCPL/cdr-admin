#----------------------------------------------------------------------
#
# $Id: GeneralReports.py,v 1.10 2004-02-17 20:01:01 venglisc Exp $
#
# Submenu for general reports.
#
# $Log: not supported by cvs2svn $
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
form = "<INPUT TYPE='hidden' NAME='%s' VALUE='%s'><OL>\n" % (cdrcgi.SESSION,
                                                             session)
reports = [
           ('AdHocQuery.py', 
            'Ad-Hoc Reports'),
           ('CheckedOutDocs.py', 
            'Checked Out Documents'),
           ('CdrReport.py', 
            'Checked Out Documents With No Activity'),
           ('ActiveLogins.py', 
            'Current Sessions'),
           ('DateLastModified.py', 
            'Date Last Modified'),
           ('DatedActions.py', 
            'Dated Actions'),
           ('ActivityReport.py', 
            'Document Activity Report'),
           ('DocVersionHistory.py', 
            'Document Version History'),
           ('LinkedDocs.py', 
            'Linked Documents'),
           ('NewDocsWithPubStatus.py', 
            'List of New Documents with Publication Status'),
           ('NewDocReport.py', 
            'New Document Count'),
           ('ModWithoutPubVersion.py', 
            'Records Modified Since Last Publishable Version'),
           ('UnchangedDocs.py', 
            'Unchanged Documents'),
           ('CheckUrls.py', 
            'URL Check')
          ]

for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
