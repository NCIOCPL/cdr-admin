#!/usr/bin/env python

""" Report all citations linked by a summary document.
"""

from functools import cached_property
from cdrcgi import Controller, Reporter, Excel
from cdrbatch import CdrBatch
from CdrLongReports import CitationsInSummaries


class Control(Controller):
    SUBTITLE = "Citations In Summaries"
    COLS = (
        Reporter.Column("Citation ID", width="60px"),
        Reporter.Column("Citation Title", width="1000px"),
        Reporter.Column("PMID", width="70px"),
        Reporter.Column("Summary ID", width="60px"),
        Reporter.Column("Summary Title", width="500px"),
        Reporter.Column("Summary Boards", width="500px"),
    )
    OPTS = dict(columns=COLS, caption=SUBTITLE, sheet_name=SUBTITLE)
    LINK_PATH = "/Summary/%CitationLink/@cdr:ref"
    LOGNAME = "CitationsInSummaries"
    LONG_REPORTS = "lib/Python/CdrLongReports.py"
    OPTIONS = (
        ("quick", "Quick sample report"),
        ("debug", "Log debugging information"),
    )
    TIP = "Run report directly instead of queuing a batch report."
    REPORT_LIMITS = (
        ("max-citations", "Max Citations", 100),
        ("max-seconds", "Max Seconds", 60),
    )
    INSTRUCTIONS = (
        "The full report generally takes about an hour or more to generate. "
        "When the report is ready an email notification will be sent "
        "to the address(es) provided, with a link to the Excel report. "
        "For testing you can choose a quick version of the report, "
        "for which you can specify the maximum number of Citation "
        "documents to be included, and/or the maximum number of seconds "
        "for collecting the information to be included in the report."
    )

    def populate_form(self, page):
        """Find out how the users wants to run this report.

        Required positional argument:
          page - instance of the cdrcgi.HTMLPage class
        """

        # Explain how the report works.
        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)

        # Add the options which are always visible.
        fieldset = page.fieldset("Report Options")
        for value, label in self.OPTIONS:
            opts = dict(value=value, label=label)
            if value == "quick":
                opts["tooltip"] = self.TIP
            fieldset.append(page.checkbox("options", **opts))
        page.form.append(fieldset)

        # Add a block for the required email address(s).
        fieldset = page.fieldset("Email (Required)", id="email-block")
        opts = dict(value=self.email, label="Address(es)")
        opts["tooltip"] = "Separate multiple addresses with a space."
        fieldset.append(page.text_field("email", **opts))
        page.form.append(fieldset)

        # Add a second block for options on the "quick" report.
        fieldset = page.fieldset("Report Limits", id="limit-block")
        fieldset.set("class", "hidden usa-fieldset")
        for name, display, value in self.REPORT_LIMITS:
            opts = dict(label=display, value=value)
            fieldset.append(page.text_field(name, **opts))
        page.form.append(fieldset)
        page.head.append(page.B.SCRIPT(src="/js/CitationsInSummaries.js"))

    def show_report(self):
        """Queue the report or generate it directly."""

        args = []
        if self.debug:
            args.append(("debug", True))
        if self.quick:
            args.append(("max_time", self.max_seconds))
            args.append(("limit", self.max_citations))
            args.append(("throttle", True))
        opts = dict(
            jobName=CitationsInSummaries.NAME,
            command=self.LONG_REPORTS,
            email=self.email,
            args=args,
        )
        job = CdrBatch(**opts)
        if self.quick:
            report = CitationsInSummaries(job)
            report.excel = Excel(wrap=True, stamp=True)
            report.add_sheets()
            self.logger.info("elapsed time for report: %s", self.elapsed)
            report.excel.send()
        else:
            if not self.session.can_do("RUN LONG REPORT"):
                self.bail("Not authorized to run batch reports")
            if not self.email:
                self.bail("Missing required email address.")
            try:
                job.queue()
            except Exception as e:
                self.logger.exception("Failure queuing job")
                self.bail(f"Unable to queue job: {e}")
            self.logger.info("elapsed time for report: %s", self.elapsed)
            job.show_status_page(self.session)

    @cached_property
    def debug(self):
        """True if the debugging option has been checked."""
        return True if "debug" in self.options else False

    @cached_property
    def email(self):
        """Where to send notification if the report is queued."""

        addresses = self.fields.getvalue("email", "").strip()
        return addresses or self.session.user.email

    @cached_property
    def loglevel(self):
        """Bump up logging verbosity if requested."""
        return "DEBUG" if self.debug else "INFO"

    @cached_property
    def max_citations(self):
        """When to stop when testing."""
        return int(self.fields.getvalue("max-citations", "10"))

    @cached_property
    def max_seconds(self):
        """When to stop when testing."""
        return int(self.fields.getvalue("max-seconds", "10"))

    @cached_property
    def options(self):
        """Checkbox options for the report."""
        return self.fields.getlist("options")

    @cached_property
    def quick(self):
        """True if we deliver the report immediately, avoiding the queue."""
        return "quick" in self.options


if __name__ == "__main__":
    """Don't run if loaded as a module."""
    Control().run()
