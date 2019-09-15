#!/usr/bin/env python

"""Search for CDR Person documents.
"""

from cdrcgi import AdvancedSearch

class PersonSearch(AdvancedSearch):
    """Customize search for this document type."""

    DOCTYPE = "Person"
    SUBTITLE = DOCTYPE
    LOCATIONS = "/Person/PersonLocations"
    HOME_ADDRESS = f"{LOCATIONS}/Home/PostalAddress"
    PRIVATE_PRACTICE = f"{LOCATIONS}/PrivatePractice/PrivatePracticeLocation"
    PRIVATE_PRACTICE_ADDRESS = f"{PRIVATE_PRACTICE}/PostalAddress"
    OTHER_ADDRESS = f"{LOCATIONS}/OtherPracticeLocation/SpecificPostalAddress"
    PATHS = {
        "surname": ["/Person/PersonNameInformation/SurName"],
        "forname": ["/Person/PersonNameInformation/GivenName"],
        "initials": ["/Person/PersonNameInformation/MiddleInitial"],
        "street": [
            f"{HOME_ADDRESS}/Street",
            f"{PRIVATE_PRACTICE_ADDRESS}/Street",
            f"{OTHER_ADDRESS}/Street"
        ],
        "city": [
            f"{HOME_ADDRESS}/City",
            f"{PRIVATE_PRACTICE_ADDRESS}/City",
            f"{OTHER_ADDRESS}/City"
        ],
        "state": [
            f"{HOME_ADDRESS}/PoliticalSubUnit_State/@cdr:ref",
            f"{PRIVATE_PRACTICE_ADDRESS}/PoliticalSubUnit_State/@cdr:ref",
            f"{OTHER_ADDRESS}/PoliticalSubUnit_State/@cdr:ref"
        ],
        "zipcode": [
            f"{HOME_ADDRESS}/PostalCode_ZIP",
            f"{PRIVATE_PRACTICE_ADDRESS}/PostalCode_ZIP",
            f"{OTHER_ADDRESS}/PostalCode_ZIP"
        ],
        "country": [
            f"{HOME_ADDRESS}/Country/@cdr:ref",
            f"{PRIVATE_PRACTICE_ADDRESS}/Country/@cdr:ref",
            f"{OTHER_ADDRESS}/Country/@cdr:ref"
        ],
    }

    def __init__(self):
        """Add the fields for this search type."""
        AdvancedSearch.__init__(self)
        for name in self.PATHS:
            setattr(self, name, self.fields.getvalue(name))
        if self.state and self.state not in [s[0] for s in self.states]:
            raise Exception("Tampering with form values")
        if self.country and self.country not in [c[0] for c in self.countries]:
            raise Exception("Tampering with form values")
        self.search_fields = (
            self.text_field("surname"),
            self.text_field("forename", label="Given Name"),
            self.text_field("initials"),
            self.text_field("street"),
            self.text_field("city"),
            self.select("state", options=[""]+self.states),
            self.text_field("zipcode", label="ZIP Code"),
            self.select("country", options=[""]+self.countries),
        )
        self.query_fields = []
        for name, paths in self.PATHS.items():
            field = self.QueryField(getattr(self, name), paths)
            self.query_fields.append(field)


if __name__ == "__main__":
    PersonSearch().run()
