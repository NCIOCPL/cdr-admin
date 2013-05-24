#----------------------------------------------------------------------
#
# $Id$
#
# Prototype for CDR reporting/formatting web wrapper.
#
# $Log: not supported by cvs2svn $
# Revision 1.4  2006/09/28 23:12:45  ameyer
# Fixed spelling error.
#
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
tier    = 'PROD'
location= "cdr/Documentation"
cgiLoc  = "cgi-bin/cdr"
usrdocs = [['CdrUserGuide.pdf',  'User Guide'],
           ['CdrSystemDocs.pdf', 'System Documentation'],
	       ['CdrOpsManual.pdf',  'Operation Manual']]
usrhtml = [['Help.py', 'User Guide'],
           ['Help.py?flavor=System%', 'System Documentation'],
           ['Help.py?flavor=Operating%Instructions', 'Operation Manual']]

# Resolve tier to host fully qualified name in CBIIT environment
hostInfo = cdr.h.getTierHostNames(tier, 'APPWEB')
server   = hostInfo.qname

form = """\
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  <h3>CDR Documentation (PDF) as of 2007-08-22</h3>
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
   <li><a href="%s">%s</a></li>
""" % (cdr.h.makeCdrCgiUrl(tier, row[0]), row[1])

form    += """\
  </ol>
 </body>
</html>
"""
cdrcgi.sendPage(header + form)
