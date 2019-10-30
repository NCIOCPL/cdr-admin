#!/usr/bin/env python

"""Report on newly created documents and their publication statuses.
"""

import datetime
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

    @property
    def doctypes(self):
        """Sorted sequence of `DoctypeCounts` objects with report counts."""

        if not hasattr(self, "_doctypes"):
            names = self.typenames if self.type == "any" else [self.type]
            self._doctypes = []
            for name in names:
                doctype = Doctype(self, name)
                if doctype.table:
                    self._doctypes.append(doctype)
        return self._doctypes

    @property
    def end(self):
        """String for the end of the report's date range (optional)."""
        return self.fields.getvalue("end")

    @property
    def start(self):
        """String for the start of the report's date range (optional)."""
        return self.fields.getvalue("start")

    @property
    def subtitle(self):
        """Customize the string below the main banner."""

        if not hasattr(self, "_subtitle"):
            if self.request == "Submit":
                if self.type == "any":
                    self._subtitle = "New Documents"
                else:
                    self._subtitle = f"New {self.type} Documents"
                start, end = self.start, self.end
                if start:
                    if end:
                        self._subtitle += f" Created Between {start} and {end}"
                    else:
                        self._subtitle += f" Created Since {start}"
                elif self.end:
                    self._subtitle += f" Created Through {end}"
            else:
                self._subtitle = self.SUBTITLE
        return self._subtitle

    @property
    def type(self):
        """Selected document type for the report (or "any")."""
        return self.fields.getvalue("type")

    @property
    def typenames(self):
        """Document type names for the form's picklist."""

        if not hasattr(self, "_typenames"):
            self._typenames = []
            for name in cdrapi.docs.Doctype.list_doc_types(self.session):
                if name:
                    self._typenames.append(name)
        return self._typenames


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

    def __init__(self, control, name):
        """Capture the caller's values.

        Pass:
            control - access to the database
            name - string for this document type's name
        """

        self.__control = control
        self.__name = name

    @property
    def control(self):
        """Access to the database."""
        return self.__control

    @property
    def docs(self):
        """New documents of this type."""

        if not hasattr(self, "_docs"):
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
            self._docs = [Doc(self.control, row) for row in rows]
        return self._docs

    @property
    def name(self):
        """String for this document type's name."""
        return self.__name

    @property
    def table(self):
        """Table of new documents (or None if there aren't any)."""

        if not hasattr(self, "_table"):
            self._table = None
            if self.docs:
                opts = dict(caption=self.name, columns=self.COLUMNS)
                rows = [doc.row for doc in self.docs]
                self._table = Reporter.Table(rows, **opts)
        return self._table


class Doc:
    """Publication and version information about a newly created CDR doc."""

    def __init__(self, control, row):
        """Save the caller's values.

        Pass:
            control - access to the database
            row - row from the `docs_with_pub_status` view
        """

        self.__control = control
        self.__row = row

    def __getattr__(self, name):
        """Pull most properties from the database row."""
        return getattr(self.__row, name)

    @property
    def control(self):
        """Access to the database."""
        return self.__control

    @property
    def row(self):
        """Table row for the report."""

        if not hasattr(self, "_row"):
            ver_date = str(self.ver_date)[:10] if self.ver_date else ""
            self._row = (
                Reporter.Cell(self.doc_id, center=True),
                self.doc_title,
                Reporter.Cell(self.cre_user, center=True),
                Reporter.Cell(str(self.cre_date)[:10], center=True),
                Reporter.Cell(ver_date, center=True),
                Reporter.Cell(self.ver_user, center=True),
                Reporter.Cell(self.pv, center=True),
                Reporter.Cell("Y" if self.epv else "N", center=True),
            )
        return self._row


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
