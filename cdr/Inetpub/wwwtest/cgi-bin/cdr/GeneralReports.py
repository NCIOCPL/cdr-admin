#----------------------------------------------------------------------
#
# $Id: GeneralReports.py,v 1.1 2002-05-24 20:37:30 bkline Exp $
#
# Submenu for general reports.
#
# $Log: not supported by cvs2svn $
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
           ('CdrReport.py', 'Inactive Documents'),
           ('LinkedDocs.py', 'Linked Documents'),
           ('NewDocReport.py', 'New Document Count'),
           ('PubJobQueue.py', 'Publishing Job Queue'),
           ('UnchangedDocs.py', 'Unchanged Documents'),
           ('CheckUrls.py', 'URL Check'),
          ]

for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
