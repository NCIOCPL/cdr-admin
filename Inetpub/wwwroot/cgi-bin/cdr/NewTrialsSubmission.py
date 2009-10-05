#----------------------------------------------------------------------
#
# $Id: NewTrialsSubmission.py,v 1.1 2008-04-17 18:47:50 bkline Exp $
#
# Sub-menu for CIAT/CIPS staff.
#
# $Log: not supported by cvs2svn $
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
section = "CIAT/CIPS Staff"
buttons = []
html    = [cdrcgi.header(title, title, section, "", buttons) + u"""\
   <h3>New Trials Submission</h3>
   <ol>
"""]
items   = (('CtsSubmittedTrials.py', 'New Oncore Trials', '&source=Oncore' ),
           ('CtsSubmittedTrials.py', 'Submitted Trials Review', '' ),
           )
for item in items:
    html.append("""\
    <li><a href='%s/%s%s%s'>%s</a></li>
""" % (cdrcgi.BASE, item[0], session, item[2], item[1]))
html.append(u"""
   </ol>
   <h3>Reports</h3>
   <ol>
""")
for item in (
    ('Request4010.py', "Oncore Duplicate Trials Report", ''),
    ):
    html.append("""\
    <li><a href='%s/%s%s%s'>%s</a></li>
""" % (cdrcgi.BASE, item[0], session, item[2], item[1]))
html.append(u"""\
   </ol>
  </form>
 </body>
</html>
""")
cdrcgi.sendPage(u"".join(html))
