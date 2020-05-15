#!/usr/bin/env python

"""Generate parameterized reports on the CDR glossary translation job queue.

https://tracker.nci.nih.gov/browse/OCECDR-4487
"""

from datetime import date, timedelta
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
    REPORTS_MENU = SUBMENU = "Reports"
    ADMINMENU = "Admin"
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

    def show_report(self):
        """Override the base class version so we can add extra buttons."""

        page = self.report.page
        buttons = page.body.find("form/header/h1/span")
        buttons.insert(0, page.button(self.MEDIA))
        buttons.insert(0, page.button(self.SUMMARY))
        self.report.send(self.format)

    @property
    def buttons(self):
        """Customize the form's buttons."""

        return (
            self.SUBMIT,
            self.SUMMARY,
            self.MEDIA,
            self.REPORTS_MENU,
            self.ADMINMENU,
            self.LOG_OUT,
        )

    @property
    def columns(self):
        """Headers for the top of the table."""

        if not hasattr(self, "_columns"):
            self._columns = (
                self.Reporter.Column("CDR ID"),
                self.Reporter.Column("TITLE", width="500px"),
                self.Reporter.Column("STATUS", width="175px"),
                self.Reporter.Column("STATUS DATE", width="100px"),
                self.Reporter.Column("ASSIGNED TO", width="175px"),
                self.Reporter.Column("COMMENT", width="250px")
            )
        return self._columns

    @property
    def comments(self):
        """Show comments in full or truncated?"""

        if not hasattr(self, "_comments"):
            default = self.COMMENTS[0][0]
            self._comments = self.fields.getvalue("comments", default)
            if self._comments not in {c[0] for c in self.COMMENTS}:
                self.bail()
        return self._comments

    @property
    def end(self):
        """End of the date range for the report."""

        if not hasattr(self, "_end"):
            self._end = self.parse_date(self.fields.getvalue("end"))
            if not self._end:
                args = (
                    self.started.year,
                    self.started.month,
                    self.started.day,
                )
                self._end = date(*args)
        return self._end

    @property
    def jobs(self):
        """Sequence of `Job` objects used for the report."""

        if not hasattr(self, "_jobs"):
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
            self._jobs = []
            for row in query.execute(self.cursor).fetchall():
                job = Job(self, row)
                if not self._jobs or job != self._jobs[-1]:
                    self._jobs.append(job)
        return self._jobs

    @property
    def rows(self):
        """Collect the rows for the report's table."""

        if not hasattr(self, "_rows"):
            self._rows = [job.row for job in sorted(self.jobs)]
        return self._rows

    @property
    def sort(self):
        """In which order does the user want the report rows?"""

        if not hasattr(self, "_sort"):
            self._sort = self.fields.getvalue("sort", self.SORT[0])
            if self._sort not in self.SORT:
                self.bail()
        return self._sort

    @property
    def start(self):
        """Beginning of the date range for the report."""

        if not hasattr(self, "_start"):
            self._start = self.parse_date(self.fields.getvalue("start"))
            if not self._start:
                self._start = self.end - timedelta(7)
        return self._start

    @property
    def state(self):
        """State(s) selected for the report."""

        if not hasattr(self, "_state"):
            self._state = []
            for value in self.fields.getlist("state"):
                try:
                    state = int(value)
                except Exception:
                    self.bail()
                if state not in self.states.map:
                    self.bail()
                self._state.append(state)
        return self._state

    @property
    def state_sequence(self):
        if not hasattr(self, "_state_sequence"):
            self._state_sequence = {}
            for i, state in enumerate(self.states.values):
                state_id, state_name = state
                self._state_sequence[state_name] = i
        return self._state_sequence

    @property
    def states(self):
        """Valid values for glossary translation states."""

        if not hasattr(self, "_states"):
            self._states = self.load_valid_values("glossary_translation_state")
        return self._states

    @property
    def translator(self):
        """Translator(s) selected for the report."""

        if not hasattr(self, "_translator"):
            self._translator = []
            for value in self.fields.getlist("translator"):
                try:
                    translator = int(value)
                except Exception:
                    self.bail()
                if translator not in self.translators.map:
                    self.bail()
                self._translator.append(translator)
        return self._translator

    @property
    def translators(self):
        """Members of the Spanish Glossary Translators group."""

        if not hasattr(self, "_translators"):
            self._translators = self.load_group("Spanish Glossary Translators")
        return self._translators

    @property
    def type(self):
        """History or just the current jobs."""

        if not hasattr(self, "_type"):
            self._type = self.fields.getvalue("type", self.TYPES[0][0])
            if self._type not in {t[0] for t in self.TYPES}:
                self.bail()
        return self._type


class Job:
    """
    Represents a translation job for the currently selected CDR
    Glossary document.
    """

    FIELDS = "doc_id", "state", "user", "state_date", "comments"

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

    @property
    def comments(self):
        """String for notes on this job."""
        return self.__row.comments

    @property
    def date(self):
        """String for the date portion of the date/time value."""

        if not hasattr(self, "_date"):
            self._date = str(self.state_date)[:10]
        return self._date

    @property
    def doc_id(self):
        """Integer for the CDR ID of the glossary document."""
        return self.__row.doc_id

    @property
    def doc_type(self):
        """GlossaryTermName or GlossaryTermConcept."""

        if not hasattr(self, "_doc_type"):
            query = self.__control.Query("doc_type t", "t.name")
            query.join("document d", "d.doc_type = t.id")
            query.where(query.Condition("d.id", self.doc_id))
            row = query.execute(self.__control.cursor).fetchone()
            if not row:
                self.__control.bail(f"Unable to find CDR{self.doc_id}")
            self._doc_type = row.name
        return self._doc_type

    @property
    def key(self):
        """Sort key depends on the selected order for the report."""

        if not hasattr(self, "_key"):
            if self.__control.sort == "Glossary CDR ID":
                self._key = self.doc_id
            elif self.__control.sort == "Processing Status":
                state_sequence = self.__control.state_sequence[self.state]
                self._key = state_sequence, self.title.lower()
            elif self.__control.sort == "Status Date":
                self._key = self.date, self.title.lower()
            elif self.__control.sort == "User":
                self._key = self.user, self.title.lower()
            else:
                self._key = self.title.lower()
        return self._key

    @property
    def row(self):
        """Assemble the row for the report's table."""

        if not hasattr(self, "_row"):
            Cell = self.__control.Reporter.Cell
            comments = (self.comments or "").strip().replace("\r", "")
            if self.__control.comments == "short":
                comments = comments.replace("\n", "")
                if len(comments) > 40:
                    comments = Cell(f"{comments[:40]}...", title=comments)
            else:
                comments = comments.split("\n")
            self._row = (
                self.doc_id,
                self.title,
                self.state,
                Cell(self.date, classes="nowrap"),
                self.user,
                comments,
            )
        return self._row

    @property
    def state(self):
        """Which phase of the translation job have we reached?"""
        return self.__row.value_name

    @property
    def state_date(self):
        """When the current translation job's state was last modified."""
        return self.__row.state_date

    @property
    def title(self):
        """String for the document title (artificial for concept docs)."""

        if not hasattr(self, "_title"):
            if self.doc_type.lower() == "glossarytermname":
                query = self.__control.Query("document", "title")
                query.where(query.Condition("id", self.doc_id))
                row = query.execute(self.__control.cursor).fetchone()
                self._title = row.title.split(";")[0] if row else None
            else:
                path = "/GlossaryTermName/GlossaryTermConcept/@cdr:ref"
                query = self.__control.Query("document d", "d.title").limit(1)
                query.join("query_term q", "q.doc_id = d.id")
                query.where(query.Condition("q.path", path))
                query.where(query.Condition("q.int_val", self.doc_id))
                query.order("d.title")
                row = query.execute(self.__control.cursor).fetchone()
                if row:
                    title = row.title.split(";")[0]
                    self._title = f"GTC for {title}"
                else:
                    self._title = f"GTC CDR{self.doc_id:d}"
        return self._title

    @property
    def user(self):
        """String for the full name of the translator."""
        return self.__row.fullname


if __name__ == "__main__":
    """Make it possible to load this script as a module."""
    Control().run()
