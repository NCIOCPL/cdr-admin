#!/usr/bin/env python

"""Search for CDR Person documents with addresses displayed in the results.
"""

import cgi
import cdrcgi
from cdrapi.docs import Doc
from cdrapi.users import Session

class Control:
    """Coordination of the processing flow."""

    def __init__(self):
        fields = cgi.FieldStorage()
        self.session = Session(cdrcgi.getSession(fields) or "guest")
        self.surname = fields.getvalue("surname")
        self.forename = fields.getvalue("forename")
        self.initials = fields.getvalue("initials")
        self.request = fields.getvalue("Request")
        self.match_all = True if fields.getvalue("match_all") else False

    def run(self):
        if self.request == "Search":
            self.show_report()
        else:
            self.show_form()

    def show_form(self):
        Page = cdrcgi.AdvancedSearchPage
        fields = (
            Page.text_field("surname"),
            Page.text_field("given", label="Given Name"),
            Page.text_field("initials"),
        )
        page = Page(self.session.name, "Person (with locations)", fields)
        cdrcgi.sendPage(page.tostring())

    def show_report(self):
        """Assemble the query, execute it, and show the results."""

        # Assemble the advanced search query.
        Field = cdrcgi.SearchField
        fields = (
            Field(surname, ["/Person/PersonNameInformation/SurName"]),
            Field(givenName, ["/Person/PersonNameInformation/GivenName"]),
            Field(initials, ["/Person/PersonNameInformation/MiddleInitial"]),
        )
        query = cdrcgi.AdvancedSearchQuery(fields, "Person", match_all)

        # Get the results from the query.
        try:
            rows = query.execute().fetchall()
        except Exception as e:
            cdrcgi.bail(f"Failure retrieving Person documents: {e}")

        # Create the shell for the results page.
        strings = " ".join(query.criteria)
        opts = dict(search_strings=strings, count=len(rows))
        page = cdrcgi.AdvancedSearchResultsPage("Person", **opts)

        # Housekeeping before we get into the loop for the search results.
        table = page.body.find("table")
        table.set("class", "person-loc-search-results")
        session_parm = f"&{cdrcgi.SESSION}={self.session.name}"
        filter_parms = dict(repName="dummy", includeHomeAddresses="yes")
        filtre = "name:Person Locations Picklist"

        # Walk through each row in the results set.
        for i, row  in enumerate(rows):
            doc = Doc(self.session, id=row[0])
            title = row[1]
            url = f"{cdrcgi.BASE}/QcReport.py?DocId={doc.cdr_id}{session_parm}"
            link = page.B.A(doc.cdr_id, href=url)

            # Create the first table row for this result.
            tr = page.B.TR(page.B.CLASS("row-item"))
            tr.append(page.B.TD(f"{i+1}.", page.B.CLASS("row-number")))
            tr.append(page.B.TD(link, page.B.CLASS("doc-link")))
            tr.append(page.B.TD(title, page.B.CLASS("doc-title")))
            table.append(tr)

            # Add a second row to the table if there are any addresses.
            filter_parms["docId"] = doc.cdr_id
            try:
                response = doc.filter(filtre, parms=filter_parms)
                tree = response.result_tree
            except Exception as e:
                cdrcgi.bail(str(e))
            addresses = [node for node in tree.iter("Data")]
            if addresses:
                ul = page.B.UL()
                td = page.B.TD(ul, colspan="3")
                tr = page.B.TR(page.B.CLASS("person-addresses"))
                for node in addresses:
                    ul.append(page.B.LI(Doc.get_text(node, default="")))
                table.append(tr)

        # Send the page back to the browser.
        cdrcgi.sendPage(page.tostring())


if __name__ == "__main__":
    try:
        Control().run()
    except Exception as e:
        cdrcgi.bail(str(e))
