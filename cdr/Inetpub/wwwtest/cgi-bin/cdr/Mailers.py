#----------------------------------------------------------------------
#
# $Id: Mailers.py,v 1.5 2002-06-04 19:15:01 ameyer Exp $
#
# Main menu for mailer jobs.
#
# $Log: not supported by cvs2svn $
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
reports = [('PDQMailerRequestForm.py', 'PDQ Editorial Board Members Mailing'),
           ('ProtAbstractMailerReqForm.py',
            'Protocol Abstract Initial Verification Mailer'),
           ('ProtAbstractUpdateMailer.py',
            'Protocol Abstract Update Mailer'),
           ('StatAndParticMailer.py',
            'Protocol Status and Participant Initial Verification Mailer'),
           ('StatAndParticUpdateMailer.py',
            'Protocol Status and Participant Update Verification Mailer'),
           ('DirectoryMailerReqForm.py',
            'Directory Mailers')]

for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</A></LI>\n" % (
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
