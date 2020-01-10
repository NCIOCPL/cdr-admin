#!/usr/bin/env python

"""Search for CDR Help ("Documentation") documents.
"""

from cdrcgi import AdvancedSearch

class DocumentationSearch(AdvancedSearch):
    """Customize search for this document type."""

    DOCTYPE = "Documentation"
    SUBTITLE = DOCTYPE
    FILTER = "name:Documentation Help Screens Filter"
    PATHS = {
        "doctype": (
            "/Documentation/Metadata/DocType",
        ),
        "function": (
            "/Documentation/Metadata/Function",
        ),
        "keyword": (
            "/Documentation/Metadata/Subject",
            "/Documentation/Body/DocumentationTitle",
        ),
        "infotype": (
            "/Documentation/@InfoType",
        ),
    }
    PICKLIST_FIELDS = "doctype", "function", "infotype"

    def __init__(self):
        AdvancedSearch.__init__(self)
        self.doctype = self.fields.getvalue("doctype")
        self.infotype = self.fields.getvalue("infotype")
        self.function = self.fields.getvalue("function")
        self.keyword = self.fields.getvalue("keyword")
        for name in self.PICKLIST_FIELDS:
            values = self.values_for_paths(self.PATHS[name])
            value = getattr(self, name)
            if value and value not in values:
                raise Exception("Tampering with form values")
            setattr(self, f"{name}s", [""] + values)
        self.search_fields = (
            self.select("doctype", label="Doc Type", options=self.doctypes),
            self.select("function", options=self.functions),
            self.text_field("keyword"),
            self.select("infotype", label="Info Type", options=self.infotypes),
        )
        self.query_fields = []
        for name, paths in self.PATHS.items():
            field = self.QueryField(getattr(self, name), paths)
            self.query_fields.append(field)


if __name__ == "__main__":
    DocumentationSearch().run()
