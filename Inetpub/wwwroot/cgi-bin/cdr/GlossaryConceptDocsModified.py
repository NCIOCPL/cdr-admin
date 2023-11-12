#!/usr/bin/env python

"""Show which glossary concept documents have changed recently.

"The Glossary Term Concept - Documents Modified Report will serve as a
QC report to verify which documents were changed within a given time
frame. The report will be separated into English and Spanish.
New 'documents modified' reports for restructured glossary documents."
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc
import datetime
from openpyxl.styles import Alignment


class Control(Controller):
    """Access to database, session, and report/form building."""

    SUBTITLE = "GTC Documents Modified Report"
    AUDIENCES = ("Patient", "Health professional")
    LANGUAGES = (("en", "English"), ("es", "Spanish"))

    def build_tables(self):
        """Assemble the table for the report."""

        opts = dict(columns=self.columns, sheet_name="Glossary Term Concepts")
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Put up the CGI form fields with defaults and instructions.

        Pass:
            page - HTMLPage object with which the form is built
        """

        end = datetime.date.today()
        start = end - datetime.timedelta(7)
        fieldset = page.fieldset("Date Range")
        fieldset.append(page.date_field("start_date", value=start))
        fieldset.append(page.date_field("end_date", value=end))
        page.form.append(fieldset)
        fieldset = page.fieldset("Language")
        checked = True
        for value, label in self.LANGUAGES:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("language", **opts))
            checked = False
        page.form.append(fieldset)
        fieldset = page.fieldset("Audience")
        checked = True
        for audience in self.AUDIENCES:
            opts = dict(value=audience, checked=checked)
            fieldset.append(page.radio_button("audience", **opts))
            checked = False
        page.form.append(fieldset)
        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(
            "Specify the date range for the versions to be examined "
            "for the report. The required language and audience choices "
            "determine which comments will be included in the report. "
            "This report is generated as an Excel workbook, directly "
            "downloaded to your workstation."
        ))
        page.form.append(fieldset)

    @cached_property
    def audience(self):
        """Audience for the report."""
        return self.fields.getvalue("audience")

    @cached_property
    def audience_display(self):
        """Audience display for the comment column."""

        display = {'Patient': 'PT', 'Health professional': 'HP'}
        return display[self.audience]

    @cached_property
    def columns(self):
        """Column headers for the report."""

        return (
            self.Reporter.Column("CDR ID", width="70px"),
            self.Reporter.Column("Date Last Modified", width="100px"),
            self.Reporter.Column("Publishable?", width="100px"),
            self.Reporter.Column("Date First Published (*)", width="100px"),
            self.Reporter.Column(f"Last {self.audience_display} Comment",
                                 width="450px")
        )

    @cached_property
    def docs(self):
        """GlossaryTermConcept documents to be included in this report."""

        query = self.Query("doc_version v", "v.id", "MAX(v.num) as num")
        query.join("doc_type t", "t.id = v.doc_type")
        query.join("document d", "d.id = v.id")
        query.where("d.active_status = 'A'")
        query.where("t.name = 'GlossaryTermConcept'")
        if self.start:
            query.where(query.Condition("v.dt", str(self.start), ">="))
        if self.end:
            query.where(query.Condition("v.dt", f"{self.end} 23:59:59", "<="))
        query.group("v.id")
        rows = query.execute(self.cursor).fetchall()
        docs = [GlossaryTermConcept(self, row) for row in rows]
        return sorted(docs)

    @cached_property
    def end(self):
        """End of the date range for the report."""
        return self.parse_date(self.fields.getvalue("end_date"))

    @cached_property
    def format(self):
        """Override to get an Excel report."""
        return "excel"

    @cached_property
    def language(self):
        """Language code selected for the report (en or es)."""
        return self.fields.getvalue("language")

    @cached_property
    def rows(self):
        """Values for the report's table."""

        note = (
            "(*) Date any GlossaryTermName document linked to the "
            "concept document was first published."
        )
        styles = dict(alignment=Alignment(wrap_text=False))
        note_cell = self.Reporter.Cell(note, sheet_styles=styles)
        return [doc.row for doc in self.docs] + [[note_cell]]

    @property
    def start(self):
        """Beginning of the date range for the report."""
        return self.parse_date(self.fields.getvalue("start_date"))


class GlossaryTermConcept:
    """Information needed for a single row of the report."""

    NAME_PATH = "/GlossaryTermName/GlossaryTermConcept/@cdr:ref"
    DEFINITION_PATHS = dict(
        en="TermDefinition",
        es="TranslatedTermDefinition",
    )

    def __init__(self, control, row):
        """Save the caller's values.

        Pass:
            control - access to the database and report-building tools
            row - results set values from the database query
        """

        self.__control = control
        self.__row = row

    def __lt__(self, other):
        """Support sorting the documents by title."""
        return self.doc.title < other.doc.title

    @cached_property
    def doc(self):
        """`Doc` object for the glossary term concept document."""

        if not hasattr(self, "_doc"):
            opts = dict(id=self.__row.id, version=self.__row.num)
            self._doc = Doc(self.__control.session, **opts)
        return self._doc

    @cached_property
    def comment(self):
        """First comment for the definition selected for the report."""

        if self.definition is not None:
            node = self.definition.find("Comment")
            if node is not None:
                return self.Comment(node)
        return None

    @cached_property
    def date_first_published(self):
        """Date of first publication of any linked term name document."""

        query = self.__control.Query("document d", "MIN(d.first_pub) fp")
        query.join("query_term n", "n.doc_id = d.id")
        query.where(f"n.path = '{self.NAME_PATH}'")
        query.where(query.Condition("n.int_val", self.doc.id))
        row = query.execute(self.__control.cursor).fetchone()
        return str(row.fp)[:10] if row and row.fp else ""

    @cached_property
    def date_last_modified(self):
        """Date the definition for this report was last modified."""

        if self.definition is not None:
            node = self.definition.find("DateLastModified")
            return Doc.get_text(node, "")[:10]
        return ""

    @cached_property
    def definition(self):
        """Definition matching the report's language and audience."""

        path = self.DEFINITION_PATHS[self.__control.language]
        for node in self.doc.root.findall(path):
            audiences = [a.text for a in node.findall("Audience")]
            if self.__control.audience in audiences:
                return node
        return None

    @cached_property
    def publishable(self):
        """String 'Y' or 'N' depending on whether the version is publshable."""
        return "Y" if self.doc.publishable else "N"

    @cached_property
    def row(self):
        "Serialize the concept information to the report table row."

        Cell = self.__control.Reporter.Cell
        return (
            Cell(self.doc.id, center=True),
            Cell(self.date_last_modified, center=True),
            Cell(self.publishable, center=True),
            Cell(self.date_first_published, center=True),
            str(self.comment or ""),
        )

    class Comment:
        "Subclass holding text and metadata for a definition comment"

        def __init__(self, node):
            """Remember the caller's value.

            Pass:
                node - element containing the definition comment
            """

            self.__node = node

        @cached_property
        def text(self):
            """String for the comment text."""
            return Doc.get_text(self.__node)

        @cached_property
        def date(self):
            """String for the date the comment was entered."""
            return self.__node.get("date")

        @cached_property
        def audience(self):
            """String for the audience of the comment (internal or external)"""
            return self.__node.get("audience")

        @cached_property
        def user(self):
            """String for the account name of the user entering the comment."""
            return self.__node.get("user")

        def __str__(self):
            """Serialize the comment's values."""

            args = self.date, self.user, self.audience, self.text
            return "[date: {}; user; {}; audience: {}] {}".format(*args)


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
