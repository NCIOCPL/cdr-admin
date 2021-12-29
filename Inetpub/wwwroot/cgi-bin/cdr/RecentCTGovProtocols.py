#!/usr/bin/env python

"""Report on recently imported CT.gov protocols.
"""

import datetime
from cdrcgi import Controller


class Control(Controller):

    SUBTITLE = "Recent CT.gov Protocols"

    def build_tables(self):
        """Assemble the table for the report."""

        opts = dict(columns=self.columns, caption=self.caption)
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """If we don't have the required parameters, ask for them.

        Pass:
            page - HTMLPage on which to place the form fields.
        """

        fieldset = page.fieldset("Date Range for Report")
        end = datetime.date.today()
        start = end - datetime.timedelta(30)
        fieldset.append(page.date_field("start", value=start))
        fieldset.append(page.date_field("end", value=end))
        page.form.append(fieldset)
        page.add_output_options(default="excel")

    @property
    def caption(self):
        """String displayed at the top of the table."""

        if not hasattr(self, "_caption"):
            suffix = ""
            if self.start:
                if self.end:
                    suffix = f" Received Between {self.start} and {self.end}"
                else:
                    suffix = f" Received Since {self.start}"
            elif self.end:
                suffix = f" Received Through {self.end}"
            self._caption = f"CT.gov Protocols{suffix}"
        return self._caption

    @property
    def columns(self):
        """Column headers for the report."""

        return (
            self.Reporter.Column("NCT ID", width="100px"),
            self.Reporter.Column("Received", width="100px"),
            self.Reporter.Column("Trial Title", width="500px"),
            self.Reporter.Column("Phase", width="100px"),
            self.Reporter.Column("Other IDs", width="200px"),
            self.Reporter.Column("Sponsors", width="1000px"),
        )

    @property
    def end(self):
        """End of the report's date range."""
        return self.fields.getvalue("end")

    @property
    def rows(self):
        """Table rows for the report."""

        if not hasattr(self, "_rows"):
            self._rows = [trial.row for trial in self.trials]
        return self._rows

    @property
    def start(self):
        """Beginning of the report's date range."""
        return self.fields.getvalue("start")

    @property
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

            self.__control = control
            self.__row = row

        @property
        def ids(self):
            """Alternate IDs for the trial."""

            query = self.__control.Query("ctgov_trial_other_id", "other_id")
            query.order("position")
            query.where(query.Condition("nct_id", self.nctid))
            rows = query.execute(self.__control.cursor).fetchall()
            return "; ".join([row.other_id for row in rows])

        @property
        def nctid(self):
            """NLM's ID for the trial."""
            return self.__row.nct_id

        @property
        def phase(self):
            """The phase of the trial (e.g., "Phase 3")."""
            return self.__row.trial_phase

        @property
        def received(self):
            """The date the trial was first received."""
            return str(self.__row.first_received)[:10]

        @property
        def row(self):
            """Table row for the report."""

            opts = dict(href=self.url, target="_blank", center=True)
            return (
                self.__control.Reporter.Cell(self.nctid, **opts),
                self.__control.Reporter.Cell(self.received, center=True),
                self.title,
                self.phase,
                self.ids,
                self.sponsors,
            )

        @property
        def sponsors(self):
            """Sponsors for the trial.

            Hard to pin down the definition of 'sponsor' in this context.
            """

            query = self.__control.Query("ctgov_trial_sponsor", "sponsor")
            query.order("position")
            query.where(query.Condition("nct_id", self.nctid))
            rows = query.execute(self.__control.cursor).fetchall()
            return "; ".join([row.sponsor for row in rows])

        @property
        def title(self):
            """The title of the clinical trial."""
            return self.__row.trial_title

        @property
        def url(self):
            """Address of the web page for the trial at NLM."""
            return f"https://clinicaltrials.gov/ct2/show/{self.nctid}"


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
