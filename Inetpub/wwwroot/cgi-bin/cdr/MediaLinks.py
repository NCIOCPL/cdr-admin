#!/usr/bin/env python

"""Report listing all document that link to Media documents
"""

from cdrcgi import Controller


class Control(Controller):

    SUBTITLE = "Documents that Link to Media Documents"
    DOCTYPES = "Glossary Term", "Summary"
    COLUMNS = "CDR ID", "Document Title"

    def populate_form(self, page):
        """Add the fields to the form.

        Pass:
            page - HTMLPage object on whieh the fields are placed
        """

        fieldset = page.fieldset("Select Document Type(s)")
        for doctype in self.DOCTYPES:
            fieldset.append(page.checkbox("type", value=doctype, checked=True))
        page.form.append(fieldset)

    def build_tables(self):
        """Create a separate table for each document type selected."""

        if not self.types:
            self.show_form()
        tables = []
        if "Glossary Term" in self.types:
            tables.append(self.glossary_terms)
        if "Summary" in self.types:
            tables.append(self.summaries)
        return tables

    def show_report(self):
        """Override in order to customize the formatting."""

        css = (
            "table { width: 90%; }",
            "td:first-child { width: 100px; text-align: center; }",
        )
        self.report.page.add_css("\n".join(css))
        self.report.send()

    @property
    def glossary_terms(self):
        """Table for glossary terms which link to media documents."""

        if not hasattr(self, "_glossary_terms"):
            d_path = "/GlossaryTermConcept/TermDefinition/DefinitionText"
            fields = "d.doc_id", "d.value"
            query = self.Query("query_term_pub d", *fields).unique()
            query.join("query_term_pub o", "o.doc_id = d.doc_id")
            query.join("query_term_pub m", "m.doc_id = o.int_val")
            query.where(f"d.path = '{d_path}'")
            query.where("m.path LIKE '%MediaID/@cdr:ref'")
            rows = query.order("d.value").execute(self.cursor).fetchall()
            caption = f"Glossary Terms ({len(rows)})"
            opts = dict(columns=self.COLUMNS, caption=caption)
            self._glossary_terms = self.Reporter.Table(rows, **opts)
        return self._glossary_terms

    @property
    def summaries(self):
        """Table for summaries which link to media documents."""

        if not hasattr(self, "_summaries"):
            fields = "t.doc_id", "t.value"
            query = self.Query("query_term_pub t", *fields).order("t.value")
            query.join("query_term_pub m", "m.doc_id = t.doc_id")
            query.where("t.path = '/Summary/SummaryTitle'")
            query.where("m.path LIKE '/Summary/%MediaID/@cdr:ref'")
            rows = query.unique().execute(self.cursor).fetchall()
            caption = f"Summaries ({len(rows)})"
            opts = dict(columns=self.COLUMNS, caption=caption)
            self._summaries = self.Reporter.Table(rows, **opts)
        return self._summaries

    @property
    def types(self):
        """Document type(s) selected for the report."""
        return self.fields.getlist("type")


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
