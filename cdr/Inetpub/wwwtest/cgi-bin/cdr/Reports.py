#----------------------------------------------------------------------
#
# $Id: Reports.py,v 1.7 2002-03-09 03:27:40 bkline Exp $
#
# Prototype for editing CDR linking tables.
#
# $Log: not supported by cvs2svn $
# Revision 1.6  2002/03/02 13:50:31  bkline
# Added report for checked-out documents.
#
# Revision 1.5  2002/02/26 18:55:29  bkline
# Sorted report menu alphabetically.
#
# Revision 1.4  2002/02/21 15:22:03  bkline
# Added navigation buttons.
#
# Revision 1.3  2002/01/22 21:32:01  bkline
# Added three new reports.
#
# Revision 1.2  2001/12/01 18:07:34  bkline
# Added some new reports.
#
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
action  = cdrcgi.getRequest(fields)
title   = "CDR Administration"
section = "Reports"
buttons = [cdrcgi.MAINMENU]
header  = cdrcgi.header(title, title, section, "Reports.py", buttons)

#----------------------------------------------------------------------
# Return to the main menu if requested.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)

#----------------------------------------------------------------------
# Display available report choices.
#----------------------------------------------------------------------
form = "<INPUT TYPE='hidden' NAME='%s' VALUE='%s'><OL>\n" % (cdrcgi.SESSION,
                                                             session)
reports = [
           ('CheckedOutDocs.py', 'Checked Out Documents'),
           ('ConceptTermReviewReport.py', 'Concept/Term Review Report'),
           ('CdrReport.py', 'Inactive Documents'),
           ('CheckUrls.py', 'Inactive Hyperlinks'),
           ('LinkedDocs.py', 'Linked Documents'),
           ('ModifiedPubMedDocs.py', 'Modified PubMed Documents'),
           ('PdqBoards.py', 'PDQ Boards'),
           ('TermUsage.py', 'Term Usage'),
           ('UnchangedDocs.py', 'Unchanged Documents'),
           ('UnverifiedCitations.py', 'Unverified Citations')
          ]
if type(reports) == type(""): cdrcgi.bail(reports)

for r in reports:
    form += "<LI><A HREF='%s/%s?%s=%s'>%s</LI>\n" % (
            cdrcgi.BASE, r[0], cdrcgi.SESSION, session, r[1])

form += """\
<LI><A HREF="%s/Logout.py?%s=%s">%s</LI>
</OL>
""" % (cdrcgi.BASE, cdrcgi.SESSION, session, "Log Out")
cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")
