#----------------------------------------------------------------------
# Submenu for summary and miscellanous document reports.
#
# BZIssue::545      - menu reorganization
# BZIssue::1059     - plugged in additions requested by Margaret
# BZIssue::1231     - added SummariesTocReport; fixed CSS list & header rules
# BZIssue::1329     - match entries between CIAT and CIPS summary menus
# BZIssue::1531     - added Publish Preview menu option
# BZIssue::1537     - replaced the Stub.py to run the BoardRoster report
# BZIssue::3666     - added Summaries with Non-Journal Article Citations report
# JIRA::OCECDR-3650 - added Summary Internal Links report
# Removed unused parameter July 2015 as part of security sweep (and
# modified the script to use the cdrcgi.Page class in the process).
# JIRA::OCECDR-4360 - Admin menu changes
#----------------------------------------------------------------------
import cdr
import cdrcgi
import cgi

class Control:
    TITLE = "CDR Administration"
    SUBMENU = "Reports Menu"
    def __init__(self):
        fields = cgi.FieldStorage()
        self.session = cdrcgi.getSession(fields)
        self.request = cdrcgi.getRequest(fields)
        self.buttons = (Control.SUBMENU, cdrcgi.MAINMENU, "Log Out")
        cdrcgi.valParmVal(self.request, val_list=self.buttons, empty_ok=True,
                          msg="CGI form field tampering detected")
    def run(self):
        if self.request == cdrcgi.MAINMENU:
            cdrcgi.navigateTo("Admin.py", self.session)
        elif self.request == Control.SUBMENU:
            cdrcgi.navigateTo("Reports.py", self.session)
        elif self.request == "Log Out":
            cdrcgi.logout(self.session)
        else:
            self.show_menu()
    def show_menu(self):
        opts = {
            "body_classes": "admin-menu",
            "action": "SummaryAndMiscReports.py",
            "subtitle": "Summary and Miscellaneous Document Reports",
            "buttons": self.buttons,
            "session": self.session
        }
        page = cdrcgi.Page(self.TITLE, **opts)
        page.add(page.B.H2("QC Reports"))
        page.add(page.B.H3("Summary QC Reports"))
        page.add("<ol>")
        args = {
            "DocType": "Summary",
            cdrcgi.SESSION: self.session
        }
        for report_type, label in (
            ("bu", "Bold/Underline (HP)"),
            ("rs", "Redline/Strikeout (HP)"),
            ("patbu","Bold/Underline (Patient)"),
            ("pat","Redline/Strikeout (Patient)"),
            ("pp", "Publish Preview")
        ):
            args["ReportType"] = report_type
            page.add_menu_link("QcReport.py", label, **args)
        page.add("</ol>")
        page.add(page.B.H3("Management QC Reports"))
        page.add("<ol>")
        for script, display in (
            ("ChangesToSummaries.py", "Changes to Summaries"),
            ("SummaryChanges.py", "History of Changes to Summary"),
            ("PdqBoards.py", "PDQ Board Listings"),
            ("SummarySectionCleanup.py", "Summaries Cleanup"),
            ("SummaryCitations.py", "Summaries Citations"),
            ("SummaryDateLastModified.py", "Summaries Date Last Modified"),
            ("SummariesLists.py", "Summaries Lists"),
            ("SummaryMetaData.py", "Summaries Metadata"),
            ("SummariesTocReport.py", "Summaries TOC Lists"),
            ("SummaryTypeChangeReport.py", "Summaries Type Of Change"),
            ("SummariesWithNonJournalArticleCitations.py",
             "Summaries with Non-Journal Article Citations Report"),
            ("ocecdr-3650.py", "Summary Internal Links")
        ):
            page.add_menu_link(script, display, self.session)
        page.add("</ol>")
        page.add(page.B.H3("Board Member Information Reports"))
        page.add("<ol>")
        page.add_menu_link("QcReport.py", "Board Member Information QC Report",
                           self.session, DocType="PDQBoardMemberInfo")
        page.add_menu_link("BoardRoster.py", "Board Roster Reports",
                           self.session)
        page.add("</ol>")
        page.add(page.B.H3("Management QC Reports"))
        page.add("<ol>")
        page.add_menu_link("MiscSearch.py", "Miscellaneous Documents",
                           self.session)
        page.add_menu_link("SummaryMailerReport.py",
                           "Summary Mailer History Report", self.session,
                           flavor="4259")
        page.add_menu_link("SummaryMailerReport.py",
                           "Summary Mailer Report", self.session,
                           flavor="4258")
        page.add("</ol>")
        page.add(page.B.H3("Translation Job Reports"))
        page.add("<ol>")
        page.add_menu_link("translation-job-report.py",
                           "Translation Job Workflow Report",
                           self.session)
        page.add("</ol>")
        page.send()
Control().run()
