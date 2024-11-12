#!/usr/bin/env python

"""Search for CDR Person documents with addresses displayed in the results.
"""

from cdrapi.docs import Doc
from cdrcgi import AdvancedSearch


class PersonSearch(AdvancedSearch):
    """Coordination of the processing flow."""

    DOCTYPE = "Person"
    SUBTITLE = "Persons With Locations"
    ADDRESS_FILTER = "name:Person Locations Picklist"
    PATHS = {
        "surname": "/Person/PersonNameInformation/SurName",
        "forename": "/Person/PersonNameInformation/GivenName",
        "initials": "/Person/PersonNameInformation/MiddleInitial",
    }

    # Tell the base class to let us populate the report's table.
    INCLUDE_ROWS = False
    CSS = """\
.has-addresses td { border-bottom: none; }
.person-addresses td { border-top: none; }
td ul { margin-top: 0; margin-bottom: 0; }
"""

    def __init__(self):
        """Add the fields for this search type."""

        AdvancedSearch.__init__(self)
        for name in self.PATHS:
            setattr(self, name, self.fields.getvalue(name))
        self.search_fields = (
            self.text_field("surname"),
            self.text_field("forename", label="Given Name"),
            self.text_field("initials"),
        )
        self.query_fields = []
        for name, path in self.PATHS.items():
            field = self.QueryField(getattr(self, name), [path])
            self.query_fields.append(field)

    def customize_report(self, page):
        """Create a custom version of the report with address information."""

        # Styling for the custom portion of the table.
        page.head.append(page.B.STYLE(self.CSS))

        # Housekeeping before we get into the loop for the search results.
        table = page.body.find(".//table")
        table.set("class", "usa-table usa-table--borderless")
        session_parm = f"&{self.SESSION}={self.session.name}"
        filter_parms = dict(repName="dummy", includeHomeAddresses="yes")

        # Walk through each row in the results set.
        for i, row in enumerate(self.rows):
            doc = Doc(self.session, id=row[0])
            title = row[1]
            url = f"{self.BASE}/QcReport.py?DocId={doc.cdr_id}{session_parm}"
            link = page.B.A(doc.cdr_id, href=url)

            # Find addresses for the person.
            filter_parms["docId"] = doc.cdr_id
            response = doc.filter(self.ADDRESS_FILTER, parms=filter_parms)
            root = response.result_tree.getroot()
            addresses = []
            for node in root.iter("Data"):
                address = Doc.get_text(node)
                if address:
                    addresses.append(address)

            # Create the first table row for this result.
            classes = "has-addresses" if addresses else "no-addresses"
            tr = page.B.TR(page.B.CLASS(classes))
            tr.append(page.B.TD(f"{i+1}.", page.B.CLASS("row-number")))
            tr.append(page.B.TD(link, page.B.CLASS("doc-link")))
            tr.append(page.B.TD(title, page.B.CLASS("doc-title")))
            table.append(tr)

            # Add a second row to the table if there are any addresses.
            if addresses:
                ul = page.B.UL()
                td = page.B.TD(ul, colspan="3")
                tr = page.B.TR(td, page.B.CLASS("person-addresses"))
                for address in addresses:
                    ul.append(page.B.LI(address))
                table.append(tr)


if __name__ == "__main__":
    PersonSearch().run()
