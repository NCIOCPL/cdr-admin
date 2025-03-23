#!/usr/bin/env python

"""Report on newly created documents and their publication statuses.
"""

import datetime
from functools import cached_property
from cdrcgi import Controller, Reporter
import cdrapi.docs


class Control(Controller):
    """Report logic."""

    SUBTITLE = "New Documents With Publication Status"

    def populate_form(self, page):
        """Add the fields to the form.

        Pass:
            page - HTMLPage to which we add the fields
        """

        fieldset = page.fieldset("Select Document Type")
        fieldset.append(page.radio_button("type", value="any", checked=True))
        for name in self.typenames:
            fieldset.append(page.radio_button("type", value=name, label=name))
        page.form.append(fieldset)
        fieldset = page.fieldset("Date Range")
        end = datetime.date.today()
        start = end - datetime.timedelta(7)
        fieldset.append(page.date_field("start", value=start))
        fieldset.append(page.date_field("end", value=end))
        page.form.append(fieldset)

    def build_tables(self):
        """Create a table for each selected document type."""
        return [doctype.table for doctype in self.doctypes]

    @cached_property
    def doctypes(self):
        """Sorted sequence of `DoctypeCounts` objects with report counts."""

        names = self.typenames if self.type == "any" else [self.type]
        doctypes = []
        for name in names:
            doctype = Doctype(self, name)
            if doctype.table:
                doctypes.append(doctype)
        return doctypes

    @cached_property
    def end(self):
        """String for the end of the report's date range (optional)."""
        return self.parse_date(self.fields.getvalue("end"))

    @cached_property
    def start(self):
        """String for the start of the report's date range (optional)."""
        return self.parse_date(self.fields.getvalue("start"))

    @cached_property
    def subtitle(self):
        """Customize the string displayed at the top of the page."""

        if self.request != "Submit":
            return self.SUBTITLE
        if self.type == "any":
            docs = "New Documents"
        else:
            docs = f"New {self.type} Documents"
        if self.start:
            if not self.end:
                return f"{docs} Created Since {self.start}"
            en_dash = self.HTMLPage.EN_DASH
            return f"{docs} Created {self.start} {en_dash} {self.end}"
        if self.end:
            return f"{docs} Created Through {self.end}"
        return docs

    @cached_property
    def type(self):
        """Selected document type for the report (or "any")."""
        return self.fields.getvalue("type")

    @cached_property
    def typenames(self):
        """Document type names for the form's picklist."""

        names = []
        for name in cdrapi.docs.Doctype.list_doc_types(self.session):
            if name:
                names.append(name)
        return names

    @cached_property
    def wide_css(self):
        """Give the report more breathing room."""
        return self.Reporter.Table.WIDE_CSS


class Doctype:
    """Collection of newly published documents of a specific type."""

    COLUMNS = (
        Reporter.Column("CDR ID", width="80px"),
        Reporter.Column("Document Title", width="500px"),
        Reporter.Column("Created By", width="150px"),
        Reporter.Column("Creation Date", width="150px"),
        Reporter.Column("Latest Version Date", width="150px"),
        Reporter.Column("Latest Version By", width="150px"),
        Reporter.Column("Pub?", width="50px"),
        Reporter.Column("Earlier Pub Ver?", width="50px"),
    )
    # COLUMNS = [column.name for column in COLUMNS]

    def __init__(self, control, name):
        """Capture the caller's values.

        Pass:
            control - access to the database
            name - string for this document type's name
        """

        self.control = control
        self.name = name

    @cached_property
    def docs(self):
        """New documents of this type."""

        query = self.control.Query("docs_with_pub_status", "*")
        query.order("pv", "cre_date", "ver_date")
        query.where(query.Condition("doc_type", self.name))
        start, end = self.control.start, self.control.end
        if start:
            query.where(query.Condition("cre_date", start, ">="))
        if end:
            end = f"{end} 23:59:59"
            query.where(query.Condition("cre_date", end, "<="))
        rows = query.execute(self.control.cursor).fetchall()
        return [Doc(self.control, row) for row in rows]

    @cached_property
    def table(self):
        """Table of new documents (or None if there aren't any)."""

        if not self.docs:
            return None
        opts = dict(caption=self.name, columns=self.COLUMNS)
        rows = [doc.row for doc in self.docs]
        return Reporter.Table(rows, **opts)


class Doc:
    """Publication and version information about a newly created CDR doc."""

    def __init__(self, control, row):
        """Save the caller's values.

        Pass:
            control - access to the database
            row - row from the `docs_with_pub_status` view
        """

        self.control = control
        self.__row = row

    def __getattr__(self, name):
        """Pull most properties from the database row."""
        return getattr(self.__row, name)

    @cached_property
    def row(self):
        """Table row for the report."""

        ver_date = str(self.ver_date)[:10] if self.ver_date else ""
        return (
            self.doc_id,
            self.doc_title,
            self.cre_user,
            Reporter.Cell(str(self.cre_date)[:10], classes="nowrap"),
            Reporter.Cell(ver_date, classes="nowrap"),
            self.ver_user,
            self.pv,
            "Y" if self.epv else "N",
        )


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
