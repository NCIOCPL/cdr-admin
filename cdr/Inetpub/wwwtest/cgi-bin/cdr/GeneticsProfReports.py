#----------------------------------------------------------------------
#
# $Id: GeneticsProfReports.py,v 1.1 2009-03-09 16:44:57 venglisc Exp $
#
# $Log: not supported by cvs2svn $
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
section = "Genetics Professional Reports"
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
    <H3>Upload Reports</H3>
    <OL>                                                                        
""" % (cdrcgi.SESSION, session)                                                 
QCReports = [('GeneticsProfUploadFiles.py', 
              'Document Upload Statistics'),
             ('stub.py',
              'Folders Uploaded')]

for r in QCReports:
    form += "<LI><A HREF='%s/%s&%s=%s'>%s</LI></A>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

cdrcgi.sendPage(header + form + "</OL></FORM></BODY></HTML>")
