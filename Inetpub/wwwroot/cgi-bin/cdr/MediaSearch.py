#!/usr/bin/env python

"""Search for CDR Media documents.
"""

from cdrcgi import AdvancedSearch


class MediaSearch(AdvancedSearch):
    """Customize search for this document type."""

    DOCTYPE = "Media"
    SUBTITLE = DOCTYPE
    FILTER = "set:QC Media Set"
    PATHS = {
        "title": ["/Media/MediaTitle"],
        "desc": ["/Media/MediaContent/ContentDescriptions/ContentDescription"],
        "category": ["/Media/MediaContent/Categories/Category"],
        "diagnosis": ["/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref"],
        "image_type": ["/Media/PhysicalMedia/ImageData/ImageType"],
        "language": ["/Media/MediaContent/Captions/MediaCaption/@language"],
        "use": [
            "/Media/ProposedUse/Summary/@cdr:ref[int_val]",
            "/Media/ProposedUse/Glossary/@cdr:ref[int_val]",
        ],
    }

    def __init__(self):
        """Add the fields for this search type."""

        AdvancedSearch.__init__(self)
        for name in self.PATHS:
            setattr(self, name, self.fields.getvalue(name))
        if self.category and self.category not in self.categories:
            raise Exception("Tampering with form values")
        if self.image_type and self.image_type not in self.image_types:
            raise Exception("Tampering with form values")
        if self.language and self.language not in self.languages:
            raise Exception("Tampering with form values")
        if self.diagnosis:
            if self.diagnosis not in [d[0] for d in self.diagnoses]:
                raise Exception("Tampering with form values")
        self.search_fields = (
            self.text_field("title"),
            self.text_field("desc", label="Content Desc"),
            self.select("category", options=[""]+self.categories),
            self.select("diagnosis", options=[""]+self.diagnoses),
            self.text_field("use", label="Prop Use"),
            self.select("image_type", options=[""]+self.image_types),
            self.select("language", options=[""]+self.languages)
        )
        self.query_fields = []
        for name, paths in self.PATHS.items():
            field = self.QueryField(getattr(self, name), paths)
            self.query_fields.append(field)

    @property
    def categories(self):
        """Valid values list for image categories."""
        return self.valid_values["Category"]

    @property
    def image_types(self):
        """Valid values list for image types."""
        return self.valid_values["ImageType"]

    @property
    def languages(self):
        """Valid values list for image language."""
        return self.valid_values["MediaCaption@language"]

    @property
    def diagnoses(self):
        query = self.DBQuery("query_term t", "t.doc_id", "t.value").unique()
        query.join("query_term m", "m.int_val = t.doc_id")
        query.where(query.Condition("m.path", self.PATHS["diagnosis"][0]))
        query.where("t.path = '/Term/PreferredName'")
        query.order("t.value")
        rows = query.execute(self.session.cursor).fetchall()
        return [(f"CDR{row.doc_id:010d}", row.value) for row in rows]


if __name__ == "__main__":
    MediaSearch().run()
