#!/usr/bin/env python

"""Reports on documents which link to specified terms.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):

    SUBTITLE = "Report on documents indexed by specified terms"
    CAPTION = "Term Usage"
    COLUMNS = "Doc Type", "Doc ID", "Doc Title", "Term ID", "Term Title"

    def build_tables(self):
        """Assemble the table for the report."""

        if not self.terms:
            self.show_form()
        opts = dict(caption=self.caption, columns=self.COLUMNS)
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Put up a request for document IDs.

        Pass:
            page - HTMLPage on which to plant the field
        """

        fieldset = page.fieldset("Enter Term IDs Separated by Space")
        fieldset.append(page.textarea("ids", label="Term IDs", rows = 5))
        page.form.append(fieldset)

    @property
    def caption(self):
        """String to display above the report table."""

        count = len(set([link.id for link in self.links]))
        return f"Number of documents using specified terms: {count}"

    @property
    def ids(self):
        """Term IDs selected for the report."""

        if not hasattr(self, "_ids"):
            ids = self.fields.getvalue("ids") or ""
            try:
                self._ids = [Doc.extract_id(id) for id in ids.split()]
            except:
                self.bail(f"Invalid document ID format in {ids}")
        return self._ids

    @property
    def links(self):
        """Unique combinations of linkers and link targets."""

        if not hasattr(self, "_links"):
            fields = "t.name AS dtype", "d.title", "q.int_val AS term", "d.id"
            query = self.Query("document d", *fields).unique()
            query.order("t.name", "d.title", "q.int_val")
            query.join("doc_type t", "t.id = d.doc_type")
            query.join("query_term q", "q.doc_id = d.id")
            query.where("q.path LIKE '%/@cdr:ref'")
            query.where("t.name <> 'Term'")
            query.where(query.Condition("q.int_val", list(self.terms), "IN"))
            self._links = query.execute(self.cursor).fetchall()
        return self._links

    @property
    def rows(self):
        """Table rows for the report."""

        if not hasattr(self, "_rows"):
            self._rows = []
            for link in self._links:
                self._rows.append([
                    link.dtype,
                    f"CDR{link.id:010d}",
                    link.title,
                    f"CDR{link.term:010d}",
                    self.terms[link.term],
                ])
        return self._rows

    @property
    def terms(self):
        """Dictionary of term document titles indexed by CDR ID integers."""

        if not hasattr(self, "_terms"):
            query = self.Query("document", "id", "title")
            query.where(query.Condition("id", self.ids, "IN"))
            rows = query.execute(self.cursor).fetchall()
            self._terms = dict([tuple(row) for row in rows])
        return self._terms


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
