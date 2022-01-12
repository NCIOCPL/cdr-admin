#!/usr/bin/env python

"""Search for CDR Term documents.
"""

from functools import cached_property
from cdrcgi import AdvancedSearch


class TermSearch(AdvancedSearch):
    """Customize search for this document type."""

    DOCTYPE = "Term"
    SUBTITLE = DOCTYPE
    FILTER = "set:QC Term Set"
    NCIT = "https://nciterms.nci.nih.gov"
    PATHS = dict(
        name="/Term/PreferredName",
        other_name="/Term/OtherName/OtherTermName",
        term_type="/Term/TermType/TermTypeName",
        sem_type="/Term/SemanticType/@cdr:ref",
    )

    def __init__(self):
        """Set the stage for showing the search form or the search results."""

        AdvancedSearch.__init__(self)
        for name in self.PATHS:
            setattr(self, name, self.fields.getvalue(name))
        self.changes = None
        # pylint: disable=no-member
        if self.term_type and self.term_type not in self.term_types:
            raise Exception("Tampering with form values")
        if self.sem_type:
            if self.sem_type not in [st[0] for st in self.semantic_types]:
                raise Exception("Tampering with form values")
        # pylint: enable=no-member
        self.search_fields = (
            self.text_field("name"),
            self.text_field("other_name"),
            self.select("term_type", options=[""]+self.term_types),
            self.select("sem_type", options=[""]+self.semantic_types),
        )
        self.query_fields = []
        for name, path in self.PATHS.items():
            field = self.QueryField(getattr(self, name), [path])
            self.query_fields.append(field)

    def customize_form(self, page):
        """Add a button for browsing the NCI Thesaurus.

        If the user has sufficient permissions, also add fields for
        importing a new thesaurus concept or updating one we have imported
        in the past.
        """

        ncit = f"window.open('{self.NCIT}', 'ncit');"
        buttons = page.body.xpath("//*[@id='header-buttons']")
        buttons[0].append(self.button("Search NCI Thesaurus", onclick=ncit))

    @cached_property
    def semantic_types(self):
        """Valid values for the semantic types piclist."""

        fields = "d.id", "d.title"
        query = self.DBQuery("document d", *fields).unique().order("d.title")
        query.join("query_term t", "t.int_val = d.id")
        query.where(query.Condition("t.path", self.PATHS["sem_type"]))
        rows = query.execute(self.session.cursor).fetchall()
        return [(f"CDR{row.id:010d}", row.title) for row in rows]

    @cached_property
    def term_types(self):
        """Valid values for the term types picklist."""
        return self.values_for_paths([self.PATHS["term_type"]])


if __name__ == "__main__":
    TermSearch().run()
