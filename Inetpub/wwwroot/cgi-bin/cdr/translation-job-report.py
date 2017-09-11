#----------------------------------------------------------------------
# Generate parameterized reports on the CDR summary translation job queue.
# JIRA::OCECDR-4193
#----------------------------------------------------------------------
import datetime
import operator
import cdrcgi
import cdrdb

class Control(cdrcgi.Control):
    """
    Let the user specify filtering, sorting, and output format for
    a report on the CDR summary translation queue jobs, and then
    generate and return that report.
    """

    SORT = (
        ("s.value_name", "Processing Status"),
        ("j.state_date", "Status Date"),
        ("u.fullname", "User"),
        ("c.value_name", "Type of Change"),
        ("d.title", "English Summary Title")
    )
    SORT_VALS = [s[0] for s in SORT]
    TAMPERING = cdrcgi.TAMPERING

    def __init__(self):
        """
        Collect and validate the report request's parameters.
        """

        cdrcgi.Control.__init__(self, "Translation Job Workflow Report")
        self.states = self.load_values("summary_translation_state")
        self.changes = self.load_values("summary_change_type")
        self.translators = self.load_group("Spanish Translators")
        self.start = self.fields.getvalue("start")
        self.end = self.fields.getvalue("end")
        self.state = self.get_list("state", self.states.map)
        self.change = self.get_list("change", self.changes.map)
        self.translator = self.get_list("translator", self.translators)
        self.sort = self.fields.getvalue("sort") or self.SORT[0][0]
        cdrcgi.valParmVal(self.sort, valList=self.SORT_VALS, msg=self.TAMPERING)
        cdrcgi.valParmDate(self.start, empty_ok=True, msg=self.TAMPERING)
        cdrcgi.valParmDate(self.end, empty_ok=True, msg=self.TAMPERING)

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
        form.add(form.B.LEGEND("Statuses (all if none checked)"))
        for value, label in self.states.values:
            form.add_checkbox("state", label, value)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Types of Change (all if none checked)"))
        for value, label in self.changes.values:
            form.add_checkbox("change", label, value)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Users (all if none checked)"))
        for value, label in self.sort_dict(self.translators):
            form.add_checkbox("translator", label, value)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Sort By"))
        checked = True
        for value, label in self.SORT:
            form.add_radio("sort", label, value, checked=checked)
            checked = False
        form.add("</fieldset>")
        form.add_output_options("html")

    def build_tables(self):
        """
        Generate the single table for the report, filtered and sorted
        as requested.
        """

        sort = [self.sort]
        if self.sort != "d.title":
            sort.append("d.title")
        fields = ("d.id", "d.title", "s.value_name", "c.value_name",
                  "u.fullname", "j.state_date", "j.comments")
        query = cdrdb.Query("summary_translation_job j", *fields)
        query.join("usr u", "u.id = j.assigned_to")
        query.join("document d", "d.id = j.english_id")
        query.join("summary_translation_state s", "s.value_id = j.state_id")
        query.join("summary_change_type c", "c.value_id = j.change_type")
        # dates have been sanitized above
        if self.start:
            query.where("j.state_date >= '%s'" % self.start)
        if self.end:
            query.where("j.state_date <= '%s 23:59:59'" % self.end)
        if self.translator:
            query.where(query.Condition("u.id", self.translator, "IN"))
        if self.state:
            query.where(query.Condition("s.value_id", self.state, "IN"))
        if self.change:
            query.where(query.Condition("c.value_id", self.change, "IN"))
        rows = query.order(*sort).execute(self.cursor).fetchall()
        jobs = [Job(self, *row) for row in rows]
        rows = [job.row() for job in jobs]
        columns = (
            cdrcgi.Report.Column("CDR ID"),
            cdrcgi.Report.Column("Title", width="500px"),
            cdrcgi.Report.Column("Audience", width="150px"),
            cdrcgi.Report.Column("Assigned To", width="175px"),
            cdrcgi.Report.Column("Translation Status", width="175px"),
            cdrcgi.Report.Column("Translation Status Date", width="100px"),
            cdrcgi.Report.Column("Type of Change", width="175px"),
            cdrcgi.Report.Column("TRANSLATED DOC CDR ID"),
            cdrcgi.Report.Column("Comments")
        )
        ncols = len(columns)
        rows.append([unichr(160)] * ncols)
        padding = [""] * (ncols - 2)
        rows.append(["", cdrcgi.Report.Cell("TOTALS", bold=True)] + padding)
        for state in sorted(Job.COUNTS):
            rows.append(["", state, Job.COUNTS[state]] + [""] * (ncols - 3))
        self.PAGE_TITLE = "Translation Job Workflow Report"
        return [cdrcgi.Report.Table(columns, rows)]

    def load_group(self, group):
        """
        Fetch the user ID and name for all members of a specified group.

        Pass:
            group - name of group to fetch

        Return:
            dictionary of user names indexed by user ID
        """

        query = cdrdb.Query("usr u", "u.id", "u.fullname")
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

        query = cdrdb.Query(table_name, "value_id", "value_name")
        rows = query.order("value_pos").execute(self.cursor).fetchall()
        class Values:
            def __init__(self, rows):
                self.map = {}
                self.values = []
                for value_id, value_name in rows:
                    self.map[value_id] = value_name
                    self.values.append((value_id, value_name))
        return Values(rows)

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
    Represents a translation job for the currently selected English
    CDR summary document.
    """

    URL = "translation-job.py?Session=%s&english_id=%s"
    COUNTS = {}

    def __init__(self, control, doc_id, title, state, change, user, date, cmt):
        """
        Collect the information about the English CDR summary document
        being translated, as well as about the corresponding translated
        Spanish document (if it exists). Also collect information about
        the ongoing translation job.
        """

        self.doc_id = doc_id
        self.title = title.split(";")[0]
        self.audience = title.split(";")[-1]
        self.state = state
        self.change = change
        self.user = user
        self.date = date
        self.comments = cmt
        Job.COUNTS[state] = self.COUNTS.get(state, 0) + 1
        self.spanish_id = self.spanish_title = self.spanish_audience = None
        query = cdrdb.Query("query_term q", "d.id", "d.title")
        query.join("document d", "d.id = q.doc_id")
        query.where("path = '/Summary/TranslationOf/@cdr:ref'")
        query.where(query.Condition("int_val", doc_id))
        row = query.execute(control.cursor).fetchone()
        if row:
            self.spanish_id, title = row
            title_parts = title.split(";")
            self.spanish_title = title = title_parts[0]
            self.spanish_audience = title_parts[-1]

    def row(self):
        """
        Generate a row for the report's table.
        """

        comments = self.comments or ""
        if len(comments) > 40:
            comments = comments[:40] + "..."
        return [
            self.doc_id,
            self.title,
            self.audience,
            self.user,
            self.state,
            cdrcgi.Report.Cell(str(self.date)[:10], classes="nowrap"),
            self.change,
            self.spanish_id or "",
            comments
        ]

if __name__ == "__main__":
    """
    Make it possible to load this script as a module.
    """

    Control().run()
