#!/usr/bin/env python

"""Generate parameterized reports on the CDR glossary translation job queue.

https://tracker.nci.nih.gov/browse/OCECDR-4487
"""

from datetime import date, timedelta
from functools import cached_property
from cdrcgi import Controller


class Control(Controller):
    """Access to the database and report-building tools."""

    SUBTITLE = "Translation Job Workflow Report"
    FIELDS = (
        "j.doc_id",
        "s.value_name",
        "u.fullname",
        "j.state_date",
        "j.comments",
    )
    SORT = (
        "Processing Status",
        "Status Date",
        "User",
        "Glossary CDR ID",
        "Glossary Title",
    )
    SUMMARY = "Summary"
    MEDIA = "Media"
    TYPES = (
        ("current", "Current Jobs", True),
        ("history", "Job History", False),
    )
    TABLES = dict(
        current="glossary_translation_job j",
        history="glossary_translation_job_history j",
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
        fieldset = page.fieldset("Users (all if none checked)")
        for value, label in self.translators.items:
            opts = dict(label=label, value=value)
            fieldset.append(page.checkbox("translator", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Sort By")
        checked = True
        for value in self.SORT:
            opts = dict(value=value, label=value, checked=checked)
            fieldset.append(page.radio_button("sort", **opts))
            checked = False
        page.form.append(fieldset)
        page.add_output_options("html")

    def run(self):
        """Override the base class method to handle additional buttons."""

        if self.request == self.MEDIA:
            self.redirect("media-translation-jobs.py")
        elif self.request == self.SUMMARY:
            self.redirect("translation-jobs.py")
        else:
            Controller.run(self)

    @cached_property
    def buttons(self):
        """Customize the form's buttons."""
        return self.SUBMIT, self.SUMMARY, self.MEDIA

    @cached_property
    def columns(self):
        """Headers for the top of the table."""

        column_values = (
            ("CDR ID", None),
            ("Title", 500),
            ("Status", 175),
            ("Status Date", 100),
            ("Assigned To", 175),
            ("Comment", 250),
        )
        if self.format == "html":
            return [values[0] for values in column_values]
        columns = []
        for header, width in column_values:
            opts = dict(width=f"{width}px") if width else {}
            columns.append(self.Reporter.Column(header, **opts))
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
    def end(self):
        """End of the date range for the report."""

        end = self.parse_date(self.fields.getvalue("end"))
        if end:
            return end
        return date(self.started.year, self.started.month, self.started.day)

    @cached_property
    def jobs(self):
        """Sequence of `Job` objects used for the report."""

        query = self.Query(self.TABLES[self.type], *self.FIELDS)
        query.join("usr u", "u.id = j.assigned_to")
        query.join("document d", "d.id = j.doc_id")
        query.join("glossary_translation_state s",
                   "s.value_id = j.state_id")
        query.where(f"j.state_date >= '{self.start}'")
        query.where(f"j.state_date <= '{self.end} 23:59:59'")
        if self.translator:
            query.where(query.Condition("u.id", self.translator, "IN"))
        if self.state:
            query.where(query.Condition("s.value_id", self.state, "IN"))
        jobs = []
        for row in query.execute(self.cursor).fetchall():
            job = Job(self, row)
            if not jobs or job != jobs[-1]:
                jobs.append(job)
        return jobs

    @cached_property
    def rows(self):
        """Collect the rows for the report's table."""
        return [job.row for job in sorted(self.jobs)]

    @cached_property
    def same_window(self):
        """Don't open a new browser tab for these buttons."""
        return self.SUMMARY, self.MEDIA

    @cached_property
    def sort(self):
        """In which order does the user want the report rows?"""

        sort = self.fields.getvalue("sort", self.SORT[0])
        if sort not in self.SORT:
            self.bail()
        return sort

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
    def state_sequence(self):
        """Map used for ordering the job states."""

        state_sequence = {}
        for i, state in enumerate(self.states.values):
            state_id, state_name = state
            state_sequence[state_name] = i
        return state_sequence

    @cached_property
    def states(self):
        """Valid values for glossary translation states."""
        return self.load_valid_values("glossary_translation_state")

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
        """Members of the Spanish Glossary Translators group."""
        return self.load_group("Spanish Glossary Translators")

    @cached_property
    def type(self):
        """History or just the current jobs."""

        type = self.fields.getvalue("type", self.TYPES[0][0])
        if type not in {t[0] for t in self.TYPES}:
            self.bail()
        return type

    @cached_property
    def wide_css(self):
        """Override so we can widen the report table."""
        return self.Reporter.Table.WIDE_CSS


class Job:
    """
    Represents a translation job for the currently selected CDR
    Glossary document.
    """

    FIELDS = "doc_id", "state", "user", "date", "comments"

    def __init__(self, control, row):
        """Remember the caller's values.

        Pass:
            control - access to the database and report-building tools
            row - values from the database query
        """

        self.__control = control
        self.__row = row

    def __lt__(self, other):
        """Order the jobs according to the chosen sort method."""
        return self.key < other.key

    def __ne__(self, other):
        """Determine whether two jobs have the same values."""

        for name in self.FIELDS:
            if getattr(self, name) != getattr(other, name):
                return True
        return False

    @cached_property
    def comments(self):
        """String for notes on this job."""
        return self.__row.comments

    @cached_property
    def date(self):
        """String for the date portion of the date/time value."""
        return str(self.__row.state_date)[:10]

    @cached_property
    def doc_id(self):
        """Integer for the CDR ID of the glossary document."""
        return self.__row.doc_id

    @cached_property
    def doc_type(self):
        """GlossaryTermName or GlossaryTermConcept."""

        query = self.__control.Query("doc_type t", "t.name")
        query.join("document d", "d.doc_type = t.id")
        query.where(query.Condition("d.id", self.doc_id))
        row = query.execute(self.__control.cursor).fetchone()
        if not row:
            self.__control.bail(f"Unable to find CDR{self.doc_id}")
        return row.name

    @cached_property
    def key(self):
        """Sort key depends on the selected order for the report."""

        if self.__control.sort == "Glossary CDR ID":
            return self.doc_id
        elif self.__control.sort == "Processing Status":
            state_sequence = self.__control.state_sequence[self.state]
            return state_sequence, self.title.lower()
        elif self.__control.sort == "Status Date":
            return self.date, self.title.lower()
        elif self.__control.sort == "User":
            return self.user, self.title.lower()
        else:
            return self.title.lower()
        return self._key

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
            self.doc_id,
            self.title,
            self.state,
            Cell(self.date, classes="nowrap"),
            self.user,
            comments,
        )

    @property
    def state(self):
        """Which phase of the translation job have we reached?"""
        return self.__row.value_name

    @cached_property
    def title(self):
        """String for the document title (artificial for concept docs)."""

        if self.doc_type.lower() == "glossarytermname":
            query = self.__control.Query("document", "title")
            query.where(query.Condition("id", self.doc_id))
            row = query.execute(self.__control.cursor).fetchone()
            return row.title.split(";")[0] if row else None
        path = "/GlossaryTermName/GlossaryTermConcept/@cdr:ref"
        query = self.__control.Query("document d", "d.title").limit(1)
        query.join("query_term q", "q.doc_id = d.id")
        query.where(query.Condition("q.path", path))
        query.where(query.Condition("q.int_val", self.doc_id))
        query.order("d.title")
        row = query.execute(self.__control.cursor).fetchone()
        if row:
            title = row.title.split(";")[0]
            return f"GTC for {title}"
        return f"GTC CDR{self.doc_id:d}"

    @property
    def user(self):
        """String for the full name of the translator."""
        return self.__row.fullname


if __name__ == "__main__":
    """Make it possible to load this script as a module."""
    Control().run()
