#!/usr/bin/env python

"""Generate parameterized reports on the CDR media translation job queue.

https://tracker.nci.nih.gov/browse/OCECDR-4491
"""

from datetime import date, timedelta
from cdrcgi import Controller


class Control(Controller):
    """Access to the database and report-building tools."""

    SUBTITLE = "Translation Job Workflow Report"
    FIELDS = (
        "j.english_id",
        "d.title",
        "s.value_name",
        "u.fullname",
        "j.state_date",
        "j.comments",
    )
    SORT = (
        ("s.value_pos", "Processing Status", True),
        ("j.state_date", "Status Date", False),
        ("u.fullname", "User", False),
        ("j.english_id", "Media CDR ID", False),
        ("d.title", "Media Title", False),
    )
    SORT_VALS = [s[0] for s in SORT]
    SUMMARY = "Summary"
    GLOSSARY = "Glossary"
    REPORTS_MENU = SUBMENU = "Reports"
    ADMINMENU = "Admin"
    TYPES = (
        ("current", "Current Jobs", True),
        ("history", "Job History", False),
    )
    TABLES = dict(
        current="media_translation_job j",
        history="media_translation_job_history j",
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
        for value, label, checked in self.SORT:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("sort", **opts))
        page.form.append(fieldset)
        page.add_output_options("html")

    def run(self):
        """Override the base class method to handle additional buttons."""

        if self.request == self.GLOSSARY:
            self.redirect("glossary-translation-jobs.py")
        elif self.request == self.SUMMARY:
            self.redirect("translation-jobs.py")
        Controller.run(self)

    def show_report(self):
        """Override the base class version so we can add extra buttons."""

        page = self.report.page
        buttons = page.body.find("form/header/h1/span")
        buttons.insert(0, page.button(self.GLOSSARY))
        buttons.insert(0, page.button(self.SUMMARY))
        self.report.send(self.format)

    @property
    def buttons(self):
        """Customize the form's buttons."""

        return (
            self.SUBMIT,
            self.SUMMARY,
            self.GLOSSARY,
            self.REPORTS_MENU,
            self.ADMINMENU,
            self.LOG_OUT,
        )

    @property
    def columns(self):
        """Headers for the top of the table."""

        if not hasattr(self, "_columns"):
            self._columns = (
                self.Reporter.Column("CDR ID EN"),
                self.Reporter.Column("TITLE EN", width="500px"),
                self.Reporter.Column("CDR ID ES", width="175px"),
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
            query.join("document d", "d.id = j.english_id")
            query.join("media_translation_state s", "s.value_id = j.state_id")
            query.where(f"j.state_date >= '{self.start}'")
            query.where(f"j.state_date <= '{self.end} 23:59:59'")
            if self.translator:
                query.where(query.Condition("u.id", self.translator, "IN"))
            if self.state:
                query.where(query.Condition("s.value_id", self.state, "IN"))
            rows = query.order(*self.sort).execute(self.cursor).fetchall()
            self._jobs = []
            for row in rows:
                job = Job(self, row)
                if not self._jobs or job != self._jobs[-1]:
                    self._jobs.append(job)
        return self._jobs

    @property
    def rows(self):
        """Collect the rows for the report's table."""

        if not hasattr(self, "_rows"):
            self._rows = [job.row for job in self.jobs]
        return self._rows

    @property
    def sort(self):
        """Columns to be used for the user's selected sort order."""

        if not hasattr(self, "_sort"):
            sort = self.fields.getvalue("sort", self.SORT_VALS[0])
            if sort not in self.SORT_VALS:
                self.bail()
            self._sort = [sort]
            if sort in ("j.english_id", "d.title"):
                self._sort.append("j.state_date")
            else:
                self._sort.append("d.title")
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
    def states(self):
        """Valid values for media translation states."""

        if not hasattr(self, "_states"):
            self._states = self.load_valid_values("media_translation_state")
        return self._states

    @property
    def subtitle(self):
        """What do we display immediately under the top banner?"""

        if self.type == "history":
            return "Translation Job History Report"
        return self.SUBTITLE

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
        """Members of the Spanish Media Translators group."""

        if not hasattr(self, "_translators"):
            self._translators = self.load_group("Spanish Media Translators")
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
    Represents a translation job for the currently selected English
    CDR Media document.
    """

    URL = "media-translation-job.py?Session=%s&english_id=%s"
    FIELDS = "english_id", "state", "user", "date", "comments"

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

    @property
    def comments(self):
        """String for notes on this job."""
        return self.__row.comments

    @property
    def date(self):
        """When the current translation job's state was last modified."""
        return self.__row.state_date

    @property
    def english_id(self):
        """Integer for the CDR ID of the original language summary."""
        return self.__row.english_id

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
                self.english_id,
                self.title,
                self.spanish_id,
                self.state,
                Cell(str(self.date)[:10], classes="nowrap"),
                self.user,
                comments,
            )
        return self._row

    @property
    def spanish_id(self):
        """Integer for the CDR ID of the translated summary document."""

        if not hasattr(self, "_spanish_id"):
            query = self.__control.Query("query_term", "doc_id")
            query.where("path = '/Media/TranslationOf/@cdr:ref'")
            query.where(query.Condition("int_val", self.english_id))
            row = query.execute(self.__control.cursor).fetchone()
            self._spanish_id = row.doc_id if row else None
        return self._spanish_id

    @property
    def state(self):
        """Which phase of the translation job have we reached?"""
        return self.__row.value_name

    @property
    def title(self):
        """String for the title of the original language summary."""

        if not hasattr(self, "_title"):
            self._title = self.__row.title.split(";")[0]
        return self._title

    @property
    def user(self):
        """String for the full name of the translator."""
        return self.__row.fullname


if __name__ == "__main__":
    """Make it possible to load this script as a module."""
    Control().run()
