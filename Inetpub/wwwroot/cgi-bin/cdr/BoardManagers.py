#----------------------------------------------------------------------
#
#
# $Id$
#
# Main menu for board managers.
#
# BZIssue::4648
# BZIssue::4671 - Summaries with Markup Report
# BZIssue::4673 - Adding Board Roster (Full) option
#
# Revision 1.15  2008/08/26 21:16:18  venglisc
# Added new menu item Changes to Summaries (Bug 4243)
#
# Revision 1.14  2008/08/22 19:40:04  venglisc
# Adding new menu option for Board Meeting Dates. (Bug 4205)
#
# Revision 1.13  2007/11/05 13:10:25  kidderc
# 3672,3666 added two items to menu under Management Reports.
#
# Revision 1.12  2005/10/13 21:33:16  venglisc
# Modified title of one menu item and moved another. (Bug 1853)
#
# Revision 1.11  2005/04/21 21:26:11  venglisc
# Added menu item for Publish Preview report. (Bug 1531)
#
# Revision 1.10  2005/02/23 14:38:01  bkline
# Added link to board member mailer page.
#
# Revision 1.9  2004/09/09 19:19:44  venglisc
# Minor changes to menu entries to have menu items match between the
# CIAT and CIPS summary menu. (Bug 1329).
#
# Revision 1.8  2004/07/13 19:11:14  venglisc
# Added menu item for Summaries TOC Report (Bug 1231).
# Minor formatting changes to list HTML tags in upper case.
#
# Revision 1.7  2004/06/02 15:19:58  venglisc
# Testing CVS server:  Adding extra comment line.
#
# Revision 1.6  2004/05/11 17:29:53  bkline
# Plugged in Board Roster report.
#
# Revision 1.5  2004/04/16 21:56:57  venglisc
# Removed stub to link to Board Member QC report. (Bug 1059).
#
# Revision 1.4  2004/04/08 20:31:10  bkline
# Plugged in additions requested by Margaret (request #1059).
#
# Revision 1.3  2003/12/19 18:29:08  bkline
# Plugged in new Summaries LIsts report.
#
# Revision 1.2  2003/12/18 22:16:41  bkline
# Alphabetized first section at Volker's request (with Lakshmi's
# concurrence).
#
# Revision 1.1  2003/12/16 16:02:14  bkline
# Main menu for board managers.
#
#  Adding menu item for Comprehensive Review Date Report
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
title   = "CDR Administration"
section = "Board Managers"
buttons = []
header  = cdrcgi.header(title, title, section, "BoardManagers.py", buttons,
                        numBreaks = 1, stylesheet = """\
  <style type='text/css'>
   H2 { font-family: Arial; font-size: 14pt; font-weight: bold }
   LI { font-family: Arial; font-size: 12pt; font-weight: bold }
  </style>
""")

#----------------------------------------------------------------------
# Display available menu choices.
#----------------------------------------------------------------------
session = "%s=%s" % (cdrcgi.SESSION, session)
form = """\
   <H2>General Use Reports</H2>
   <OL>
"""
for choice in (
    ('GeneralReports.py', 'All General Reports'         ),
    ('CheckedOutDocs.py', 'Checked Out Documents Report'),
    ('ActivityReport.py', 'Document Activity Report'    ),
    ('LinkedDocs.py',     'Linked Documents Report'     ),
    ('UnchangedDocs.py',  'Unchanged Documents Report'  )
    ):
    form += """\
    <LI><a href='%s/%s?%s'>%s</a></LI>
""" % (cdrcgi.BASE, choice[0], session, choice[1])

form += """\
   </OL>
   <H2>Summary QC Reports</H2>
   <OL>
"""
for choice in (
    ('bu',  'Bold/Underline (HP/Old Patient)'   ),
    ('rs',  'Redline/Strikeout (HP/Old Patient)'),
    ('pat', 'New Patient'                       ),
    ('pp',  'Publish Preview'                   )
    ):
    form += """\
    <LI><a href='%s/QcReport.py?DocType=Summary&ReportType=%s&%s'>%s</a></LI>
""" % (cdrcgi.BASE, choice[0], session, choice[1])

form += """\
   </OL>
   <H2>Management Reports</H2>
   <OL>
"""

for choice in (
    ('BoardMeetingDates.py',       'Board Meeting Dates'          ),
    ('ChangesToSummaries.py',      'Changes to Summaries'         ),
    ('SummaryChanges.py',          'History of Changes to Summary'),
    ('SummaryCitations.py',        'Summaries Citations'          ),
    ('SummaryComments.py',         'Summaries Comments'           ),
    ('SummaryCRD.py',
                      'Summaries Comprehensive Review Date Report'),
    ('SummaryDateLastModified.py', 'Summaries Date Last Modified' ),
    ('SummariesLists.py',          'Summaries Lists'              ),
    ('SummariesWithMarkup.py',     'Summaries Markup Report'      ),
    ('SummaryMetaData.py',         'Summaries Metadata'           ),
    ('SummariesTocReport.py',      'Summaries TOC Lists'          ),
    ('SummaryTypeChangeReport.py?','Summaries Type Of Change'     ),
    ('SummariesWithProtocolLinks.py',
                      'Summaries with Protocols Links/Refs Report'),
    ('SummariesWithNonJournalArticleCitations.py',
             'Summaries with Non-Journal Article Citations Report')
    ):
    form += """\
    <LI><a href='%s/%s?%s'>%s</a></LI>
""" % (cdrcgi.BASE, choice[0], session, choice[1])

form += """\
   </OL>
   <H2>Board Member Information Reports</H2>
   <OL>
"""

for choice in (
    ('QcReport.py',                'Board Member Information QC Report'  ),
    ('BoardRoster.py',             'Board Roster Reports'                ),
    ('BoardRosterFull.py',         'Board Roster Reports (Combined)'     ),
    ('BoardInvitationHistory.py',  'Invitation History Report'           ),
    ('PdqBoards.py',               'PDQ Board Members and Topics'        )
    ):
    form += """\
    <LI><a href='%s/%s?DocType=PDQBoardMemberInfo&%s'>%s</a></LI>
""" % (cdrcgi.BASE, choice[0], session, choice[1])

cdrcgi.sendPage(header + form + """\
   </OL>
   <H2>Miscellaneous Document QC Report</H2>
   <OL>
    <LI><a href='%s/MiscSearch.py?%s'>Miscellaneous Documents</a></LI>
   </OL>
   <H2>Mailers</H2>
   <OL>
    <LI><a href='%s/BoardMemberMailerReqForm.py?%s'>PDQ&reg; Board
     Member Correspondence Mailers</a></LI>
    <LI><A HREF='%s/SummaryMailerReport.py?flavor=4259&%s'
        >Summary Mailer History Report</A></LI>
    <LI><A HREF='%s/SummaryMailerReport.py?flavor=4258&%s'
        >Summary Mailer Report</A></LI>
   </OL>
  </FORM>
 </BODY>
</HTML>""" % (cdrcgi.BASE, session, cdrcgi.BASE, session,
              cdrcgi.BASE, session, cdrcgi.BASE, session))
