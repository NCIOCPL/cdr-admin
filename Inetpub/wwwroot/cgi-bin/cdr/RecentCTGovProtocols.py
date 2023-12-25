#!/usr/bin/env python

"""Report on recently imported CT.gov protocols.
"""

from datetime import date, timedelta
from functools import cached_property
from cdrcgi import Controller, BasicWebPage


class Control(Controller):

    SUBTITLE = "Recent CT.gov Protocols"

    def build_tables(self):
        """Callback to get the report's tables."""
        return [self.table]

    def populate_form(self, page):
        """If we don't have the required parameters, ask for them.

        Pass:
            page - HTMLPage on which to place the form fields.
        """

        fieldset = page.fieldset("Date Range for Report")
        end = date.today()
        start = end - timedelta(30)
        fieldset.append(page.date_field("start", value=start))
        fieldset.append(page.date_field("end", value=end))
        page.form.append(fieldset)
        page.add_output_options(default="excel")

    def show_report(self):
        """Overridden because the table is too wide for the standard layout."""

        if self.format == "excel":
            Controller.show_report(self)
        else:
            report = BasicWebPage()
            report.wrapper.append(report.B.H1(self.subtitle))
            report.wrapper.append(self.table.node)
            report.wrapper.append(self.footer)
            report.send()

    @cached_property
    def caption(self):
        """String displayed at the top of the table."""

        suffix = ""
        if self.start:
            if self.end:
                suffix = f" Received Between {self.start} and {self.end}"
            else:
                suffix = f" Received Since {self.start}"
        elif self.end:
            suffix = f" Received Through {self.end}"
        return f"CT.gov Protocols{suffix}"

    @cached_property
    def columns(self):
        """Column headers for the report."""

        if self.format == "html":
            return (
                "NCI ID",
                "Received",
                "Trial Title",
                "Phase",
                "Other IDs",
                "Sponsors",
            )
        return (
            self.Reporter.Column("NCT ID", width="100px"),
            self.Reporter.Column("Received", width="100px"),
            self.Reporter.Column("Trial Title", width="500px"),
            self.Reporter.Column("Phase", width="100px"),
            self.Reporter.Column("Other IDs", width="200px"),
            self.Reporter.Column("Sponsors", width="1000px"),
        )

    @cached_property
    def end(self):
        """End of the report's date range."""
        return self.parse_date(self.fields.getvalue("end"))

    @cached_property
    def rows(self):
        """Table rows for the report."""
        return [trial.row for trial in self.trials]

    @cached_property
    def start(self):
        """Beginning of the report's date range."""
        return self.parse_date(self.fields.getvalue("start"))

    @cached_property
    def table(self):
        """Assemble the table for the report."""

        opts = dict(columns=self.columns, caption=self.caption)
        return self.Reporter.Table(self.rows, **opts)

    @cached_property
    def trials(self):
        """Clinical trials to be included in the report."""

        fields = "nct_id", "first_received", "trial_title", "trial_phase"
        query = self.Query("ctgov_trial", *fields).order("nct_id")
        if self.start:
            query.where(query.Condition("first_received", self.start, ">="))
        if self.end:
            end = f"{self.end} 23:59:59"
            query.where(query.Condition("first_received", end, "<="))
        rows = query.execute(self.cursor).fetchall()
        return [self.Trial(self, row) for row in rows]

    class Trial:
        """Recent clinical trial to be included in the report."""

        def __init__(self, control, row):
            """Capture the caller's values.

            Pass:
                control - access to the database and HTML page building
                row - column values from the ctgov_trial table
            """

            self.control = control
            self.db_row = row

        @cached_property
        def ids(self):
            """Alternate IDs for the trial."""

            query = self.control.Query("ctgov_trial_other_id", "other_id")
            query.order("position")
            query.where(query.Condition("nct_id", self.nctid))
            rows = query.execute(self.control.cursor).fetchall()
            return "; ".join([row.other_id for row in rows])

        @cached_property
        def nctid(self):
            """NLM's ID for the trial."""
            return self.db_row.nct_id

        @cached_property
        def phase(self):
            """The phase of the trial (e.g., "Phase 3")."""
            return self.db_row.trial_phase

        @cached_property
        def received(self):
            """The date the trial was first received."""

            received = str(self.db_row.first_received)[:10]
            return received.replace("-", Control.NONBREAKING_HYPHEN)

        @cached_property
        def row(self):
            """Table row for the report."""

            opts = dict(href=self.url, target="_blank", center=True)
            return (
                self.control.Reporter.Cell(self.nctid, **opts),
                self.control.Reporter.Cell(self.received, center=True),
                self.title,
                self.phase,
                self.ids,
                self.sponsors,
            )

        @cached_property
        def sponsors(self):
            """Sponsors for the trial.

            Hard to pin down the definition of 'sponsor' in this context.
            """

            query = self.control.Query("ctgov_trial_sponsor", "sponsor")
            query.order("position")
            query.where(query.Condition("nct_id", self.nctid))
            rows = query.execute(self.control.cursor).fetchall()
            return "; ".join([row.sponsor for row in rows])

        @cached_property
        def title(self):
            """The title of the clinical trial."""
            return self.db_row.trial_title

        @cached_property
        def url(self):
            """Address of the web page for the trial at NLM."""
            return f"https://clinicaltrials.gov/study/{self.nctid}"


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
