#!/usr/bin/env python

"""Report on audio files with a specified review disposition.
"""

from cdrcgi import Controller, Reporter


class Control(Controller):
    """Script logic."""

    SUBTITLE = "Glossary Term Audio Review Statistical Report"
    INSTRUCTIONS = (
        "Select a language and approval status for the term names "
        "to include in the report.  Optionally add start and/or "
        "end dates for the term reviews to limit the size of the output."
    )
    LANGUAGES = "English", "Spanish"
    STATUSES = "Approved", "Rejected", "Unreviewed"
    REPORT_TYPES = (
        "Full report showing terms",
        "Summary report with status totals only",
    )

    def build_tables(self):
        """Create the full or summary report, as requested by the user."""

        self.subtitle = f"{self.status} {self.language} Audio Pronunciations"
        tables = [self.summary_table]
        if self.type == "full":
            tables += [audio_set.table for audio_set in self.sets]
        return tables

    def populate_form(self, page):
        """Add the fields to the form.

        Pass:
            page - HTMLPage object to which we add the fields
        """

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)
        fieldset = page.fieldset("Select Language")
        checked = True
        for language in self.LANGUAGES:
            opts = dict(value=language, checked=checked)
            fieldset.append(page.radio_button("language", **opts))
            checked = False
        page.form.append(fieldset)
        fieldset = page.fieldset("Select Status")
        checked = True
        for status in self.STATUSES:
            opts = dict(value=status, checked=checked)
            fieldset.append(page.radio_button("status", **opts))
            checked = False
        page.form.append(fieldset)
        fieldset = page.fieldset("Select Full or Summary Report")
        checked = True
        for display in self.REPORT_TYPES:
            value = display.split()[0].lower()
            opts = dict(value=value, label=display, checked=checked)
            fieldset.append(page.radio_button("type", **opts))
            checked = False
        page.form.append(fieldset)
        fieldset = page.fieldset("Optional Start and End Dates")
        fieldset.append(page.date_field("start_date"))
        fieldset.append(page.date_field("end_date"))
        page.form.append(fieldset)

    def show_report(self):
        """Override the base class version in order to add style rules."""

        css = (
            "table { width: 500px; margin-top: 50px; }",
            "table.set { width: 75%; }",
            ".center {width: 150px; }",
            ".set td:last-child { width: 200px; }",
        )
        self.report.page.add_css("\n".join(css))
        self.report.send()

    @property
    def end(self):
        """Optional end to report's date range."""
        return self.parse_date(self.fields.getvalue("end_date"))

    @property
    def language(self):
        """Language value selected from the form by the user."""
        return self.fields.getvalue("language")

    @property
    def sets(self):
        """Audio pronunciation sets in scope for this report."""

        if not hasattr(self, "_sets"):
            fields = "z.id", "z.filename"
            query = self.Query("term_audio_zipfile z", *fields).unique()
            query.join("term_audio_mp3 m", "m.zipfile_id = z.id")
            query.where(query.Condition("m.language", self.language))
            query.where(query.Condition("m.review_status", self.status[0]))
            if self.start:
                query.where(query.Condition("m.review_date", self.start, ">="))
            if self.end:
                end = f"{str(self.end)[:10]} 23:59:59"
                query.where(query.Condition("m.review_date", end, "<="))
            rows = query.order("z.id").execute(self.cursor).fetchall()
            self._sets = [AudioSet(self, row) for row in rows]
        return self._sets

    @property
    def start(self):
        """Optional start to report's date range."""
        return self.parse_date(self.fields.getvalue("start_date"))

    @property
    def status(self):
        """Status value selected from the form by the user."""
        return self.fields.getvalue("status")

    @property
    def subtitle(self):
        """String displayed immediately under the page's main banner."""

        if not hasattr(self, "_subtitle"):
            self._subtitle = self.SUBTITLE
        return self._subtitle

    @subtitle.setter
    def subtitle(self, value):
        """Make this modifiable on the fly."""
        self._subtitle = value

    @property
    def summary_table(self):
        """Table showing the totals for each status."""

        if not hasattr(self, "_summary_table"):
            approved = rejected = unreviewed = 0
            for audio_set in self.sets:
                approved += audio_set.approved
                rejected += audio_set.rejected
                unreviewed += audio_set.unreviewed
            row = approved, rejected, unreviewed
            opts = dict(columns=self.STATUSES, caption="Status Totals")
            self._summary_table = Reporter.Table([row], **opts)
        return self._summary_table

    @property
    def type(self):
        """Report type selected by the user (full or summary)."""
        return self.fields.getvalue("type")


class AudioSet:
    """Zip file containing glossary term audio pronunciation recordings."""

    FIELDS = "m.term_name", "m.review_date", "u.fullname"
    COLUMNS = "Term", "Review Date", "User"

    def __init__(self, control, row):
        """Capture the caller's values.

        Pass:
            control - access to the database and the runtime report parameters
            row - id and name for this set
        """

        self.__control = control
        self.__row = row

    @property
    def audio_files(self):
        """Audio recordings in this set which are in scope for the report."""

        if not hasattr(self, "_audio_files"):
            class MP3:
                def __init__(self, row):
                    self.name = row.term_name
                    self.user = row.fullname
                    self.date = row.review_date

                @property
                def row(self):
                    return (
                        self.name,
                        str(self.date)[:19],
                        self.user,
                    )
            status = self.control.status[0]
            query = self.control.Query("term_audio_mp3 m", *self.FIELDS)
            query.join("usr u", "u.id = m.reviewer_id")
            query.where(query.Condition("m.zipfile_id", self.id))
            query.where(query.Condition("m.language", self.control.language))
            query.where(query.Condition("m.review_status", status))
            if self.control.start:
                start = self.control.start
                query.where(query.Condition("m.review_date", start, ">="))
            if self.control.end:
                end = f"{str(self.control.end)[:10]} 23:59:59"
                query.where(query.Condition("m.review_date", end, "<="))
            query.order("m.term_name")
            rows = query.execute(self.control.cursor).fetchall()
            self._audio_files = [MP3(row) for row in rows]
        return self._audio_files

    @property
    def control(self):
        """Access to the database and the options selected by the user."""
        return self.__control

    @property
    def counts(self):
        """Totals for each status in this set."""

        if not hasattr(self, "_counts"):
            fields = "review_status", "COUNT(*)"
            query = self.control.Query("term_audio_mp3", *fields)
            query.where(query.Condition("zipfile_id", self.id))
            query.where(query.Condition("language", self.control.language))
            query.group("review_status")
            rows = query.execute(self.control.cursor).fetchall()
            self._counts = dict([tuple(row) for row in rows])
        return self._counts

    @property
    def id(self):
        """Primary key for this set in its database row."""
        return self.__row.id

    @property
    def name(self):
        """File name for this set."""
        return self.__row.filename

    @property
    def subtotals(self):
        """Row in the report table for this set's subtotals."""

        if not hasattr(self, "_subtotals"):
            subtotals = []
            for status in Control.STATUSES:
                subtotals.append(f"{status}={self.counts.get(status[0], 0)}")
            subtotals = "\xa0 ".join(subtotals)
            language = self.control.language
            subtotals = f"{language} names in this set:\xa0 {subtotals}"
            cell = Reporter.Cell(subtotals, center=True, colspan=3)
            self._subtotals = [cell]
        return self._subtotals

    @property
    def table(self):
        """Report table for this set."""

        if not hasattr(self, "_table"):
            rows = [mp3.row for mp3 in self.audio_files]
            rows.append(self.subtotals)
            opts = dict(cols=self.COLUMNS, caption=self.name, classes="set")
            self._table = Reporter.Table(rows, **opts)
        return self._table

    @property
    def approved(self):
        """Number of approved recordings for the selected language."""
        return self.counts.get("A", 0)

    @property
    def rejected(self):
        """Number of rejected recordings for the selected language."""
        return self.counts.get("R", 0)

    @property
    def unreviewed(self):
        """Number of unreviewed recordings for the selected language."""
        return self.counts.get("U", 0)


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
