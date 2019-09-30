#!/usr/bin/env python

"""Find Miscellaneous documents and display QC reports for them.

JIRA::OCECDR-4115 - support searching titles with non-ascii characters
"""

from cdrcgi import AdvancedSearch

class MiscSearch(AdvancedSearch):
    """Customize search for this document type."""

    DOCTYPE = "MiscellaneousDocument"
    SUBTITLE = "Miscellaneous Documents"
    FILTER = "name:Miscellaneous Document Report Filter"
    META_DATA = "/MiscellaneousDocument/MiscellaneousDocumentMetadata"
    TYPE_PATH = f"{META_DATA}/MiscellaneousDocumentType"

    def __init__(self):
        """Add the fields for this search type."""
        AdvancedSearch.__init__(self)
        self.title = self.fields.getvalue("title")
        self.type = self.fields.getvalue("type")
        if self.type and self.type not in self.types:
            raise Exception("Tampering with form values")
        self.search_fields = (
            self.text_field("title"),
            self.select("type", options=[""]+self.types)
        )
        self.query_fields = (
            self.QueryField(self.title, "title"),
            self.QueryField(self.type, [self.TYPE_PATH]),
        )

    @property
    def types(self):
        """Valid miscellaneous document type names."""
        return self.values_for_paths([self.TYPE_PATH])

if __name__ == "__main__":
    MiscSearch().run()
