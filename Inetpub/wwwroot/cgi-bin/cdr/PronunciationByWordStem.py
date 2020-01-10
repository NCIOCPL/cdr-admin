#!/usr/bin/env python

"""Show glossary term matching a name or pronunciation stem.

"The Glossary Terms by Status Report will list terms and their
pronunciations by the user requesting a specific word stem from
the Glossary Term name or Term Pronunciation." (request 2643)
"""

from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Report logic."""

    SUBTITLE = "Pronunciation by Term Stem Report"
    NAME_PATH = "/GlossaryTermName/TermName/TermNameString"
    PRON_PATH = "/GlossaryTermName/TermName/TermPronunciation"

    def populate_form(self, page):
        """Give the user two ways to identify glossary terms.

        Pass:
            page - HTMLPage object on which to place the fields
        """

        fieldset = page.fieldset("Enter a term or pronunciation word stem")
        fieldset.append(page.text_field("term_stem"))
        fieldset.append(page.text_field("pron_stem"))
        page.form.append(fieldset)

    def build_tables(self):
        """Return the single row for this report."""
        return self.table

    @property
    def caption(self):
        """Caption string(s) for the report's table."""

        if not hasattr(self, "_caption"):
            name = self.fields.getvalue("term_stem")
            pron = self.fields.getvalue("pron_stem")
            self._caption = []
            if name:
                self._caption.append(f"Name Stem: {name}")
            if pron:
                self._caption.append(f"Pronunciation Stem: {pron}")
        return self._caption

    @property
    def columns(self):
        """Column header definitions for the report."""

        return (
            self.Reporter.Column("Doc ID", width="75px"),
            self.Reporter.Column("Term Name", width="300px"),
            self.Reporter.Column("Pronunciation", width="350px"),
            self.Reporter.Column("Pronunciation Resource", width="200px"),
            self.Reporter.Column("Comments", width="500px"),
        )

    @property
    def pron_stem(self):
        """Substring for matching glossary term pronunciations."""

        if not hasattr(self, "_pron_stem"):
            self._pron_stem = self.fields.getvalue("pron_stem", "").strip()
            if self._pron_stem and "%" not in self._pron_stem:
                self._pron_stem = f"%{self._pron_stem}%"
        return self._pron_stem

    @property
    def term_stem(self):
        """Substring for matching glossary term names."""

        if not hasattr(self, "_term_stem"):
            self._term_stem = self.fields.getvalue("term_stem", "").strip()
            if self._term_stem and "%" not in self._term_stem:
                self._term_stem = f"%{self._term_stem}%"
        return self._term_stem

    @property
    def rows(self):
        """Table rows for the report."""

        if not hasattr(self, "_rows"):
            self._rows = [term.row for term in self.terms]
        return self._rows

    @property
    def table(self):
        """This report has a single table."""

        if not hasattr(self, "_table"):
            opts = dict(caption=self.caption, columns=self.columns)
            self._table = self.Reporter.Table(self.rows, **opts)
        return self._table

    @property
    def terms(self):
        """Terms matching the word stem."""

        if not hasattr(self, "_terms"):
            query = self.Query("query_term", "doc_id")
            if self.term_stem:
                query.where(f"path = '{self.NAME_PATH}'")
                query.where(query.Condition("value", self.term_stem, "LIKE"))
            if self.pron_stem:
                query.where(f"path = '{self.PRON_PATH}'")
                query.where(query.Condition("value", self.pron_stem, "LIKE"))
            self._terms = []
            for row in query.execute(self.cursor).fetchall():
                self._terms.append(Term(self, row.doc_id))
        return self._terms


class Term:
    """Glossary term information for the report."""

    CLASSES = dict(
        Insertion="insertion",
        Deletion="deletion",
        Strong="strong",
        Emphasis="emphasis",
        ScientificName="emphasis",
    )

    def __init__(self, control, id):
        """Capture the caller's values.

        Pass:
            control - access to the database and reporting
        """

        self.__control = control
        self.__id = id

    def make_span(self, node):
        """Create a wrapper for the contents of a report table cell.

        Works through the node's tree recursively, setting classes
        to control display effects.

        Pass:
            node - parsed XML document node to be rolled into a wrapper

        Return:
            HTML span element object (or None if no content)
        """

        if node is None:
            return None
        segments = []
        text = []

        # Special handling for comments, to get their user and date info.
        if node.tag == "Comment":
            user = node.get("user")
            date = node.get("date")
            if user:
                text.append(f"[user={user}]")
            if date:
                text.append(f"[date={date}]")
        if node.text is not None and node.text:
            text.append(node.text)
        if text:
            segments.append(" ".join(text))

        # Recurse through all the child nodes.
        for child in node.findall("*"):
            span = self.make_span(child)
            if span is not None:
                segments.append(span)
            if child.tail is not None and child.tail:
                segments.append(child.tail)
        if not segments:
            return None

        # Roll the segments into a single span element and set styling.
        span = self.control.HTMLPage.B.SPAN(*segments)
        span_class = self.CLASSES.get(node.tag)
        if span_class:
            span.set("class", span_class)
        return span

    @property
    def comment(self):
        """Node for the first comment found for the English term name."""

        if not hasattr(self, "_comment"):
            self._comment = self.doc.root.find("TermName/Comment")
        return self._comment

    @property
    def control(self):
        """Access to the database and reporting."""
        return self.__control

    @property
    def doc(self):
        """The `Doc` object for this glossary term name."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.control.session, id=self.id)
        return self._doc

    @property
    def id(self):
        """Document ID for the glossary term name document."""
        return self.__id

    @property
    def name(self):
        """Node for the document's English name."""

        if not hasattr(self, "_name"):
            self._name = self.doc.root.find("TermName/TermNameString")
        return self._name

    @property
    def pronunciation(self):
        """Node for the document's English pronunciation."""

        if not hasattr(self, "_pron"):
            self._pron = self.doc.root.find("TermName/TermPronunciation")
        return self._pron

    @property
    def resource(self):
        """Node for the document's English pronunciation."""

        if not hasattr(self, "_resource"):
            path = "TermName/PronunciationResource"
            self._resource = self.doc.root.find(path)
        return self._resource

    @property
    def row(self):
        """Row for the report table."""

        if not hasattr(self, "_row"):
            Cell = self.control.Reporter.Cell
            self._row = (
                Cell(self.id, center=True),
                Cell(self.make_span(self.name)),
                Cell(self.make_span(self.pronunciation)),
                Cell(self.make_span(self.resource)),
                Cell(self.make_span(self.comment)),
            )
        return self._row


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
