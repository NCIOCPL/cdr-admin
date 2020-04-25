#!/usr/bin/env python

"""Report documents last modified during a specified time period.
"""

import datetime
from cdrcgi import Controller

class Control(Controller):
    """Top-level report logic."""

    SUBTITLE = "Date Last Modified"
    COLUMNS = (
        ("Date Last Modified", "100px"),
        ("CDR ID", "150px"),
        ("Document Title", "500px"),
    )

    def build_tables(self):
        """Create the table (or tables) for the report."""

        if isinstance(self.doctype, self.Doctype):
            return self.doctype.table
        tables = []
        for doctype in self.doctype:
            if doctype.docs:
                tables.append(doctype.table)
        if not tables:
            self.bail("No documents match the selected date range")
        return tables

    def populate_form(self, page):
        """Ask the user for the report parameters.

        Pass:
            page - HTMLPage object on which we place the fields
        """

        fieldset = page.fieldset("Select Document Type")
        opts = dict(value="all_types", checked=True)
        fieldset.append(page.radio_button("doctype", **opts))
        doctypes = sorted(self.doctypes.items(), key=lambda t:t[1].lower())
        for value, label in doctypes:
            opts = dict(value=value, label=label)
            fieldset.append(page.radio_button("doctype", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Date Range For Report")
        fieldset.append(page.date_field("start", value=self.range.start))
        fieldset.append(page.date_field("end", value=self.range.end))
        page.form.append(fieldset)
        page.add_output_options(default="html")

    @property
    def columns(self):
        """Column headers shared by all the tables."""

        if not hasattr(self, "_columns"):
            self._columns = []
            for label, width in self.COLUMNS:
                self._columns.append(self.Reporter.Column(label, width=width))
        return self._columns

    @property
    def doctype(self):
        """The `Doctype` object(s) for the types selected by the user."""

        if not hasattr(self, "_doctype"):
            doctype = self.fields.getvalue("doctype")
            if doctype.isdigit():
                name = self.doctypes[int(doctype)]
                self._doctype = self.Doctype(self, doctype, name)
            else:
                items = list(self.doctypes.items())
                doctypes = sorted(items, key=lambda t:t[1].lower())
                self._doctype = []
                for id, name in doctypes:
                    self._doctype.append(self.Doctype(self, id, name))
        return self._doctype

    @property
    def doctypes(self):
        """Dictionary of active CDR document types, indexed by ID."""

        if not hasattr(self, "_doctypes"):
            query = self.Query("doc_type t", "t.id", "t.name")
            query.where("active = 'Y'")
            names = {}
            for row in query.execute(self.cursor):
                if row.name.strip():
                    names[row.name] = row.id
            query = self.Query("query_term", "path").unique()
            query.where("path LIKE '%/DateLastModified'")
            query.where("int_val IS NOT NULL")
            self._doctypes = {}
            for row in query.execute(self.cursor):
                name = row.path.strip("/").split("/")[0]
                id = names.get(name)
                if id:
                    self._doctypes[id] = name
        return self._doctypes

    @property
    def end(self):
        """Ending date for the report's date range."""

        if not hasattr(self, "_end"):
            self._end = self.fields.getvalue("end")
        return self._end

    @property
    def range(self):
        """Default date range for report."""

        if not hasattr(self, "_range"):
            today = datetime.date.today()
            start = today - datetime.timedelta(7)
            class Range:
                def __init__(self, start, end):
                    self.start = start
                    self.end = end
            self._range = Range(start, today)
        return self._range

    @property
    def start(self):
        """Starting date for the report's date range."""

        if not hasattr(self, "_start"):
            self._start = self.fields.getvalue("start")
        return self._start

    @property
    def subtitle(self):
        if not hasattr(self, "_subtitle"):
            subtitle = self.SUBTITLE
            if self.request == "Submit":
                if self.start:
                    if self.end:
                        subtitle = f"{subtitle} ({self.start} to {self.end})"
                    else:
                        subtitle = f"{subtitle} (since {self.start})"
                elif self.end:
                    subtitle = f"{subtitle} (through {self.end})"
            self._subtitle = subtitle
        return self._subtitle

    @property
    def title(self):
        """Override for the Excel version of the report."""
        if self.request == "Submit" and self.format == "excel":
            return self.SUBTITLE
        return self.TITLE


    class Doctype:
        """Collect information about docs of this document type."""

        def __init__(self, control, id, name):
            """Capture the caller's values."""

            self.__control = control
            self.__id = id
            self.__name = name

        @property
        def control(self):
            """Access to the database and the report options."""
            return self.__control

        @property
        def docs(self):
            """Sequence of `Doc` objects for the report."""

            if not hasattr(self, "_docs"):
                fields = "MAX(m.value) AS last_mod", "d.id", "d.title"
                query = self.control.Query("query_term m", *fields).unique()
                query.join("document d", "d.id = m.doc_id")
                if self.start:
                    query.where(query.Condition("m.value", self.start, ">="))
                if self.end:
                    query.where(query.Condition("m.value", self.end, "<="))
                query.where(query.Condition("m.path", self.path, "LIKE"))
                query.order("MAX(m.value)", "d.id")
                query.group("d.id", "d.title")
                rows = query.execute(self.control.cursor).fetchall()
                self._docs = [self.Doc(self.control, row) for row in rows]
            return self._docs

        @property
        def end(self):
            """Ending date/time for the report's date range."""
            return f"{self.control.end} 23:59:59"

        @property
        def name(self):
            """String for the document type's name."""
            return self.__name

        @property
        def path(self):
            """Pattern string for searching the query_term table."""
            return f"/{self.name}/%DateLastModified"

        @property
        def start(self):
            """Starting date for the report's date range."""
            return self.control.start

        @property
        def table(self):
            """`Table` object for this document type."""

            if not hasattr(self, "_table"):
                rows = [doc.row for doc in self.docs]
                opts = dict(columns=self.control.columns, caption=self.name)
                if self.control.format == "excel":
                    opts["sheet_name"] = self.name
                self._table = self.control.Reporter.Table(rows, **opts)
            return self._table


        class Doc:
            """CDR document with its most recent "date last modified" value."""

            def __init__(self, control, row):
                """Save the caller's values."""

                self.__control = control
                self.__row = row

            @property
            def control(self):
                """Access to classes needed to build the row's cells."""
                return self.__control

            @property
            def id(self):
                """Formatter CDR ID."""
                return f"CDR{self.__row.id:010d}"

            @property
            def modified(self):
                """Latest "date last modified" value for the document."""
                return self.__row.last_mod

            @property
            def row(self):
                """Sequence of `Cell` objects for the document's report row."""
                if not hasattr(self, "_row"):
                    self._row = (
                        self.control.Reporter.Cell(self.modified, center=True),
                        self.control.Reporter.Cell(self.id, center=True),
                        self.control.Reporter.Cell(self.title),
                    )
                return self._row

            @property
            def title(self):
                """The CDR document's title."""
                return self.__row.title


if __name__ == "__main__":
    """Don't execute script if loaded as a module."""
    Control().run()
