#----------------------------------------------------------------------
#
# $Id: Reports.py,v 1.2 2001-12-01 18:07:34 bkline Exp $
#
# Prototype for editing CDR linking tables.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2001/06/13 22:16:32  bkline
# Initial revision
#
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
title   = "CDR Administration"
section = "Reports"
buttons = []
header  = cdrcgi.header(title, title, section, "", buttons)

#----------------------------------------------------------------------
# Put up a stub page for now.
#----------------------------------------------------------------------
form = "<OL>\n"
reports = [('CdrReport.py', 'Inactive Documents'),
           ('UnchangedDocs.py', 'Unchanged Documents'),
           ('CheckUrls.py', 'Inactive Hyperlinks'),
           ('TermUsage.py', 'Term Usage'),
           ('ModifiedPubMedDocs.py', 'Modified PubMed Documents')]
if type(reports) == type(""): cdrcgi.bail(reports)

for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """\
<LI><A HREF="%s/Logout.py?%s=%s">%s</LI>
</OL>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session, "Log Out")
cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")
