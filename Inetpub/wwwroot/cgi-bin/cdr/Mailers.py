#----------------------------------------------------------------------
#
# $Id$
#
# Main menu for mailer jobs.
#
# $Log: not supported by cvs2svn $
# Revision 1.10  2004/07/17 11:52:54  bkline
# Plugged in user interface for generating PDQ Board Member Correspondence
# Mailers.
#
# Revision 1.9  2004/07/13 17:47:06  bkline
# Added electronic mailer review.
#
# Revision 1.8  2002/10/24 20:10:42  bkline
# Added separate items for Editorial and Advisory boards mailers.
#
# Revision 1.7  2002/10/24 02:50:38  bkline
# Fixed typo (missing closing parenthesis).
#
# Revision 1.6  2002/10/24 02:49:45  bkline
# Further consolidation of menu items.
#
# Revision 1.5  2002/06/04 19:15:01  ameyer
# Removed New Physician Initial Mailer - now part of directory mailers.
#
# Revision 1.4  2002/03/19 23:46:36  ameyer
# Added line for directory mailers.  Will eventually remove physician mailer.
#
# Revision 1.3  2002/02/21 22:34:00  bkline
# Added navigation buttons.
#
# Revision 1.2  2001/12/25 01:19:06  bkline
# Added missing </A> tag; added two mailers.
#
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
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