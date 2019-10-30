#!/usr/bin/env python

"""Show published Glossary Term Name documents.

"We need a New Published Glossary Terms Report which will serve as a
QC report to verify which new Glossary Term Name documents have been
published within the given time frame.  We would like a new Mailer
report so we can track responses easier."
"""

import datetime
from cdrcgi import Controller


class Control(Controller):
    """Access to the database and report-building facilities."""

    SUBTITLE = "New Published Glossary Terms"
    COLUMNS = (
        ("CDR ID", "75px"),
        ("Term Name (English)", "300px"),
        ("Term Name (Spanish)", "300px"),
        ("Date First Published", "100px"),
    )

    def build_tables(self):
        """Assemble and return the report's table."""

        opts = dict(caption=self.caption, columns=self.columns)
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Ask the user for the report parameters.

        Pass:
            page - HTMLPage object on which to place the form fields
        """

        end = datetime.date.today()
        start = end - datetime.timedelta(7)
        fieldset = page.fieldset("Report Parameters")
        opts = dict(label="Start Date", value=start)
        fieldset.append(page.date_field("start", **opts))
        opts = dict(label="End Date", value=end)
        fieldset.append(page.date_field("end", **opts))
        page.form.append(fieldset)

    @property
    def caption(self):
        """What we display at the top of the report's table."""
        return f"{len(self.rows)} Newly Published Glossary Term Documents"

    @property
    def columns(self):
        """Column headers displayed at the top of the report table."""

        cols = []
        for label, width in self.COLUMNS:
            cols.append(self.Reporter.Column(label, width=width))
        return cols

    @property
    def end(self):
        return self.fields.getvalue("end")

    @property
    def format(self):
        """Override the default report format so we get an Excel workbook."""
        return "excel"

    @property
    def rows(self):
        """Values for the report table."""

        if not hasattr(self, "_rows"):
            self._rows = [term.row for term in self.terms]
        return self._rows

    @property
    def start(self):
        return self.fields.getvalue("start")

    @property
    def terms(self):
        """Values for the report table."""

        query = self.Query("document d", "d.id", "d.first_pub").order("d.id")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'GlossaryTermName'")
        query.where("d.first_pub IS NOT NULL")
        query.where("d.active_status = 'A'")
        if self.start:
            query.where(query.Condition("d.first_pub", self.start, ">="))
        if self.end:
            end = f"{self.end} 23:59:59"
            query.where(query.Condition("d.first_pub", end, "<="))
        rows = query.execute(self.cursor).fetchall()
        return [TermName(self, row) for row in rows]


class TermName:
    """GlossaryTermName document published in the report's date range."""

    def __init__(self, control, row):
        """Remember the caller's values.

        Pass:
            control - access to the database and report-generation tools
            row - resultset row from the database query
        """

        self.__control = control
        self.__row = row

    @property
    def english_name(self):
        """The primary English name for the glossary term."""

        query = self.__control.Query("query_term", "value")
        query.where("path = '/GlossaryTermName/TermName/TermNameString'")
        query.where(query.Condition("doc_id", self.id))
        return query.execute(self.__control.cursor).fetchall()[0].value

    @property
    def first_pub(self):
        """Date the document was first published."""
        return str(self.__row.first_pub)[:10]

    @property
    def id(self):
        """Primary key from the all_docs table for the document."""
        return self.__row.id

    @property
    def row(self):
        """Values for the report's table."""
        return (
            self.__control.Reporter.Cell(self.id, center=True),
            self.english_name,
            self.spanish_names,
            self.__control.Reporter.Cell(self.first_pub, center=True),
        )

    @property
    def spanish_names(self):
        """Concatenated list of all the Spanish names for this term."""

        query = self.__control.Query("query_term", "value")
        query.where("path = '/GlossaryTermName/TranslatedName/TermNameString'")
        query.where(query.Condition("doc_id", self.id))
        rows = query.execute(self.__control.cursor).fetchall()
        return "; ".join([row.value for row in rows])


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
