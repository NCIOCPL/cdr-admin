#!/usr/bin/env python

"""Report listing summaries containing specified markup.
"""

from datetime import date
from cdrcgi import Controller, Reporter, bail
from cdrapi import db
from cdrapi.docs import Doc


class Control(Controller):
    """Top-level logic for the report."""

    TYPES = "publish", "approved", "proposed", "rejected"
    SUBTITLE = "Drug Summaries with Markup"
    DOCTYPE = "DrugInformationSummary"
    TODAY = date.today().strftime("%B %d, %Y")

    def build_tables(self):
        if not self.types:
            self.show_form()
        cols = ["ID", "Summary"]
        for markup_type in self.TYPES:
            if markup_type in self.types:
                cols.append(markup_type.title())
        query = db.Query("query_term t", "t.doc_id", "t.value").unique()
        query.join("query_term a", "a.doc_id = t.doc_id")
        query.where(f"t.path = '/{self.DOCTYPE}/Title'")
        query.where(f"a.path = '/{self.DOCTYPE}/DrugInfoMetaData/Audience'")
        query.where("a.value = 'Patients'")
        rows = query.order("t.value").execute(self.cursor).fetchall()
        summaries = [Summary(self, *row) for row in rows]
        rows = [summary.row for summary in summaries if summary.in_scope]
        return Reporter.Table(rows, columns=cols, caption=self.caption)

    def populate_form(self, page):
        """Add the fields to the form.

        Pass:
            page - HTMLPage object to which the fields are attached.
        """

        fieldset = page.fieldset("Type of mark-up to Include")
        for value in self.TYPES:
            fieldset.append(page.checkbox("type", value=value, checked=True))
        page.form.append(fieldset)

    @property
    def caption(self):
        """Display string for the top of the report's table."""
        return f"Count of Revision Level Markup - {date.today()}"

    @property
    def types(self):
        "User-selected types, validated and sorted correctly."""
        if not hasattr(self, "_types"):
            types = self.fields.getlist("type")
            for markup_type in types:
                if markup_type not in self.TYPES:
                    bail()
            self._types = [t for t in self.TYPES if t in types]
        return self._types


class Summary:
    """Information about a PDQ Cancer Information Summary document."""

    TAGS = "Insertion", "Deletion"
    URL = "QcReport.py?DocId=CDR{}&Session=guest&DocVersion=-1"

    def __init__(self, control, doc_id, title):
        """Assemble the counts needed for the report."""

        self.__control = control
        self.__id = doc_id
        self.__title = title
        self.__counts = {}
        for markup_type in control.TYPES:
            self.__counts[markup_type] = 0
        doc = Doc(control.session, id=doc_id)
        for tag in self.TAGS:
            for node in doc.root.iter(tag):
                self.__counts[node.get("RevisionLevel")] += 1

    @property
    def id(self):
        """Unique ID for the summary document."""
        return self.__id

    @property
    def title(self):
        """Summary document's title."""
        return self.__title

    @property
    def row(self):
        """Assemble the report row for this summary."""
        if not hasattr(self, "_row"):
            self._row = [self.link, self.title]
            for markup_type in self.__control.types:
                count = self.__counts[markup_type]
                if count:
                    self._row.append(Reporter.Cell(count, center=True))
                else:
                    self._row.append("")
        return self._row

    @property
    def link(self):
        """Cell containing a link to the QC report for this summary."""
        url = self.URL.format(self.id)
        return Reporter.Cell(self.id, href=url, center=True)

    @property
    def in_scope(self):
        """Does this have any reportable markup?"""
        for markup_type in self.__control.types:
            if self.__counts[markup_type]:
                return True
        return False


if __name__ == "__main__":
    """Don't run if this script is loaded as a module."""
    Control().run()
