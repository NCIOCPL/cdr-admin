#----------------------------------------------------------------------
# Submenu for general reports.
#
# BZIssue::255
# BZIssue::1373
# BZIssue::1417
# BZIssue::4126
# JIRA::OCECDR-3800
#----------------------------------------------------------------------
import cdrcgi

class Control(cdrcgi.Control):
    REPORTS = (
        ("CheckedOutDocs.py", "Checked Out Documents"),
        ("CdrReport.py", "Checked Out Documents With No Activity"),
        ("ActiveLogins.py", "Current Sessions"),
        ("db-tables.py", "Database Tables/Columns"),
        ("DateLastModified.py", "Date Last Modified"),
        ("ActivityReport.py", "Document Activity Report"),
        ("DocVersionHistory.py", "Document Version History"),
        ("DocumentsModified.py", "Documents Modified"),
        ("ExternMapFailures.py", "External Map Failures Report"),
        ("/CdrFilter.html", "Filter Document"),
        ("ShowGlobalChangeTestResults.py", "Global Change Test Results"),
        ("InvalidDocs.py", "Invalid Documents"),
        ("LinkedDocs.py", "Linked Documents"),
        ("MediaLinks.py", "Linked Media Documents"),
        ("NewDocsWithPubStatus.py",
         "List of New Documents with Publication Status"),
        ("NewDocReport.py", "New Document Count"),
        ("ModWithoutPubVersion.py",
         "Records Modified Since Last Publishable Version"),
        ("ShowCdrDocument.py", "Show CDR Document XML"),
        ("ShowSummaryIncludes.py", "Show Summary Elements"),
        ("UnchangedDocs.py", "Unchanged Documents"),
        ("CheckUrls.py", "URL Check"),
        ("UrlListReport.py", "URL List Report"),
        ("ReplaceCWDReport.py", "Versions that Replaced CWDs"),
        ("xmetal-icons.py", "XMetaL CDR Icons"),
    )
    def __init__(self):
        cdrcgi.Control.__init__(self, "General Reports")
    def set_form_options(self, opts):
        opts["body_classes"] = "admin-menu"
        return opts
    def populate_form(self, form):
        form.add("<ol>")
        for script, display in self.REPORTS:
            form.add_menu_link(script, display, self.session)
        form.add("</ol>")
Control().run()
