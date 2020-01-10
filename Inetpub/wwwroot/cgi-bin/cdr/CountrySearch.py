#!/usr/bin/env python

"""Search for CDR Person documents with addresses displayed in the results.
"""

from cdrcgi import AdvancedSearch

class CountrySearch(AdvancedSearch):
    """Customize search for this document type."""

    DOCTYPE = "Country"
    SUBTITLE = DOCTYPE
    FILTER = "name:Country QC Report Filter"
    PATHS = (
        "/Country/CountryFullName",
        "/Country/CountryShortName",
        "/CountryCountryAlternateName",
    )

    def __init__(self):
        AdvancedSearch.__init__(self)
        name = self.fields.getvalue("name")
        self.search_fields = [self.text_field("name")]
        self.query_fields = [self.QueryField(name, self.PATHS)]


if __name__ == "__main__":
    CountrySearch().run()
