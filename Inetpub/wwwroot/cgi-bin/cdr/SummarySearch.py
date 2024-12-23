#!/usr/bin/env python

"""Search for CDR Summary documents.
"""

from functools import cached_property
from cdrcgi import AdvancedSearch


class SummarySearch(AdvancedSearch):
    """Customize search for this document type."""

    DOCTYPE = "Summary"
    SUBTITLE = DOCTYPE
    SUMMARY_SECTION = "/Summary/SummarySection"
    SUMMARY_METADATA = "/Summary/SummaryMetaData"
    PATHS = {
        "title": ["/Summary/SummaryTitle"],
        "section_type": [f"{SUMMARY_SECTION}/%SectMetaData/SectionType"],
        "diagnosis": [f"{SUMMARY_SECTION}/%SectMetaData/Diagnosis/@cdr:ref"],
        "audience": ["/Summary/SummaryMetaData/SummaryAudience"],
        "topic": ["/Summary/SummaryMetaData/%Topics/Term/@cdr:ref"],
        "status": "active_status",
    }

    def __init__(self):
        AdvancedSearch.__init__(self)
        for name in self.PATHS:
            setattr(self, name, self.fields.getvalue(name))
        # pylint: disable=no-member
        if self.section_type and self.section_type not in self.section_types:
            raise Exception("Tampering with form values")
        if self.audience and self.audience not in self.audiences:
            raise Exception("Tampering with form values")
        if self.topic and self.topic not in [t[0] for t in self.topics]:
            raise Exception("Tampering with form values")
        if self.status and self.status not in [s[0] for s in self.statuses]:
            raise Exception("Tampering with form values")
        if self.diagnosis:
            if self.diagnosis not in [d[0] for d in self.diagnoses]:
                raise Exception("Tampering with form values")
        # pylint: enable=no-member
        types = [""] + self.section_types
        self.search_fields = (
            self.text_field("title"),
            self.select("section_type", label="Sec Type", options=types),
            self.select("diagnosis", options=[""]+self.diagnoses),
            self.select("audience", options=[""]+self.audiences),
            self.select("topic", options=[""]+self.topics),
            self.select("status", options=[""]+self.statuses),
        )
        self.query_fields = []
        for name, paths in self.PATHS.items():
            field = self.QueryField(getattr(self, name), paths)
            self.query_fields.append(field)

    @cached_property
    def audiences(self):
        """Valid values for the audience field"""

        query = self.DBQuery("query_term", "value").unique().order("value")
        query.where(query.Condition("path", self.PATHS["audience"][0]))
        query.where("value IS NOT NULL")
        query.where("value <> ''")
        rows = query.execute(self.session.cursor).fetchall()
        return [row.value for row in rows]

    @cached_property
    def section_types(self):
        """Valid summary section types."""

        path = self.PATHS["section_type"][0]
        query = self.DBQuery("query_term", "value").unique().order("value")
        query.where(query.Condition("path", path, "LIKE"))
        query.where("value IS NOT NULL")
        query.where("value <> ''")
        rows = query.execute(self.session.cursor).fetchall()
        return [row.value for row in rows]

    @cached_property
    def diagnoses(self):
        """Picklist values for diagnosis field."""
        return self.__linked_docs("diagnosis")

    @cached_property
    def topics(self):
        """Picklist values for topic field."""
        return self.__linked_docs("topic")

    def __linked_docs(self, field):
        """Find documents linked for a field's path.

        Pass:
            field - field name, used as index into PATHS

        Return:
            list of (cdr-id, title) tuples for linked documents
        """

        cols = "d.id", "d.title"
        path = self.PATHS[field][0]
        query = self.DBQuery("document d", *cols).unique().order("d.title")
        query.join("query_term q", "q.int_val = d.id")
        query.where(query.Condition("q.path", path, "LIKE"))
        rows = query.execute(self.session.cursor).fetchall()
        picklist = []
        for row in rows:
            picklist.append((f"CDR{row.id:010d}", row.title.split(";")[0]))
        return picklist


if __name__ == "__main__":
    SummarySearch().run()
