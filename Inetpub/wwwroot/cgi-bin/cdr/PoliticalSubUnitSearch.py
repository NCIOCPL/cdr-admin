#!/usr/bin/env python

"""Search for CDR PoliticalSubUnit documents.
"""

from cdrcgi import AdvancedSearch


class PoliticalSubUnitSearch(AdvancedSearch):
    """Customize search for this document type."""

    DOCTYPE = "PoliticalSubUnit"
    SUBTITLE = DOCTYPE
    FILTER = "set:QC PoliticalSubUnit Set"
    PATHS = (
        "/PoliticalSubUnit/PoliticalSubUnitFullName",
        "/PoliticalSubUnit/PoliticalSubUnitShortName",
        "/PoliticalSubUnit/PoliticalSubUnitAlternateName",
    )

    def __init__(self):
        AdvancedSearch.__init__(self)
        state = self.fields.getvalue("state")
        self.search_fields = [self.text_field("state", label="Name")]
        self.query_fields = [self.QueryField(state, self.PATHS)]


if __name__ == "__main__":
    PoliticalSubUnitSearch().run()
