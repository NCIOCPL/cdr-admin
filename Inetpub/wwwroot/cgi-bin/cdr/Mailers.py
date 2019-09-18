#----------------------------------------------------------------------
# Main menu for mailer jobs.
#
# BZIssue::4630
# BZIssue::4779
# BZIssue::5239 (JIRA::OCECDR-3543) - menu cleanup
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
title   = "CDR Administration"
section = "Mailers"
buttons = [cdrcgi.DEVTOP, cdrcgi.MAINMENU]
header  = cdrcgi.header(title, title, section, "Mailers.py", buttons)

#----------------------------------------------------------------------
# Return to the main menu if requested.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == cdrcgi.DEVTOP:
    cdrcgi.navigateTo("DevSA.py", session)

#----------------------------------------------------------------------
# List the available options.
#----------------------------------------------------------------------
form = "<OL>\n"
reports = (
    ('SummaryMailerReqForm.py?BoardType=Advisory&',
     'Summary Mailers (Advisory Board)'),
    ('BoardMemberMailerReqForm.py?',
     'PDQ&reg; Board Member Correspondence Mailers'),
)

for r in reports:
    form += "<LI><A HREF='%s/%s%s=%s'>%s</A></LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])
form += """\
<LI><A HREF="%s/Logout.py?%s=%s">%s</LI>
</OL>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session, "Log Out")
cdrcgi.sendPage(header + form + """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>""" % (cdrcgi.SESSION, session))
