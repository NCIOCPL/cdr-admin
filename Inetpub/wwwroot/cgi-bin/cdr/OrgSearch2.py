#!/usr/bin/env python

"""Search for CDR Organization documents.
"""

from cdrcgi import AdvancedSearch


class OrganizationSearch(AdvancedSearch):
    """Customize search for this document type."""

    DOCTYPE = "Organization"
    SUBTITLE = DOCTYPE
    NAME_INFO = "/Organization/OrganizationNameInformation"
    ORG_LOCATION = "/Organization/OrganizationLocations/OrganizationLocation"
    ADDRESS = f"{ORG_LOCATION}/Location/PostalAddress"
    PATHS = {
        "name": [
            f"{NAME_INFO}/OfficialName/Name",
            f"{NAME_INFO}/ShortName/Name",
            f"{NAME_INFO}/AlternateName",
            f"{NAME_INFO}/FormerName",
        ],
        "type": ["/Organization/OrganizationType"],
        "street": [f"{ADDRESS}/Street"],
        "city": [f"{ADDRESS}/City"],
        "state": [f"{ADDRESS}/PoliticalSubUnit_State/@cdr:ref"],
        "country": [f"{ADDRESS}/Country/@cdr:ref"],
        "zipcode": [f"{ADDRESS}/PostalCode_ZIP"],
    }

    def __init__(self):
        """Add the fields for this search type."""
        AdvancedSearch.__init__(self)
        for name in self.PATHS:
            setattr(self, name, self.fields.getvalue(name))
        if self.type and self.type not in self.types:
            raise Exception("Tampering with form values")
        if self.state and self.state not in [s[0] for s in self.states]:
            raise Exception("Tampering with form values")
        if self.country and self.country not in [c[0] for c in self.countries]:
            raise Exception("Tampering with form values")
        self.search_fields = (
            self.text_field("name"),
            self.select("type", options=[""]+self.types),
            self.text_field("street"),
            self.text_field("city"),
            self.select("state", options=[""]+self.states),
            self.select("country", options=[""]+self.countries),
            self.text_field("zipcode", label="ZIP Code"),
        )
        self.query_fields = []
        for name, paths in self.PATHS.items():
            field = self.QueryField(getattr(self, name), paths)
            self.query_fields.append(field)

    @property
    def types(self):
        """Valid values list for organization types."""

        query = self.DBQuery("query_term", "value").order("value").unique()
        query.where("path = '/Organization/OrganizationType'")
        query.where("value IS NOT NULL")
        query.where("value <> ''")
        rows = query.execute(self.session.cursor).fetchall()
        return [row.value for row in rows]


if __name__ == "__main__":
    OrganizationSearch().run()
