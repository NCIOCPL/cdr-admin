#!/usr/bin/env python

"""Search for CDR Term documents.
"""

from functools import cached_property
from cdrcgi import AdvancedSearch, Controller


class TermSearch(AdvancedSearch):
    """Customize search for this document type."""

    DOCTYPE = "Term"
    SUBTITLE = DOCTYPE
    FILTER = "set:QC Term Set"
    NCIT = "https://evsexplore.semantics.cancer.gov/evsexplore/welcome"
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
        opts = dict(label="Semantic Type", options=[""]+self.semantic_types)
        # pylint: enable=no-member
        self.search_fields = (
            self.text_field("name"),
            self.text_field("other_name"),
            self.select("term_type", options=[""]+self.term_types),
            self.select("sem_type", **opts),
        )
        self.query_fields = []
        for name, path in self.PATHS.items():
            field = self.QueryField(getattr(self, name), [path])
            self.query_fields.append(field)

    def show_form(self, subtitle="Term", error=None):
        """Add a button for browsing the NCI Thesaurus."""

        args = self.session.name, subtitle, self.search_fields
        page = self.Form(*args, error=error, control=self)
        classes = page.B.CLASS("button usa-button")
        opts = dict(name="Request", value="Search", type="submit")
        page.form.append(page.B.INPUT(classes, **opts))
        opts["value"] = "Search NCI Thesaurus"
        opts["onclick"] = f"window.open('{self.NCIT}', 'ncit');"
        page.form.append(page.B.INPUT(classes, **opts))
        page.body.append(page.B.SCRIPT(src=f"{page.USWDS}/js/uswds.min.js"))
        Controller.send_page(page.tostring())

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
