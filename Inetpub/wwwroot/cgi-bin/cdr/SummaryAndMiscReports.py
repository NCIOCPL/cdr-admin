#!/usr/bin/env python

"""Summary and Miscellaneous Document report menu.
"""

from cdrcgi import Controller


class Control(Controller):

    SUBTITLE = "Summary and Miscellaneous Document Reports"
    SUBMIT = None

    def populate_form(self, page):
        page.body.set("class", "admin-menu")

        # Part 1: Board member information.
        page.form.append(page.B.H3("Board Member Information Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script, parms in (
            ("Board Member Information QC Report", "QcReport.py",
             dict(DocType="PDQBoardMemberInfo")),
            ("Board Roster Reports", "BoardRoster.py", {}),
        ):
            ol.append(page.B.LI(page.menu_link(script, display, **parms)))

        # Part 2: Management QC.
        page.form.append(page.B.H3("Management QC Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script in (
            ("Changes to Summaries", "ChangesToSummaries.py"),
            ("History of Changes to Summary", "SummaryChanges.py"),
            ("PDQ Board Listings", "PdqBoards.py"),
            ("Standard Wording", "SummaryStandardWording.py"),
            ("Summaries Citations", "SummaryCitations.py"),
            ("Summaries Cleanup", "SummarySectionCleanup.py"),
            ("Summaries Date Last Modified", "SummaryDateLastModified.py"),
            ("Summaries Lists", "SummariesLists.py"),
            ("Summaries Metadata", "SummaryMetaData.py"),
            ("Summaries TOC Lists", "SummariesTocReport.py"),
            ("Summaries Type Of Change", "SummaryTypeChangeReport.py"),
            ("Summaries With Non-Journal Article Citations Report",
             "SummariesWithNonJournalArticleCitations.py"),
            ("Summaries with ProtocolRef Links (> 5min)",
             "SummaryProtocolRefLinks.py"),
            ("Summary Internal Links", "ocecdr-3650.py"),
            ("Updated SummaryRef Titles", "UpdatedSummaryRefTitles.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))

        # Part 3: Related QC.
        page.form.append(page.B.H3("Related QC Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script, parms in (
            ("Miscellaneous Documents", "MiscSearch.py", {}),
            ("Summary Mailer History Report", "SummaryMailerReport.py",
             dict(flavor="historical")),
            ("Summary Mailer Report", "SummaryMailerReport.py",
             dict(flavor="standard")),
        ):
            ol.append(page.B.LI(page.menu_link(script, display, **parms)))

        # Part 4: Summary QC.
        page.form.append(page.B.H3("Summary QC Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        script = "QcReport.py"
        parms = dict(DocType="Summary", DocVersion="0")
        for display, report_type in (
            ("HP Bold/Underline QC Report", "bu"),
            ("HP Redline/Strikeout QC Report", "rs"),
            ("PT Bold/Underline QC Report", "patbu"),
            ("PT Redline/Strikeout QC Report", "pat"),
            ("Publish Preview Report", "pp"),
        ):
            parms["ReportType"] = report_type
            ol.append(page.B.LI(page.menu_link(script, display, **parms)))

        # Part 5: Translation jobs.
        page.form.append(page.B.H3("Translation Job Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script in (
            ("Translation Job Workflow Report", "translation-job-report.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))


Control().run()
