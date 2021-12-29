#!/usr/bin/env python

"""Search for CDR GlossaryTermName documents.
"""

from cdrcgi import AdvancedSearch


class GlossaryTermNameSearch(AdvancedSearch):
    """Customize search for this document type."""

    DOCTYPE = "GlossaryTermName"
    SUBTITLE = "Glossary Term Name"
    PATHS = dict(
        name_en="/GlossaryTermName/TermName/TermNameString",
        name_es="/GlossaryTermName/TranslatedName/TermNameString",
        stat_en="/GlossaryTermName/TermNameStatus",
        stat_es="/GlossaryTermName/TranslatedName/TranslatedNameStatus",
    )

    def __init__(self):
        AdvancedSearch.__init__(self)
        for name in self.PATHS:
            setattr(self, name, self.fields.getvalue(name))
        if self.stat_en and self.stat_en not in self.statuses_en:
            raise Exception("Tampering with form values")
        if self.stat_es and self.stat_es not in self.statuses_es:
            raise Exception("Tampering with form values")
        statuses_en = [""] + self.statuses_en
        statuses_es = [""] + self.statuses_es
        self.search_fields = (
            self.text_field("name_en", label="Name (en)"),
            self.select("stat_en", label="Status (en)", options=statuses_en),
            self.text_field("name_es", label="Name (es)"),
            self.select("stat_es", label="Status (es)", options=statuses_es),
        )
        self.query_fields = []
        for name, path in self.PATHS.items():
            field = self.QueryField(getattr(self, name), [path])
            self.query_fields.append(field)

    @property
    def statuses_en(self):
        return self.__status_list(self.PATHS["stat_en"])

    @property
    def statuses_es(self):
        return self.__status_list(self.PATHS["stat_es"])

    def __status_list(self, path):
        query = self.DBQuery("query_term", "value").unique().order("value")
        query.where(query.Condition("path", path))
        rows = query.execute(self.session.cursor).fetchall()
        return [row.value for row in rows]


if __name__ == "__main__":
    GlossaryTermNameSearch().run()
