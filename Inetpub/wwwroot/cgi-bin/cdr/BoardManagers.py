#----------------------------------------------------------------------
#
# Main menu for board managers.
#
# BZIssue::1059 - Replaced stub with link to Board Member QC report
# BZIssue::1231 - Added Summaries TOC report
# BZIssue::1329 - Rationalize item naming with the CIAT menu
# BZIssue::1531 - Added Publish Preview
# BZIssue::1853 - Modified on item label and moved another item
# BZIssue::3666 - Added menu item
# BZIssue::3672 - Added menu item
# BZIssue::4205 - Add Board Meeting Dates
# BZIssue::4243 - Add Changes to Summaries
# BZIssue::4648
# BZIssue::4671 - Summaries with Markup Report
# BZIssue::4673 - Adding Board Roster (Full) option
#
#  Adding menu item for Comprehensive Review Date Report
#
# Switched to Page class as part of security sweep summer 2015.
#
#----------------------------------------------------------------------
import cdr
import cdrcgi
import cgi

class Control:
    TITLE = "CDR Administration"
    SECTION = "Board Managers"
    def __init__(self):
        fields  = cgi.FieldStorage()
        self.session = cdrcgi.getSession(fields)
        if not self.in_group("Board Manager Menu Users"):
            cdrcgi.bail("User not authorized for this menu")
    def in_group(self, group):
        try:
            name = cdr.idSessionUser(self.session, self.session)[0]
            user = cdr.getUser(self.session, name)
            return group in user.groups
        except:
            return False
    def show_menu(self):
        opts = { "subtitle": self.SECTION, "body_classes": "admin-menu" }
        page = cdrcgi.Page(self.TITLE, **opts)
        page.add(page.B.H3("General Use Reports"))
        page.add("<ol>")
        for script, display in (
            ("GeneralReports.py", "All General Reports"),
            ("CheckedOutDocs.py", "Checked Out Documents Report"),
            ("ActivityReport.py", "Document Activity Report"),
            ("LinkedDocs.py", "Linked Documents Report"),
            ("UnchangedDocs.py", "Unchanged Documents Report")
        ):
            page.add_menu_link(script, display, self.session)
        page.add("</ol>")
        opts = { "DocType": "Summary", "session": self.session }
        page.add(page.B.H3("Summary QC Reports"))
        page.add("<ol>")
        for report_key, display in (
            ("bu", "Bold/Underline (HP/Old Patient)"),
            ("rs", "Redline/Strikeout (HP/Old Patient)"),
            ("pat","New Patient"),
            ("pp", "Publish Preview")
        ):
            opts["ReportType"] = report_key
            page.add_menu_link("QcReport.py", display, **opts)
        page.add("</ol>")
        page.add(page.B.H3("Management Reports"))
        page.add("<ol>")
        for script, display in (
            ("BoardMeetingDates.py", "Board Meeting Dates"),
            ("ChangesToSummaries.py", "Changes to Summaries"),
            ("SummaryChanges.py", "History of Changes to Summary"),
            ("RunPCIBStatReport.py", "PCIB Statistics Report"),
            ("SummaryCitations.py", "Summaries Citations"),
            ("SummaryComments.py", "Summaries Comments"),
            ("SummaryCRD.py", "Summaries Comprehensive Review Date Report"),
            ("SummaryDateLastModified.py", "Summaries Date Last Modified"),
            ("SummariesLists.py", "Summaries Lists"),
            ("SummariesWithMarkup.py", "Summaries Markup Report"),
            ("SummaryMetaData.py", "Summaries Metadata"),
            ("SummariesTocReport.py", "Summaries TOC Lists"),
            ("SummaryTypeChangeReport.py", "Summaries Type Of Change"),
            ("SummariesWithProtocolLinks.py",
             "Summaries with Protocols Links/Refs Report"),
            ("SummariesWithNonJournalArticleCitations.py",
             "Summaries with Non-Journal Article Citations Report")
        ):
            page.add_menu_link(script, display, self.session)
        page.add("</ol>")
        page.add(page.B.H3("Board Member Information Reports"))
        page.add("<ol>")
        for script, display in (
            ("QcReport.py", "Board Member Information QC Report"),
            ("BoardRoster.py", "Board Roster Reports"),
            ("BoardRosterFull.py", "Board Roster Reports (Combined)"),
            ("BoardInvitationHistory.py", "Invitation History Report"),
            ("PdqBoards.py", "PDQ Board Members and Topics")
        ):
            page.add_menu_link(script, display, self.session)
        page.add("</ol>")
        page.add(page.B.H3("Miscellaneous Document QC Report"))
        page.add("<ol>")
        page.add_menu_link("MiscSearch.py", "Miscellaneous Documents",
                           self.session)
        page.add("</ol>")
        page.add(page.B.H3("Mailers"))
        page.add("<ol>")
        page.add_menu_link("BoardMemberMailerReqForm.py",
                           u"PDQ\xAE Board Member Correspondence Mailers",
                           self.session)
        page.add_menu_link("SummaryMailerReport.py",
                           "Summary Mailer History Report", self.session,
                           flavor="4259")
        page.add_menu_link("SummaryMailerReport.py",
                           "Summary Mailer Report", self.session,
                           flavor="4258")
        page.add("</ol>")
        page.send()
Control().show_menu()
