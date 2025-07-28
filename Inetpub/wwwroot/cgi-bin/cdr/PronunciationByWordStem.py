#!/usr/bin/env python

"""Show glossary term matching a name or pronunciation stem.

"The Glossary Terms by Status Report will list terms and their
pronunciations by the user requesting a specific word stem from
the Glossary Term name or Term Pronunciation." (request 2643)
"""

from functools import cached_property
from cdrcgi import Controller, BasicWebPage
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
        opts = dict(label="Pronunciation Stem")
        fieldset.append(page.text_field("pron_stem", **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Return the single row for this report."""
        """Overridden because the table is too wide for the standard layout."""

        report = BasicWebPage()
        report.wrapper.append(report.B.H1(self.subtitle))
        report.wrapper.append(self.table.node)
        report.wrapper.append(self.footer)
        report.send()

    @cached_property
    def caption(self):
        """Caption string(s) for the report's table."""

        name = self.fields.getvalue("term_stem")
        pron = self.fields.getvalue("pron_stem")
        caption = []
        if name:
            caption.append(f"Name Stem: {name}")
        if pron:
            caption.append(f"Pronunciation Stem: {pron}")
        return caption

    @cached_property
    def columns(self):
        """Column header definitions for the report."""

        return (
            self.Reporter.Column("Doc ID", width="75px"),
            self.Reporter.Column("Term Name", width="300px"),
            self.Reporter.Column("Pronunciation", width="350px"),
            self.Reporter.Column("Pronunciation Resource", width="200px"),
            self.Reporter.Column("Comments", width="500px"),
        )

    @cached_property
    def pron_stem(self):
        """Substring for matching glossary term pronunciations."""

        pron_stem = self.fields.getvalue("pron_stem", "").strip()
        if pron_stem and "%" not in pron_stem:
            return f"%{pron_stem}%"
        return pron_stem

    @cached_property
    def term_stem(self):
        """Substring for matching glossary term names."""

        term_stem = self.fields.getvalue("term_stem", "").strip()
        if term_stem and "%" not in term_stem:
            return f"%{term_stem}%"
        return term_stem

    @cached_property
    def rows(self):
        """Table rows for the report."""
        return [term.row for term in self.terms]

    @cached_property
    def table(self):
        """This report has a single table."""

        opts = dict(caption=self.caption, columns=self.columns)
        return self.Reporter.Table(self.rows, **opts)

    @cached_property
    def terms(self):
        """Terms matching the word stem."""

        query = self.Query("query_term", "doc_id")
        if self.term_stem:
            query.where(f"path = '{self.NAME_PATH}'")
            query.where(query.Condition("value", self.term_stem, "LIKE"))
        if self.pron_stem:
            query.where(f"path = '{self.PRON_PATH}'")
            query.where(query.Condition("value", self.pron_stem, "LIKE"))
        terms = []
        for row in query.execute(self.cursor).fetchall():
            terms.append(Term(self, row.doc_id))
        return terms

    @cached_property
    def wide_css(self):
        """Give the report some extra space."""
        return self.Reporter.Table.WIDE_CSS


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

        self.control = control
        self.id = id

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

    @cached_property
    def comment(self):
        """Node for the first comment found for the English term name."""
        return self.doc.root.find("TermName/Comment")

    @cached_property
    def doc(self):
        """The `Doc` object for this glossary term name."""
        return Doc(self.control.session, id=self.id)

    @cached_property
    def name(self):
        """Node for the document's English name."""
        return self.doc.root.find("TermName/TermNameString")

    @cached_property
    def pronunciation(self):
        """Node for the document's English pronunciation."""
        return self.doc.root.find("TermName/TermPronunciation")

    @cached_property
    def resource(self):
        """Node for the document's English pronunciation."""
        return self.doc.root.find("TermName/PronunciationResource")

    @cached_property
    def row(self):
        """Row for the report table."""

        Cell = self.control.Reporter.Cell
        return (
            Cell(self.id, center=True),
            Cell(self.make_span(self.name)),
            Cell(self.make_span(self.pronunciation)),
            Cell(self.make_span(self.resource)),
            Cell(self.make_span(self.comment)),
        )


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
