#----------------------------------------------------------------------
#
# $Id$
#
# Main menu for mailer jobs.
#
# BZIssue::4630
# BZIssue::4779
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
section = "Mailers"
buttons = [cdrcgi.MAINMENU]
header  = cdrcgi.header(title, title, section, "Mailers.py", buttons)

#----------------------------------------------------------------------
# Return to the main menu if requested.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# List the available options.
#----------------------------------------------------------------------
form = "<OL>\n"
reports = (('DirectoryMailerReqForm.py?', 'Directory Mailers'),
           ('GPMailerReqForm.py?',  'Genetics Professional Mailers'),
           ('GPPubNotification.py?',
            'Genetics Professional Publication Notification'),
           ('ProtocolMailerReqForm.py?',  'Protocol Mailers'),
           ('SummaryMailerReqForm.py?BoardType=Editorial&',
            'Summary Mailers (Editorial Board)'),
           ('SummaryMailerReqForm.py?BoardType=Advisory&',
            'Summary Mailers (Advisory Board)'),
           ('BoardMemberMailerReqForm.py?',
            'PDQ&reg; Board Member Correspondence Mailers'),
           ('EmailerReview.py?',
            'Electronic Mailer Review (on CDR Server)'))

for r in reports:
    form += "<LI><A HREF='%s/%s%s=%s'>%s</A></LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])
form += """\
<LI><A HREF='http://%s/PDQUpdate/cgi-bin/ShowBatchInfo.py'
>Electronic Mailer Review (on E-Mailer Server)</A></LI>
""" % (cdr.isDevHost() and "verdi.nci.nih.gov" or "pdqupdate.cancer.gov")
form += """\
<LI><A HREF="%s/Logout.py?%s=%s">%s</LI>
</OL>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session, "Log Out")
cdrcgi.sendPage(header + form + """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>""" % (cdrcgi.SESSION, session))
