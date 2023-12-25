#!/usr/bin/env python

"""Create a new report based on the new ProcessingStatus block.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):

    SUBTITLE = "DIS Processing Status Report"
    LOGNAME = "DISProcessingStatusReport"
    STATUS_PATH = "/DrugInformationSummary/ProcessingStatus"
    VALUE_PATH = f"{STATUS_PATH}/ProcessingStatusValue"
    DATE_PATH = f"{STATUS_PATH}/StatusDate"

    def populate_form(self, page):
        """Add the fields to the report form.

        Pass:
            page - HTMLPage object where the fields go
        """

        fieldset = page.fieldset("Select Status Value(s)")
        for value in self.statuses:
            opts = dict(value=value, label=value)
            fieldset.append(page.checkbox("status", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Date Range")
        fieldset.append(page.date_field("start"))
        fieldset.append(page.date_field("end"))
        page.form.append(fieldset)
        page.add_output_options("html")

    def build_tables(self):
        """Assemble the report's table."""

        opts = dict(columns=self.columns, fixed=True)
        return [self.Reporter.Table(self.rows, **opts)]

    def show_report(self):
        """Override so we can widen the report table."""

        table = self.report.page.form.find("table")
        report_footer = self.report.page.main.find("p")
        report_footer.addprevious(table)
        css = ".report .usa-table { width: 90%; margin: 3rem auto 1.25rem; }"
        self.report.page.add_css(css)
        self.report.send(self.format)

    @cached_property
    def columns(self):
        """Column headers for the report's table."""

        return (
            "CDR ID",
            "DIS Title",
            "Processing Status Value",
            "Processing Status Date",
            "Entered By",
            self.Reporter.Column("Comments", width="20%"),
            "Last Version Publishable?",
            "Date First Published",
            "Published Date",
        )

    @property
    def drugs(self):
        """Documents selected for the report."""

        if not hasattr(self, "_drugs"):
            query = self.Query("query_term s", "s.doc_id").unique()
            query.where(f"s.path = '{self.VALUE_PATH}'")
            if self.status:
                query.where(query.Condition("s.value", self.status, "IN"))
            if self.start or self.end:
                query.join("query_term d", "d.doc_id = s.doc_id",
                           "LEFT(d.node_loc, 4) = LEFT(s.node_loc, 4)")
                if self.start:
                    start = str(self.start)
                    query.where(query.Condition("d.value", start, ">="))
                if self.end:
                    end = f"{self.end} 23:59:59"
                    query.where(query.Condition("d.value", end, "<="))
            rows = query.execute(self.cursor).fetchall()
            self._drugs = [Drug(self, row.doc_id) for row in rows]
        return self._drugs

    @property
    def end(self):
        """Ending date for the report's date range."""

        if not hasattr(self, "_end"):
            self._end = self.parse_date(self.fields.getvalue("end"))
        return self._end

    @property
    def rows(self):
        """Rows collected from the drug documents for the report."""

        if not hasattr(self, "_rows"):
            self._rows = []
            for drug in self.drugs:
                self._rows += drug.rows
        return self._rows

    @property
    def start(self):
        """Starting date for the report's date range."""

        if not hasattr(self, "_start"):
            self._start = self.parse_date(self.fields.getvalue("start"))
        return self._start

    @property
    def status(self):
        """Processing status(es) selected for the report."""

        if not hasattr(self, "_status"):
            self._status = self.fields.getlist("status")
            if set(self._status) - set(self.statuses):
                self.bail()
        return self._status

    @property
    def statuses(self):
        """Processing status values found in the data."""

        if not hasattr(self, "_statuses"):
            query = self.Query("query_term", "value").unique()
            query.where(f"path = '{self.VALUE_PATH}'")
            rows = query.execute(self.cursor).fetchall()
            self._statuses = sorted([row.value for row in rows])
        return self._statuses


class Drug:
    """Document with status value(s) selected for the report."""

    def __init__(self, control, id):
        """Save the caller's values.

        Pass:
            control - access to the database and the current session
            id - CDR document ID for the DrugInformationSummary document
        """

        self.__control = control
        self.__id = id

    @property
    def date_last_modified(self):
        """Date set by the users for the last significant change."""

        if not hasattr(self, "_date_last_modified"):
            query = self.__control.Query("query_term", "value")
            query.where("path = '/DrugInformationSummary/DateLastModified'")
            query.where(query.Condition("doc_id", self.doc.id))
            rows = query.execute(self.__control.cursor).fetchall()
            self._date_last_modified = rows[0].value if rows else None
        return self._date_last_modified

    @property
    def doc(self):
        """`Doc` object for the DIS document."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.__control.session, id=self.__id)
        return self._doc

    @property
    def last_version_publishable(self):
        """True if the most recently created version is marked publishable."""

        if not hasattr(self, "_last_version_publishable"):
            last_ver = self.doc.last_version
            pub_ver = self.doc.last_publishable_version
            self._last_version_publishable = pub_ver and pub_ver == last_ver
        return self._last_version_publishable

    @property
    def rows(self):
        """Table rows from this document for the report."""

        if not hasattr(self, "_rows"):
            self._rows = []
            first_pub = str(self.doc.first_pub or "")[:10]
            for status in sorted(self.statuses):
                lvp = "Y" if self.last_version_publishable else "N"
                dlm = self.date_last_modified
                self._rows.append([
                    self.__control.Reporter.Cell(self.doc.cdr_id, center=True),
                    self.title,
                    status.value,
                    self.__control.Reporter.Cell(status.date, center=True),
                    status.entered_by,
                    status.comment,
                    self.__control.Reporter.Cell(lvp, center=True),
                    self.__control.Reporter.Cell(first_pub, center=True),
                    self.__control.Reporter.Cell(dlm, center=True),
                ])
        return self._rows

    @property
    def statuses(self):
        """Sequence of statuses which are in scope for the report."""

        if not hasattr(self, "_statuses"):
            self._statuses = []
            for node in self.doc.root.findall("ProcessingStatus"):
                status = self.Status(self.__control, node)
                if status.in_scope:
                    self._statuses.append(status)
        return self._statuses

    @property
    def title(self):
        """Official name of the drug or drug combination."""

        if not hasattr(self, "_title"):
            self._title = Doc.get_text(self.doc.root.find("Title"))
            if not self._title:
                self._title = self.doc.title.split(";")[0]
        return self._title

    class Status:
        """A ProcessingStatus block from the DIS document."""

        def __init__(self, control, node):
            """Remember the caller's values.

            Pass:
                control - access to the report options
                node - the DOM node for the ProcessingStatus block
            """

            self.__control = control
            self.__node = node

        def __lt__(self, other):
            """Support sorting of the statuses by date."""
            return self.date < other.date

        @property
        def comment(self):
            """The (optional) comment entered for the status."""

            if not hasattr(self, "_comment"):
                self._comment = Doc.get_text(self.__node.find("Comment"))
            return self._comment

        @property
        def date(self):
            """The date (ISO format) for the status."""

            if not hasattr(self, "_date"):
                self._date = Doc.get_text(self.__node.find("StatusDate"), "")
            return self._date

        @property
        def entered_by(self):
            """User name for the account used to record the status."""

            if not hasattr(self, "_entered_by"):
                self._entered_by = Doc.get_text(self.__node.find("EnteredBy"))
            return self._entered_by

        @property
        def in_scope(self):
            """True if this status block should be included on the report."""

            if not hasattr(self, "_in_scope"):
                self._in_scope = True
                if self.__control.status:
                    if self.value not in self.__control.status:
                        self._in_scope = False
                if self._in_scope and self.__control.start:
                    if not self.date or self.date < str(self.__control.start):
                        self._in_scope = False
                if self._in_scope and self.__control.end:
                    if not self.date or self.date > str(self.__control.end):
                        self._in_scope = False
            return self._in_scope

        @property
        def value(self):
            """The status value string selected for this status."""

            if not hasattr(self, "_value"):
                node = self.__node.find("ProcessingStatusValue")
                self._value = Doc.get_text(node)
            return self._value


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
