#!/usr/bin/env python

"""Generate PCIB statistics for updated/added documents.

This report runs on a monthly schedule but can also be submitted from
the CDR Admin reports menu.
"""

from cdrcgi import Controller
import cdr_stats
import datetime


class Control(Controller):

    SUBTITLE = "PCIB Statistics Report"
    LOGNAME = "PCIBStatReport"
    SECTION_LABELS = dict(
        summary="Summaries",
        genetics="Genetics Professionals",
        drug="NCI Drug Terms",
        dis="Drug Information Summaries",
        boardmembers="PDQ Board Members",
        boardmeetings="PDQ Board Meetings",
        image="Images",
        glossary="Glossary (including audio pronunciations)",
    )
    INSTRUCTIONS = (
        "This Report runs on every 1\u02E2\u1d57 of the month for the "
        "previous month. Specify the start date and end date to run the "
        "report for a different time frame.",
        "Click the submit button only once!  The report will take a few "
        "seconds to complete.",
        "Leave the Email field empty to send the report to the default "
        "distribution list."
    )
    INCLUDE_DOCS = "Include individual documents"
    INCLUDE_IDS = "Include column for CDR IDs"
    OPTIONS = INCLUDE_DOCS, INCLUDE_IDS

    def populate_form(self, page):
        """Fill in the fields for requesting the report.

        Pass:
            page - HTMLPage object on which the fields are placed
        """

        fieldset = page.fieldset("Instructions")
        for para in self.INSTRUCTIONS:
            fieldset.append(page.B.P(para))
        page.form.append(fieldset)
        fieldset = page.fieldset("Basic Options")
        opts = dict(label="Start Date", value=self.start)
        fieldset.append(page.date_field("start", **opts))
        opts = dict(label="End Date", value=self.end)
        fieldset.append(page.date_field("end", **opts))
        fieldset.append(page.text_field("email", value=self.user.email))
        fieldset.append(page.text_field("max-docs", label="Max Docs"))
        page.form.append(fieldset)
        fieldset = page.fieldset("Sections")
        for section in cdr_stats.Control.SECTIONS:
            if section != "audio":
                label = self.SECTION_LABELS.get(section, section.capitalize())
                opts = dict(value=section, label=label, checked=True)
                fieldset.append(page.checkbox("sections", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Flags")
        for option in self.OPTIONS:
            opts = dict(value=option, label=option, checked=True)
            fieldset.append(page.checkbox("options", **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Hand off the work of creating the report to another script.

        Tell the user when we're done.
        """

        opts = {
            "mode": "live",
            "recips": self.recips,
            "start": self.start,
            "end": self.end,
            "sections": self.sections,
            "ids": self.INCLUDE_IDS in self.options,
            "docs": self.INCLUDE_DOCS in self.options,
            "max-docs": self.max_docs
        }
        try:
            cdr_stats.Control(opts).run()
        except Exception as e:
            self.logger.exception("Report failure")
            self.bail("failure: %s" % e)
        fieldset = self.HTMLPage.fieldset("Report Status")
        para = self.HTMLPage.B.P("The report has been sent to you by email.")
        para.set("class", "center")
        fieldset.append(para)
        self.report.page.form.append(fieldset)
        self.report.send()

    @property
    def end(self):
        """Optional end to the report date range."""

        end = self.fields.getvalue("end")
        if end:
            try:
                return str(self.parse_date(end))
            except Exception:
                self.bail("Invalid date string")
        return str(datetime.date.today())

    @property
    def max_docs(self):
        """Cap on the number of documents to include."""

        max_docs = self.fields.getvalue("max-docs")
        if max_docs:
            try:
                return int(max_docs)
            except Exception:
                self.bail("Max docs must be an integer")
        return None

    @property
    def no_results(self):
        """Suppress the normal message show when there are no tables."""
        return None

    @property
    def options(self):
        """Report options selected on the form."""
        return self.fields.getlist("options")

    @property
    def recips(self):
        """Email recipients for the report."""

        recips = (self.fields.getvalue("email") or "").strip()
        for punctuation in ",;":
            recips = recips.replace(punctuation, " ")
        recips = recips.split()
        if not recips:
            self.bail("At least one email recipient must be specified")
        return recips

    @property
    def sections(self):
        """Sections to be included in the report."""

        sections = self.fields.getlist("sections")
        if set(sections) - set(cdr_stats.Control.SECTIONS):
            self.bail()
        return sections

    @property
    def start(self):
        """Optional start to the report date range."""

        start = self.fields.getvalue("start")
        if start:
            try:
                return str(self.parse_date(start))
            except Exception:
                self.bail("Invalid date string")
        today = datetime.date.today()
        return datetime.date(today.year, 1, 1)

    @property
    def user(self):
        """The currently logged-in user account."""
        return self.session.User(self.session, id=self.session.user_id)


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
