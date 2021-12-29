#!/usr/bin/env python

"""Search for CDR GlossaryConceptName documents.
"""

from cdrcgi import AdvancedSearch


class GlossaryTermConceptSearch(AdvancedSearch):
    """Customize search for this document type."""

    DOCTYPE = "GlossaryTermConcept"
    SUBTITLE = "Glossary Term Concept"
    PATHS = {
        "concept": [
            "/GlossaryTermConcept/TermDefinition/DefinitionText",
            "/GlossaryTermConcept/TranslatedTermDefinition/DefinitionText",
        ],
        "audience": [
            "/GlossaryTermConcept/TermDefinition/Audience",
            "/GlossaryTermConcept/TranslatedTermDefinition/Audience",
        ],
        "dictionary": [
            "/GlossaryTermConcept/TermDefinition/Dictionary",
            "/GlossaryTermConcept/TranslatedTermDefinition/Dictionary",
        ],
        "stat_en": [
            "/GlossaryTermConcept/TermDefinition/DefinitionStatus",
        ],
        "stat_es": [
            "/GlossaryTermConcept/TranslatedTermDefinition/TranslatedStatus",
        ],
    }

    def __init__(self):
        AdvancedSearch.__init__(self)
        for name in self.PATHS:
            setattr(self, name, self.fields.getvalue(name))
        if self.audience and self.audience not in self.audiences:
            raise Exception("Tampering with form values")
        if self.dictionary and self.dictionary not in self.dictionaries:
            raise Exception("Tampering with form values")
        if self.stat_en and self.stat_en not in self.statuses_en:
            raise Exception("Tampering with form values")
        if self.stat_es and self.stat_es not in self.statuses_es:
            raise Exception("Tampering with form values")
        statuses_en = [""] + self.statuses_en
        statuses_es = [""] + self.statuses_es
        self.search_fields = (
            self.text_field("concept"),
            self.select("audience", options=[""]+self.audiences),
            self.select("dictionary", options=[""]+self.dictionaries),
            self.select("stat_en", label="Status (en)", options=statuses_en),
            self.select("stat_es", label="Status (es)", options=statuses_es),
        )
        self.query_fields = []
        for name, paths in self.PATHS.items():
            field = self.QueryField(getattr(self, name), paths)
            self.query_fields.append(field)

    @property
    def audiences(self):
        return self.values_for_paths(self.PATHS["audience"])

    @property
    def dictionaries(self):
        return self.values_for_paths(self.PATHS["dictionary"])

    @property
    def statuses_en(self):
        return self.values_for_paths(self.PATHS["stat_en"])

    @property
    def statuses_es(self):
        return self.values_for_paths(self.PATHS["stat_es"])

    def __values_list(self, paths):
        """duplicate????????????"""
        query = self.DBQuery("query_term", "value").unique().order("value")
        query.where(query.Condition("path", paths, "IN"))
        rows = query.execute(self.session.cursor).fetchall()
        return [row.value for row in rows]


if __name__ == "__main__":
    GlossaryTermConceptSearch().run()
