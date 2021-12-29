#!/usr/bin/env python

"""Main menu for board managers.
"""

from cdrapi.users import Session
from cdrcgi import Controller, bail


class Control(Controller):

    SUBTITLE = "Board Managers"
    GROUP = "Board Manager Menu Users"
    SUBMIT = None

    def populate_form(self, page):

        # Make sure the user is allowed to use this menu.
        user = Session.User(self.session, id=self.session.user_id)
        if self.GROUP not in user.groups:
            bail("User not authorized for this menu")

        # Section 1: summary and module reports.
        page.form.append(page.B.H3("Summary and Module Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script in (
            ("Most Recent Changes to Summaries", "ChangesToSummaries.py"),
            ("History of Changes to a Single Summary", "SummaryChanges.py"),
            ("Date Last Modified", "SummaryDateLastModified.py"),
            ("Comprehensive Review Dates", "SummaryCRD.py"),
            ("Titles in Alphabetical Order", "SummariesLists.py"),
            ("Metadata", "SummaryMetaData.py"),
            ("TOC Levels", "SummariesTocReport.py"),
            ("Type of Comments", "SummaryComments.py"),
            ("Current Markup", "SummariesWithMarkup.py"),
            ("Type Of Change", "SummaryTypeChangeReport.py"),
            ("Standard Wording", "SummaryStandardWording.py"),
            ("Citations in Alphabetical Order", "SummaryCitations.py"),
            ("Non-Journal Article Citations Report",
             "SummariesWithNonJournalArticleCitations.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))

        # Section 2: management reports.
        page.form.append(page.B.H3("PCIB Management Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script in (
            ("Board Meeting Dates", "BoardMeetingDates.py"),
            ("PCIB Statistics Report", "RunPCIBStatReport.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))

        # Section 3: other reports.
        page.body.set("class", "admin-menu")
        name = "Quick Links to Other Reports and Report Menus"
        page.form.append(page.B.H3(name))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script in (
            ("Checked Out Documents", "CheckedOutDocs.py"),
            ("Drug Information", "DrugInfoReports.py"),
            ("Glossary Terms", "GlossaryTermReports.py"),
            ("Linked Documents", "LinkedDocs.py"),
            ("Media", "MediaReports.py"),
            ("General Use Reports", "GeneralReports.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))

        # Section 4: board members.
        page.body.set("class", "admin-menu")
        page.form.append(page.B.H3("Board Member Information Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        opts = dict(DocType="PDQBoardMemberInfo")
        display = "Board Member Information QC Report"
        link = page.menu_link("QcReport.py", display, **opts)
        ol.append(page.B.LI(link))
        for display, script in (
            ("Board Roster Reports", "BoardRoster.py"),
            ("Board Roster Reports (Combined)", "BoardRosterFull.py"),
            ("Invitation History Report", "BoardInvitationHistory.py"),
            ("Board Members and Topics", "PdqBoards.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))

        # Section 5: mailers.
        page.form.append(page.B.H3("Mailers"))
        links = (
            page.menu_link(
                "BoardMemberMailerReqForm.py",
                "Board Member Correspondence Mailers"
            ),
            page.menu_link(
                "SummaryMailerReport.py",
                "Summary Mailer History Report",
                flavor="history"
            ),
            page.menu_link(
                "SummaryMailerReport.py",
                "Summary Mailer Report",
                flavor="standard"
            ),
        )
        items = [page.B.LI(link) for link in links]
        ol = page.B.OL(*items)
        page.form.append(ol)

        # Section 6: miscellaneous docs.
        page.form.append(page.B.H3("Miscellaneous Document QC Report"))
        ol = page.B.OL()
        page.form.append(ol)
        link = page.menu_link("MiscSearch.py", "Miscellaneous Documents")
        ol.append(page.B.LI(link))

        # Section 7: QC.
        page.form.append(page.B.H3("Summary QC Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        opts = dict(DocType="Summary", DocVersion="-1")
        for display, report_key in (
            ("HP Bold/Underline QC Report", "bu"),
            ("HP Redline/Strikeout QC Report", "rs"),
            ("PT Bold/Underline QC Report", "patbu"),
            ("PT Redline/Strikeout QC Report", "pat"),
            ("Publish Preview Report", "pp")
        ):
            opts["ReportType"] = report_key
            link = page.menu_link("QcReport.py", display, **opts)
            ol.append(page.B.LI(link))


Control().run()
