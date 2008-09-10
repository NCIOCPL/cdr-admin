#----------------------------------------------------------------------
#
# $Id: DrugInfoReports.py,v 1.4 2008-09-10 17:31:44 venglisc Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2007/04/27 22:51:54  venglisc
# Adding new menu item for Publish Preview.
#
# Revision 1.1  2006/05/16 20:45:24  venglisc
# Initila copy of DrugInfoSummary reports menu (Bug 2053).
#
# Inintial version of Drug Information Reports Menu page of the 
# Admin interface. (Bug 2053)
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
section = "Drug Information Reports"
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
# Display available menu choices.
#----------------------------------------------------------------------
form = """                                                                     
    <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
    <H3>QC Reports</H3>
    <OL>                                                                        
""" % (cdrcgi.SESSION, session)                                                 
QCReports = [('QcReport.py?DocType=DrugInformationSummary', 
            'Drug Information QC Report'),
           ('QcReport.py?DocType=DrugInformationSummary&ReportType=pp&',
           'Publish Preview')]

for r in QCReports:
    form += "<LI><A HREF='%s/%s&%s=%s'>%s</LI></A>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """</OL><H3>Other Reports</H3><OL>"""

OtherReports = [
           ('DrugDescriptionReport.py?', 'Drug Description Report'),
           ('DISLists.py?',              'Drug Information Summaries Lists')]

for r in OtherReports:
    form += "<LI><A HREF='%s/%s&%s=%s'>%s</LI></A>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
