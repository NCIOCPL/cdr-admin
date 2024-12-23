#!/usr/bin/env python

"""Report on documents unchanged for a specified number of days.
"""

from functools import cached_property
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

    @cached_property
    def caption(self):
        """String to display above the table."""

        args = self.days, self.today
        caption = "Documents Unchanged for {} Days as of {}".format(*args)
        if self.doctype and self.doctype != "all":
            caption = f"{self.doctype} {caption}"
        return caption

    @cached_property
    def columns(self):
        """Column headers for the report table."""

        return (
            self.Reporter.Column("Doc ID"),
            self.Reporter.Column("Doc Title"),
            self.Reporter.Column("Last Change"),
        )

    @cached_property
    def cutoff(self):
        """How far back the report should go."""
        return self.today - datetime.timedelta(self.days)

    @cached_property
    def days(self):
        """How far back the report should go."""

        try:
            return int(self.fields.getvalue("days"))
        except Exception:
            return 365

    @cached_property
    def docs(self):
        """Unchanged documents to be displayed for the report."""

        fields = "d.id", "d.title", "MAX(a.dt) AS last_saved"
        query = self.Query("document d", *fields).order("d.title", "d.id")
        query.join("audit_trail a", "a.document = d.id")
        query.group("d.id", "d.title")
        query.having(query.Condition("MAX(a.dt)", self.cutoff, "<"))
        query.limit(self.max)
        if self.doctype and self.doctype != "all":
            query.join("doc_type t", "t.id = d.doc_type")
            query.where(query.Condition("t.name", self.doctype))
        rows = query.execute(self.cursor).fetchall()
        return [self.Doc(row) for row in rows]

    @cached_property
    def doctype(self):
        """Document type selected from the form."""
        return self.fields.getvalue("doctype")

    @cached_property
    def doctypes(self):
        """Sorted sequence of the document type names for the picklist."""

        query = self.Query("doc_type", "name").order("name")
        query.where("name IS NOT NULL")
        query.where("name <> ''")
        query.where("active = 'Y'")
        return [row.name for row in query.execute(self.cursor)]

    @cached_property
    def max(self):
        """Throttle on the number of documents to show."""

        try:
            return int(self.fields.getvalue("max"))
        except Exception:
            return 1000

    @cached_property
    def rows(self):
        """Data rows for the report table."""
        return [doc.row for doc in self.docs]

    @cached_property
    def today(self):
        """Date of the report."""
        return datetime.date.today()

    class Doc:
        def __init__(self, row):
            """Remember the database values passed by the caller.

            Pass:
                row - result set row from the database query
            """

            self.__row = row

        @cached_property
        def id(self):
            """CDR ID of the document."""
            return f"CDR{self.__row.id:010d}"

        @cached_property
        def last_change(self):
            """Date of the last save."""
            return str(self.__row.last_saved)[:10]

        @cached_property
        def row(self):
            """Values for the report table."""
            return self.id, self.title, self.last_change

        @cached_property
        def title(self):
            """Title of the document, possibly shortened for the report."""

            title = self.__row.title
            return f"{title[:75]} ..." if len(title) > 80 else title


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
