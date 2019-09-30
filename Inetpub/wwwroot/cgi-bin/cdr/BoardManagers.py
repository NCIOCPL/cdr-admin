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

        # Section 1: general.
        page.body.set("class", "admin-menu")
        page.form.append(page.B.H3("General Use Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script in (
            ("All General Reports", "GeneralReports.py"),
            ("Checked Out Documents Report", "CheckedOutDocs.py"),
            ("Document Activity Report", "ActivityReport.py"),
            ("Linked Documents Report", "LinkedDocs.py"),
            ("Unchanged Documents Report", "UnchangedDocs.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))

        # Section 2: QC.
        page.form.append(page.B.H3("Summary QC Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        opts = dict(DocType="Summary")
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

        # Section 3: management.
        page.form.append(page.B.H3("Management Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script in (
            ("Board Meeting Dates", "BoardMeetingDates.py"),
            ("Changes to Summaries", "ChangesToSummaries.py"),
            ("History of Changes to Summary", "SummaryChanges.py"),
            ("PCIB Statistics Report", "RunPCIBStatReport.py"),
            ("Summaries Citations", "SummaryCitations.py"),
            ("Summaries Comments", "SummaryComments.py"),
            ("Summaries Comprehensive Review Date Report", "SummaryCRD.py"),
            ("Summaries Date Last Modified", "SummaryDateLastModified.py"),
            ("Summaries Lists", "SummariesLists.py"),
            ("Summaries Markup Report", "SummariesWithMarkup.py"),
            ("Summaries Metadata", "SummaryMetaData.py"),
            ("Summaries TOC Lists", "SummariesTocReport.py"),
            ("Summaries Type Of Change", "SummaryTypeChangeReport.py"),
            ("Summaries With Non-Journal Article Citations Report",
             "SummariesWithNonJournalArticleCitations.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))

        # Section 4: board members.
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
            ("PDQ Board Members and Topics", "PdqBoards.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))

        # Section 5: miscellaneous docs.
        page.form.append(page.B.H3("Miscellaneous Document QC Report"))
        ol = page.B.OL()
        page.form.append(ol)
        link = page.menu_link("MiscSearch.py", "Miscellaneous Documents")
        ol.append(page.B.LI(link))

        # Section 6: mailers.
        page.form.append(page.B.H3("Mailers"))
        links = (
            page.menu_link(
                "BoardMemberMailerReqForm.py",
                "PDQ\xAE Board Member Correspondence Mailers"
            ),
            page.menu_link(
                "SummaryMailerReport.py",
                "Summary Mailer History Report",
                flavor="4259"
            ),
            page.menu_link(
                "SummaryMailerReport.py",
                "Summary Mailer Report",
                flavor="4258"
            ),
        )
        items = [page.B.LI(link) for link in links]
        ol = page.B.OL(*items)
        page.form.append(ol)


Control().run()
