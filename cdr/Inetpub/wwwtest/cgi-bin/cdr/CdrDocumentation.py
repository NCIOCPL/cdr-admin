#----------------------------------------------------------------------
#
# $Id: CdrDocumentation.py,v 1.1 2004-09-20 20:30:21 venglisc Exp $
#
# Prototype for CDR reporting/formatting web wrapper.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
request = cdrcgi.getRequest(fields)
SUBMENU = "Report Menu"

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Put out the form if we don't have a request.
#----------------------------------------------------------------------
title   = "CDR Administration"
instr   = "CDR Documentation (PDF)"
buttons = ("Submit Request", SUBMENU, cdrcgi.MAINMENU)
header  = cdrcgi.header(title, title, instr, "CdrDocumentation.py", buttons)
server  = "bach.nci.nih.gov"
location= "cdr/Documentation"
usrdocs = [['CdrUserGuide.pdf',  'User Guide'],
           ['CdrSystemDocs.pdf', 'System Documentation'], 
	   ['CdrOpsManual.pdf',  'Operation Manual']]

form    = """\
  <h3>CDR Documentation (PDF) as of 2004-09-08</h3>
  <ol>
"""

for row in usrdocs:
   form += """\
   <li><a href="http://%s/%s/%s">%s</a></li>
""" % (server, location, row[0], row[1])

form    += """\
  </ol>
 </body>
</html>
"""
cdrcgi.sendPage(header + form)
