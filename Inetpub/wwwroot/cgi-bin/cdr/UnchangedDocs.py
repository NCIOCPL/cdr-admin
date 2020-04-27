#!/usr/bin/env python

"""Report on documents unchanged for a specified number of days.
"""

from cdrcgi import Controller
import datetime


class Control(Controller):
    """Access to the database and form/report building tools."""

    SUBTITLE = "Unchanged Documents"

    def build_tables(self):
        """Assemble the table for the report."""

        opts = dict(caption=self.caption, columns=self.columns)
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Ask for the information we'll need for the report.

        Pass:
            page - HTMLPage object where the fields go
        """

        fieldset = page.fieldset("Report Parameters")
        fieldset.append(page.text_field("days", label="Age", value="365"))
        options = ["all"] + self.doctypes
        opts = dict(label="Doc Type", options=options)
        fieldset.append(page.select("doctype", **opts))
        fieldset.append(page.text_field("max", label="Max Rows", value="1000"))
        page.form.append(fieldset)

    @property
    def caption(self):
        """String to display above the table."""

        args = self.days, self.today
        caption = "Documents Unchanged for {} Days as of {}".format(*args)
        if self.doctype and self.doctype != "all":
            caption = f"{self.doctype} {caption}"
        return caption

    @property
    def columns(self):
        """Column headers for the report table."""

        return (
            self.Reporter.Column("Doc ID"),
            self.Reporter.Column("Doc Title"),
            self.Reporter.Column("Last Change"),
        )

    @property
    def cutoff(self):
        """How far back the report should go."""

        if not hasattr(self, "_cutoff"):
            self._cutoff = self.today - datetime.timedelta(self.days)
        return self._cutoff

    @property
    def days(self):
        """How far back the report should go."""

        if not hasattr(self, "_days"):
            try:
                self._days = int(self.fields.getvalue("days"))
            except:
                self._days = 365
        return self._days

    @property
    def docs(self):
        """Unchanged document to be displayed for the report."""

        if not hasattr(self, "_docs"):
            fields = "d.id", "d.title", "MAX(a.dt) AS last_saved"
            query = self.Query("document d", *fields).order("d.title", "d.id")
            query.join("audit_trail a", "a.document = d.id")
            query.group("d.id", "d.title")
            query.having(query.Condition("MAX(a.dt)", self.cutoff, ">="))
            query.limit(self.max)
            if self.doctype and self.doctype != "all":
                query.join("doc_type t", "t.id = d.doc_type")
                query.where(query.Condition("t.name", self.doctype))
            rows = query.execute(self.cursor).fetchall()
            self._docs = [self.Doc(row) for row in rows]
        return self._docs

    @property
    def doctype(self):
        """Document type selected from the form."""
        return self.fields.getvalue("doctype")

    @property
    def doctypes(self):
        """Sorted sequence of the document type names for the picklist."""

        if not hasattr(self, "_doctypes"):
            query = self.Query("doc_type", "name").order("name")
            query.where("name IS NOT NULL")
            query.where("name <> ''")
            query.where("active = 'Y'")
            self._doctypes = [row.name for row in query.execute(self.cursor)]
        return self._doctypes

    @property
    def max(self):
        """Throttle on the number of documents to show."""

        if not hasattr(self, "_max"):
            try:
                self._max = int(self.fields.getvalue("max"))
            except:
                self._max  = 1000
        return self._max

    @property
    def rows(self):
        """Data rows for the report table."""

        if not hasattr(self, "_rows"):
            self._rows = [doc.row for doc in self.docs]
        return self._rows

    @property
    def today(self):
        """Date of the report."""

        if not hasattr(self, "_today"):
            self._today = datetime.date.today()
        return self._today


    class Doc:
        def __init__(self, row):
            """Remember the database values passed by the caller.

            Pass:
                row - result set row from the database query
            """

            self.__row = row

        @property
        def id(self):
            """CDR ID of the document."""

            if not hasattr(self, "_id"):
                self._id = f"CDR{self.__row.id:010d}"
            return self.__row.id

        @property
        def last_change(self):
            """Date of the last save."""

            if not hasattr(self, "_last_change"):
                self._last_change = str(self.__row.last_saved)[:10]
            return self._last_change

        @property
        def row(self):
            """Values for the report table."""
            return self.id, self.title, self.last_change

        @property
        def title(self):
            """Title of the document, possibly shortened for the report."""

            if not hasattr(self, "_title"):
                self._title = self.__row.title[:100]
                if len(self.__row.title) > 100:
                    self._title = f"{self._title} ..."
            return self._title


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
