#----------------------------------------------------------------------
#
# $Id: GeneralReports.py,v 1.6 2002-07-02 13:47:55 bkline Exp $
#
# Submenu for general reports.
#
# $Log: not supported by cvs2svn $
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
           ('Stub.py', 'Ad-Hoc Reports'),
           ('CheckedOutDocs.py', 'Checked Out Documents'),
           ('DateLastModified.py', 'Date Last Modified'),
           ('DatedActions.py', 'Dated Actions'),
           ('CdrReport.py', 'Checked Out Documents With No Activity'),
           ('LinkedDocs.py', 'Linked Documents'),
           ('NewDocReport.py', 'New Document Count'),
           ('PubJobQueue.py', 'Publishing Job Queue'),
           ('UnchangedDocs.py', 'Unchanged Documents'),
           ('CheckUrls.py', 'URL Check'),
           ('ActivityReport.py', 'Document Activity Report'),
           ('ActiveLogins.py', 'Current Sessions'),
           ('DocVersionHistory.py', 'Document Version History'),
           ('NewDocsWithPubStatus.py', 
            'List of New Documents with Publication Status'),
          ]

for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
