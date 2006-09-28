#----------------------------------------------------------------------
#
# $Id: CdrDocumentation.py,v 1.4 2006-09-28 23:12:45 ameyer Exp $
#
# Prototype for CDR reporting/formatting web wrapper.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2006/09/28 23:09:43  ameyer
# Added links for HTML versions of current docs.
# Updated date on PDF.
#
# Revision 1.2  2004/10/07 19:34:37  venglisc
# Fixed the problem of the navigational buttons not working properly.
# (Bug 1338)
#
# Revision 1.1  2004/09/20 20:30:21  venglisc
# Initial version of script to create statis page with links to PDF formatted
# CDR documentation. (Bug 1338)
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
SUBMENU = "Report Menu"

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Put out the form if we don't have a request.
#----------------------------------------------------------------------
title   = "CDR Administration"
instr   = "CDR Documentation (PDF)"
buttons = (SUBMENU, cdrcgi.MAINMENU)
header  = cdrcgi.header(title, title, instr, "CdrDocumentation.py", buttons)
server  = "bach.nci.nih.gov"
location= "cdr/Documentation"
cgiLoc  = "cgi-bin/cdr"
usrdocs = [['CdrUserGuide.pdf',  'User Guide'],
           ['CdrSystemDocs.pdf', 'System Documentation'],
	       ['CdrOpsManual.pdf',  'Operation Manual']]
usrhtml = [['Help.py', 'User Guide'],
           ['Help.py?flavor=System%', 'System Documentation'],
           ['Help.py?flavor=Operating%Instructions', 'Operation Manual']]


form    = """\
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  <h3>CDR Documentation (PDF) as of 2006-09-28</h3>
  <ol>
""" % (cdrcgi.SESSION, session)

for row in usrdocs:
   form += """\
   <li><a href="http://%s/%s/%s">%s</a></li>
""" % (server, location, row[0], row[1])

form += """\
  </ol>
  <h3>CDR Documentation (HTML) - Current</h3>
  <ol>
"""
for row in usrhtml:
   form += """\
   <li><a href="http://%s/%s/%s">%s</a></li>
""" % (server, cgiLoc, row[0], row[1])

form    += """\
  </ol>
 </body>
</html>
"""
cdrcgi.sendPage(header + form)
