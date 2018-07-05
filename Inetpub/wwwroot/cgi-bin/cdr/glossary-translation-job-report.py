"""
Generate parameterized reports on the CDR glossary translation job queue.

https://tracker.nci.nih.gov/browse/OCECDR-4487
"""

import datetime
import operator
import cdrcgi
from cdrapi import db

class Control(cdrcgi.Control):
    """
    Let the user specify filtering, sorting, and output format for
    a report on the CDR glossary translation queue jobs, and then
    generate and return that report.
    """

    SORT = (
        "Processing Status",
        "Status Date",
        "User",
        "Glossary CDR ID",
        "Glossary Title"
    )
    TAMPERING = cdrcgi.TAMPERING

    def __init__(self):
        """
        Collect and validate the report request's parameters.
        """

        cdrcgi.Control.__init__(self, "Translation Job Workflow Report")
        self.cursor = db.connect().cursor()
        self.states = self.load_values("glossary_translation_state")
        self.translators = self.load_group("Spanish Glossary Translators")
        self.start = self.fields.getvalue("start")
        self.end = self.fields.getvalue("end")
        self.type = self.fields.getvalue("type")
        self.state = self.get_list("state", self.states.map)
        self.translator = self.get_list("translator", self.translators)
        self.sort = self.fields.getvalue("sort") or self.SORT[0]
        self.comments = self.fields.getvalue("comments")
        cdrcgi.valParmVal(self.sort, valList=self.SORT, msg=self.TAMPERING)
        cdrcgi.valParmDate(self.start, empty_ok=True, msg=self.TAMPERING)
        cdrcgi.valParmDate(self.end, empty_ok=True, msg=self.TAMPERING)
        if self.type == "current":
            self.title = self.PAGE_TITLE = "Translation Job Workflow Report"
        else:
            self.title = self.PAGE_TITLE = "Translation Job History Report"

    def populate_form(self, form):
        """
        Let the user select which jobs to report, how to sort them, and
        whether the report should be an HTML page or an Excel spreadsheet.
        """

        end = datetime.date.today()
        start = end - datetime.timedelta(7)
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Date Range"))
        form.add_date_field("start", "Start", value=str(start))
        form.add_date_field("end", "End", value=str(end))
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Report Type"))
        form.add_radio("type", "Current Jobs", "current", checked=True)
        form.add_radio("type", "Job History", "history")
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Comment Display"))
        form.add_radio("comments", "Shortened", "short", checked=True)
        form.add_radio("comments", "Full", "full")
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Statuses (all if none checked)"))
        for value, label in self.states.values:
            form.add_checkbox("state", label, value)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Users (all if none checked)"))
        for value, label in self.sort_dict(self.translators):
            form.add_checkbox("translator", label, value)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Sort By"))
        checked = True
        for value in self.SORT:
            form.add_radio("sort", value, value, checked=checked)
            checked = False
        form.add("</fieldset>")
        form.add_output_options("html")

    def different(self, old, new):
        if old is None:
            return True
        if old.doc_id != new.doc_id:
            return True
        if old.value_name != new.value_name:
            return True
        if old.fullname != new.fullname:
            return True
        if old.state_date != new.state_date:
            return True
        if old.comments != new.comments:
            return True
        return False

    def build_tables(self):
        """
        Generate the single table for the report, filtered and sorted
        as requested.
        """

        fields = ("j.doc_id", "s.value_name", "u.fullname", "j.state_date",
                  "j.comments")
        if self.type == "current":
            query = db.Query("glossary_translation_job j", *fields)
        else:
            query = db.Query("glossary_translation_job_history j", *fields)
        query.join("usr u", "u.id = j.assigned_to")
        query.join("document d", "d.id = j.doc_id")
        query.join("glossary_translation_state s", "s.value_id = j.state_id")
        # dates have been sanitized above
        if self.start:
            query.where("j.state_date >= '%s'" % self.start)
        if self.end:
            query.where("j.state_date <= '%s 23:59:59'" % self.end)
        if self.translator:
            query.where(query.Condition("u.id", self.translator, "IN"))
        if self.state:
            query.where(query.Condition("s.value_id", self.state, "IN"))
        rows = query.execute(self.cursor).fetchall()
        jobs = []
        previous = None
        for row in rows:
            if self.different(previous, row):
                jobs.append(Job(self, row))
                previous = row
        rows = [job.row() for job in sorted(jobs)]
        columns = (
            cdrcgi.Report.Column("CDR ID"),
            cdrcgi.Report.Column("TITLE", width="500px"),
            cdrcgi.Report.Column("STATUS", width="175px"),
            cdrcgi.Report.Column("STATUS DATE", width="100px"),
            cdrcgi.Report.Column("ASSIGNED TO", width="175px"),
            cdrcgi.Report.Column("COMMENT", width="250px")
        )
        # There are no requirements for this report to include totals (yet)
        if False and self.type == "current":
            ncols = len(columns)
            rows.append([unichr(160)] * ncols)
            padding = [""] * (ncols - 2)
            rows.append(["", cdrcgi.Report.Cell("TOTALS", bold=True)] + padding)
            for state in sorted(Job.COUNTS):
                rows.append(["", state, Job.COUNTS[state]] + [""] * (ncols - 3))
        return [cdrcgi.Report.Table(columns, rows)]

    def load_group(self, group):
        """
        Fetch the user ID and name for all members of a specified group.

        Pass:
            group - name of group to fetch

        Return:
            dictionary of user names indexed by user ID
        """

        query = db.Query("usr u", "u.id", "u.fullname")
        query.join("grp_usr gu", "gu.usr = u.id")
        query.join("grp g", "g.id = gu.grp")
        query.where("u.expired IS NULL")
        query.where(query.Condition("g.name", group))
        rows = query.execute(self.cursor).fetchall()
        return dict([(row[0], row[1]) for row in rows])

    def load_values(self, table_name):
        """
        Factor out logic for collecting a valid values set.

        This works because our tables for valid values both
        have the same structure.

        Returns a populated Values object.
        """

        query = db.Query(table_name, "value_id", "value_name")
        rows = query.order("value_pos").execute(self.cursor).fetchall()
        class Values:
            def __init__(self, rows):
                self.map = {}
                self.values = []
                for value_id, value_name in rows:
                    self.map[value_id] = value_name
                    self.values.append((value_id, value_name))
        return Values(rows)

    @property
    def state_sequence(self):
        if not hasattr(self, "_state_sequence"):
            self._state_sequence = {}
            for i, state in enumerate(self.states.values):
                state_id, state_name = state
                self._state_sequence[state_name] = i
        return self._state_sequence

    def get_list(self, name, all_values):
        """
        Collect the values for the checkboxes selected by the user
        for a named group, and validate and return them.
        """

        values = []
        for value in self.fields.getlist(name):
            try:
                int_value = int(value)
            except:
                cdrcgi.bail()
            if int_value not in all_values:
                cdrcgi.bail()
            values.append(int_value)
        return values

    @staticmethod
    def sort_dict(d):
        """
        Generate a sequence from a dictionary, with the elements in the
        sequence ordered by the dictionary element's value. The sequence
        contain tuples of (key, value) pairs pulled from the dictionary.
        """

        return sorted(d.items(), key=operator.itemgetter(1))

class Job:
    """
    Represents a translation job for the currently selected CDR
    Glossary document.
    """

    URL = "glossary-translation-job.py?Session=%s&doc_id=%s"
    COUNTS = {}

    def __init__(self, control, row):
        """
        Collect the information about the CDR Glossary document being
        translated, as well as information about the ongoing translation
        job.
        """

        self.control = control
        self.doc_id = row.doc_id
        self.state = row.value_name
        self.user = row.fullname
        self.date = row.state_date
        self.comments = row.comments
        Job.COUNTS[self.state] = self.COUNTS.get(self.state, 0) + 1

    @property
    def doc_type(self):
        if not hasattr(self, "_doc_type"):
            query = db.Query("doc_type t", "t.name")
            query.join("document d", "d.doc_type = t.id")
            query.where(query.Condition("d.id", self.doc_id))
            row = query.execute(self.control.cursor).fetchone()
            self._doc_type = row.name
        return self._doc_type

    @property
    def title(self):
        if not hasattr(self, "_title"):
            if not self.doc_type:
                self._title = None
            elif self.doc_type.lower() == "glossarytermname":
                query = db.Query("document", "title")
                query.where(query.Condition("id", self.doc_id))
                row = query.execute(self.control.cursor).fetchone()
                self._title = row.title.split(";")[0] if row else None
            else:
                path = "/GlossaryTermName/GlossaryTermConcept/@cdr:ref"
                query = db.Query("document d", "d.title").limit(1)
                query.join("query_term q", "q.doc_id = d.id")
                query.where(query.Condition("q.path", path))
                query.where(query.Condition("q.int_val", self.doc_id))
                query.order("d.title")
                row = query.execute(self.control.cursor).fetchone()
                if row:
                    title = row.title.split(";")[0]
                    pattern = u"GTC for {}"
                    self._title = pattern.format(title)
                else:
                    pattern = u"GTC CDR{:d}"
                    self._title = pattern.format(self.doc_id)
        return self._title

    def row(self):
        """
        Generate a row for the report's table.
        """

        if self.control.comments == "short":
            full = display = self.comments or ""
            full = full.replace("\r", "").replace("\n", cdrcgi.NEWLINE)
            if len(display) > 40:
                display = display[:40] + "..."
            comments = cdrcgi.Report.Cell(display, title=full)
        else:
            comments = (self.comments or "").split("\n")
        return [
            self.doc_id,
            self.title,
            self.state,
            cdrcgi.Report.Cell(str(self.date)[:10], classes="nowrap"),
            self.user,
            comments
        ]

    @property
    def key(self):
        if self.control.sort == "Glossary CDR ID":
            return self.doc_id
        elif self.control.sort == "Processing Status":
            return self.control.state_sequence[self.state], self.title.lower()
        elif self.control.sort == "Status Date":
            return str(self.date)[:10], self.title.lower()
        elif self.control.sort == "User":
            return self.user, self.title.lower()
        else:
            return self.title.lower()

    def __cmp__(self, other):
        #key1 = self.key
        #key2 = other.key
        #self.control.logger.info("comparing %r against %r", key1, key2)
        return cmp(self.key, other.key)

if __name__ == "__main__":
    """
    Make it possible to load this script as a module.
    """

    Control().run()
