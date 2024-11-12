#!/usr/bin/env python

"""Show thesaurus concept IDs for concepts marked as not yet public.
"""

from functools import cached_property
from cdrcgi import Controller
from nci_thesaurus import EVS


class Control(Controller):
    """Access to database and report building facilities."""

    SUBTITLE = "NCI Thesaurus Links Not Marked Public"
    COLUMNS = (
        ("CDR ID", "unique ID of the Term document in the CDR"),
        ("Concept ID", "unique ID for the Concept in the NCI Thesaurus"),
        ("Available?", "'Yes' if the NCI Thesaurus still has the concept"),
        ("Last Mod", "the date the CDR Term document was last modified"),
        ("Semantic Types", "for example, Drug/agent"),
    )
    COLS = [column[0] for column in COLUMNS]
    INSTRUCTIONS = (
        "NCI Thesaurus concept codes/IDs are added to Term documents (using "
        "the NCIThesaurusConcept element) which are in turn used to create "
        "links from the Drug Dictionary to the NCI Thesaurus on Cancer.gov. "
        "However, there is always a lag between when we manually add the "
        "Concept code to the CDR term document and when the concept is made "
        "available in the thesaurus (by NCI Thesaurus staff) During this "
        "period, the link doesn't work from the Drug Dictionary on Cancer.gov "
        "to the NCI Thesaurus. This report shows concepts in the NCI "
        "Thesaurus whose corresponding CDR Term documents have not been "
        "marked as 'Public'. The report contains the following columns."
    )

    def populate_form(self, page):
        """Explain the report.

        Required positional argument:
          page - HTMLPage instance
        """

        # Bypass the form when not invoked from the menu.
        if not self.fields.getvalue("prompt"):
            self.show_report()

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        columns = page.B.UL()
        for name, description in self.COLUMNS:
            columns.append(page.B.LI(page.B.B(name), f" ({description})"))
        fieldset.append(columns)
        page.form.append(fieldset)

    def build_tables(self):
        """Return the single table for the report."""
        return self.table

    @cached_property
    def evs(self):
        """Interface to the EVS API."""
        return EVS()

    @cached_property
    def table(self):
        """Assemble the report's table."""
        return self.Reporter.Table(self.rows, columns=self.COLS)

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

        @cached_property
        def available(self):
            """Yes or No, depending on whether NCI/T still has the term."""

            try:
                self.__control.evs.fetch(self.code, include="minimal")
                return "Yes"
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
