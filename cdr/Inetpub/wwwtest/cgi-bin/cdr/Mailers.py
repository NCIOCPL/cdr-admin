#----------------------------------------------------------------------
#
# $Id: Mailers.py,v 1.1 2001-12-01 18:11:44 bkline Exp $
#
# Main menu for mailer jobs.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
title   = "CDR Administration"
section = "Mailers"
buttons = []
header  = cdrcgi.header(title, title, section, "", buttons)

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
           ('NewPhysicianInitMailerReqForm.py', 'New Physician Initial Mailer')]

for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """\
<LI><A HREF="%s/Logout.py?%s=%s">%s</LI>
</OL>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session, "Log Out")
cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")
