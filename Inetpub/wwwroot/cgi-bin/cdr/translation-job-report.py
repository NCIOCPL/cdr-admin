#!/usr/bin/env python

"""Generate parameterized reports on the CDR summary translation job queue.

https://tracker.nci.nih.gov/browse/OCECDR-4193
"""

from collections import defaultdict
from datetime import date, timedelta
from functools import cached_property
from cdrcgi import Controller


class Control(Controller):
    """Access to the database and report-building tools."""

    SUBTITLE = "Translation Job Workflow Report"
    FIELDS = (
        "d.id AS english_id",
        "d.title",
        "s.value_name AS state_value",
        "c.value_name AS change_value",
        "u.fullname",
        "j.state_date",
        "j.comments",
    )
    SORT = (
        ("s.value_pos", "Processing Status", True),
        ("j.state_date", "Status Date", False),
        ("u.fullname", "User", False),
        ("c.value_name", "Type of Change", False),
        ("d.title", "English Summary Title", False),
    )
    SORT_VALS = [s[0] for s in SORT]
    GLOSSARY = "Glossary"
    MEDIA = "Media"
    TYPES = (
        ("current", "Current Jobs", True),
        ("history", "Job History", False),
    )
    TABLES = dict(
        current="summary_translation_job j",
        history="summary_translation_job_history j",
    )
    COMMENTS = (
        ("short", "Shortened", True),
        ("full", "Full", False),
    )

    def build_tables(self):
        """Assemble the report's table."""
        return self.Reporter.Table(self.rows, columns=self.columns)

    def populate_form(self, page):
        """Put the fields on the form page.

        Pass:
            page - HTMLPage object on which we place the field sets
        """

        fieldset = page.fieldset("Date Range")
        fieldset.append(page.date_field("start", value=self.start))
        fieldset.append(page.date_field("end", value=self.end))
        page.form.append(fieldset)
        fieldset = page.fieldset("Report Type")
        for value, label, checked in self.TYPES:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("type", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Comment Display")
        for value, label, checked in self.COMMENTS:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("comments", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Statuses (all if none checked)")
        for value, label in self.states.values:
            fieldset.append(page.checkbox("state", label=label, value=value))
        page.form.append(fieldset)
        fieldset = page.fieldset("Types of Change (all if none checked)")
        for value, label in self.changes.values:
            fieldset.append(page.checkbox("change", label=label, value=value))
        page.form.append(fieldset)
        fieldset = page.fieldset("Users (all if none checked)")
        for value, label in self.translators.items:
            opts = dict(label=label, value=value)
            fieldset.append(page.checkbox("translator", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Sort By")
        for value, label, checked in self.SORT:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("sort", **opts))
        page.form.append(fieldset)
        page.add_output_options("html")

    def run(self):
        """Override the base class method to handle additional buttons."""

        if self.request == self.GLOSSARY:
            self.redirect("glossary-translation-jobs.py")
        elif self.request == self.MEDIA:
            self.redirect("media-translation-jobs.py")
        else:
            Controller.run(self)

    @cached_property
    def buttons(self):
        """Customize the form's buttons."""
        return self.SUBMIT, self.GLOSSARY, self.MEDIA

    @cached_property
    def change(self):
        """Summary change type(s) selected for the report."""

        types = []
        for value in self.fields.getlist("change"):
            try:
                change = int(value)
            except Exception:
                self.bail()
            if change not in self.changes.map:
                self.bail()
            types.append(change)
        return types

    @cached_property
    def changes(self):
        """Valid values for summary change types."""
        return self.load_valid_values("summary_change_type")

    @cached_property
    def columns(self):
        """Headers for the top of the table."""

        columns = (
            self.Reporter.Column("CDR ID"),
            self.Reporter.Column("Title", width="500px"),
            self.Reporter.Column("Audience", width="150px"),
            self.Reporter.Column("Assigned To", width="175px"),
            self.Reporter.Column("Translation Status", width="175px"),
            self.Reporter.Column("Translation Status Date", width="100px"),
            self.Reporter.Column("Type of Change", width="175px"),
            self.Reporter.Column("TRANSLATED DOC CDR ID"),
            self.Reporter.Column("Comments"),
        )
        if self.format == "html":
            return [column.name for column in columns]
        return columns

    @cached_property
    def comments(self):
        """Show comments in full or truncated?"""

        default = self.COMMENTS[0][0]
        comments = self.fields.getvalue("comments", default)
        if comments not in {c[0] for c in self.COMMENTS}:
            self.bail()
        return comments

    @cached_property
    def counts(self):
        """Cumulator for state-specific totals."""

        counts = defaultdict(int)
        for job in self.jobs:
            counts[job.state] += 1
        return counts

    @cached_property
    def end(self):
        """End of the date range for the report."""

        end = self.parse_date(self.fields.getvalue("end"))
        if not end:
            args = (
                self.started.year,
                self.started.month,
                self.started.day,
            )
            return date(*args)
        return end

    @cached_property
    def jobs(self):
        """Sequence of `Job` objects used for the report."""

        query = self.Query(self.TABLES[self.type], *self.FIELDS)
        query.join("usr u", "u.id = j.assigned_to")
        query.join("document d", "d.id = j.english_id")
        query.join("summary_translation_state s",
                   "s.value_id = j.state_id")
        query.join("summary_change_type c", "c.value_id = j.change_type")
        query.where(f"j.state_date >= '{self.start}'")
        query.where(f"j.state_date <= '{self.end} 23:59:59'")
        if self.translator:
            query.where(query.Condition("u.id", self.translator, "IN"))
        if self.state:
            query.where(query.Condition("s.value_id", self.state, "IN"))
        if self.change:
            query.where(query.Condition("c.value_id", self.change, "IN"))
        rows = query.order(*self.sort).execute(self.cursor).fetchall()
        jobs = []
        for row in rows:
            job = Job(self, row)
            if not jobs or job != jobs[-1]:
                jobs.append(job)
        return jobs

    @cached_property
    def rows(self):
        """Collect the rows for the report's table."""

        rows = [job.row for job in self.jobs]
        if self.type == "current":
            ncols = len(self.columns)
            rows.append(["\N{NO-BREAK SPACE}"] * ncols)
            padding = [""] * (ncols - 2)
            row = ["", self.Reporter.Cell("TOTALS", bold=True)] + padding
            rows.append(row)
            padding = [""] * (ncols - 3)
            for state in sorted(self.counts):
                row = ["", state, self.counts[state]] + padding
                rows.append(row)
        return rows

    @cached_property
    def sort(self):
        """Columns to be used for the user's selected sort order."""

        sort = self.fields.getvalue("sort", self.SORT_VALS[0])
        if sort not in self.SORT_VALS:
            self.bail()
        columns = [sort]
        if sort != "d.title":
            columns.append("d.title")
        return columns

    @cached_property
    def start(self):
        """Beginning of the date range for the report."""

        start = self.parse_date(self.fields.getvalue("start"))
        return start if start else self.end - timedelta(7)

    @cached_property
    def state(self):
        """State(s) selected for the report."""

        states = []
        for value in self.fields.getlist("state"):
            try:
                state = int(value)
            except Exception:
                self.bail()
            if state not in self.states.map:
                self.bail()
            states.append(state)
        return states

    @cached_property
    def states(self):
        """Valid values for summary translation states."""
        return self.load_valid_values("summary_translation_state")

    @cached_property
    def subtitle(self):
        """What do we display immediately under the top banner?"""

        if self.type == "history":
            return "Translation Job History Report"
        return self.SUBTITLE

    @cached_property
    def translator(self):
        """Translator(s) selected for the report."""

        translators = []
        for value in self.fields.getlist("translator"):
            try:
                translator = int(value)
            except Exception:
                self.bail()
            if translator not in self.translators.map:
                self.bail()
            translators.append(translator)
        return translators

    @cached_property
    def translators(self):
        """Members of the Spanish Translators group."""
        return self.load_group("Spanish Translators")

    @cached_property
    def type(self):
        """History or just the current jobs."""

        report_type = self.fields.getvalue("type", self.TYPES[0][0])
        if report_type not in {t[0] for t in self.TYPES}:
            self.bail()
        return report_type

    @cached_property
    def wide_css(self):
        """Give the table more horizontal room."""
        return self.Reporter.Table.WIDE_CSS


class Job:
    """
    Represents a translation job for the currently selected English
    CDR Summary document.
    """

    FIELDS = "english_id", "state", "change", "user", "date", "comments"

    def __init__(self, control, row):
        """Remember the caller's values.

        Pass:
            control - access to the database and report-building tools
            row - values from the database query
        """

        self.__control = control
        self.__row = row

    def __ne__(self, other):
        """Determine whether two jobs have the same values."""

        for name in self.FIELDS:
            if getattr(self, name) != getattr(other, name):
                return True
        return False

    @cached_property
    def audience(self):
        """String for the PDQ summary's audience."""
        return self.__row.title.split(";")[-1]

    @cached_property
    def change(self):
        """String for the type of change made to the English PDQ summary."""
        return self.__row.change_value

    @cached_property
    def comments(self):
        """String for notes on this job."""
        return self.__row.comments

    @cached_property
    def date(self):
        """When the current translation job's state was last modified."""
        return str(self.__row.state_date)[:10]

    @cached_property
    def english_id(self):
        """Integer for the CDR ID of the original language summary."""
        return self.__row.english_id

    @cached_property
    def row(self):
        """Assemble the row for the report's table."""

        Cell = self.__control.Reporter.Cell
        comments = (self.comments or "").strip().replace("\r", "")
        if self.__control.comments == "short":
            comments = comments.replace("\n", "")
            if len(comments) > 40:
                comments = Cell(f"{comments[:40]}...", title=comments)
        else:
            comments = comments.split("\n")
        return (
            self.english_id,
            self.title,
            self.audience,
            self.user,
            self.state,
            Cell(self.date, classes="nowrap"),
            self.change,
            self.spanish_id,
            comments,
        )

    @cached_property
    def spanish_id(self):
        """Integer for the CDR ID of the translated summary document."""

        query = self.__control.Query("query_term", "doc_id")
        query.where("path = '/Summary/TranslationOf/@cdr:ref'")
        query.where(query.Condition("int_val", self.english_id))
        row = query.execute(self.__control.cursor).fetchone()
        return row.doc_id if row else None

    @cached_property
    def state(self):
        """Which phase of the translation job have we reached?"""
        return self.__row.state_value

    @cached_property
    def title(self):
        """String for the title of the original language summary."""
        return self.__row.title.split(";")[0]

    @cached_property
    def user(self):
        """String for the full name of the translator."""
        return self.__row.fullname


if __name__ == "__main__":
    """Make it possible to load this script as a module."""
    Control().run()
