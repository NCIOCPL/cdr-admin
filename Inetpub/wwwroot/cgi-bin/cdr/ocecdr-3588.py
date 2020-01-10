#!/usr/bin/env python

"""Show thesaurus concept IDs for concepts marked as not yet public.
"""

from cdrcgi import Controller
from nci_thesaurus import Concept

class Control(Controller):
    """Access to database and report building facilities."""

    SUBTITLE = "NCI Thesaurus Links Not Marked Public"
    COLS = "CDR ID", "Concept ID", "Available?", "Last Mod", "Semantic Types"

    def show_form(self):
        """Bypass the form."""
        self.show_report()

    def build_tables(self):
        """Return the single table for the report."""
        return self.table

    @property
    def table(self):
        """Assemble the report's table."""

        if not hasattr(self, "_table"):
            self._table = self.Reporter.Table(self.rows, columns=self.COLS)
        return self._table

    @property
    def rows(self):
        """Table rows for the report."""
        return [term.row for term in self.terms]

    @property
    def terms(self):
        """Terms for concepts marked as not yet public."""

        query = self.Query("query_term c", "c.doc_id AS id", "c.value AS code")
        query.outer("query_term p", "p.doc_id = c.doc_id",
                    "p.node_loc = c.node_loc")
        query.where("c.path = '/Term/NCIThesaurusConcept'")
        query.where("p.path = '/Term/NCIThesaurusConcept/@Public'")
        query.where(query.Or("p.value IS NULL", "p.value <> 'Yes'"))
        query.order("c.doc_id", "c.value")
        rows = query.execute(self.cursor).fetchall()
        return [self.Term(self, row) for row in rows]


    class Term:
        """CDR Terminology document."""

        def __init__(self, control, row):
            """Remember the caller's values.

            Pass:
                control - access to the database and report building
                row - result set row from the database query
            """

            self.__control = control
            self.__row = row

        @property
        def available(self):
            """Yes or No, depending on whether NCI/T still has the term."""

            try:
                concept = Concept(code=self.code)
                return "Yes" if  concept.code.upper() == self.code else "No"
            except Exception:
                self.__control.logger.exception("fetching %r" % self.code)
                return "No"

        @property
        def code(self):
            """Thesaurus concept code for the term."""
            return self.__row.code.strip().upper()

        @property
        def id(self):
            """Display ID for the report row."""
            return f"CDR{self.__row.id}"

        @property
        def mod(self):
            """When was the term document last modified."""

            query = self.__control.Query("query_term", "value")
            query.where("path = '/Term/DateLastModified'")
            query.where(query.Condition("doc_id", self.__row.id))
            rows = query.execute(self.__control.cursor).fetchall()
            return rows[0].value if rows else ""

        @property
        def row(self):
            """Table row for the report."""
            return self.id, self.code, self.available, self.mod, self.types

        @property
        def types(self):
            """Semantic types for the term, formatted for display."""

            query = self.__control.Query("query_term n", "n.value").unique()
            query.join("query_term t", "t.int_val = n.doc_id")
            query.where("n.path = '/Term/PreferredName'")
            query.where("t.path = '/Term/SemanticType/@cdr:ref'")
            query.where(query.Condition("t.doc_id", self.__row.id))
            rows = query.execute(self.__control.cursor).fetchall()
            return "; ".join([row.value for row in rows])


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
