#!/usr/bin/env python

"""Show recent imports/updates from the EVS.
"""

from datetime import date, timedelta
from functools import cached_property
from cdrcgi import Controller


class Control(Controller):
    """Report-specific behavior implemented in this derived class."""

    SUBTITLE = "Terminology Import/Update Report"
    FIELDS = "n.doc_id", "c.value AS code, n.value AS name", "a.dt", "a.comment"
    COLUMNS = "CDR ID", "NCI/T ID", "Preferred Name", "Action", "Date"

    def build_tables(self):
        """Create the table for the report."""

        query = self.Query("audit_trail a", *self.FIELDS)
        query.join("query_term n", "n.doc_id = a.document")
        query.join("query_term c", "c.doc_id = a.document")
        query.where("n.path = '/Term/PreferredName'")
        query.where("c.path = '/Term/NCIThesaurusConcept'")
        query.where("a.comment LIKE 'Term document % from EVS 20%'")
        if self.start:
            query.where(query.Condition("a.dt", self.start, ">="))
        if self.end:
            end = f"{self.end} 23:59:59.999"
            query.where(query.Condition("a.dt", end, "<="))
        query.order("a.dt")
        rows = []
        for row in query.execute(self.cursor).fetchall():
            action = "Updated" if "refreshed" in row.comment else "Imported"
            when = row.dt.strftime("%Y-%m-%d")
            rows.append([row.doc_id, row.code, row.name, action, when])
        return self.Reporter.Table(rows, columns=self.COLUMNS, caption="Terms")

    def populate_form(self, page):
        """Put the fields on the form.

        Pass:
            page - `HTMLPage` object on which the form is drawn
        """

        end = date.today()
        start = end - timedelta(14)
        fieldset = page.fieldset("Specify Date Range For Report")
        fieldset.append(page.date_field("start", value=start))
        fieldset.append(page.date_field("end", value=end))
        page.form.append(fieldset)

    @cached_property
    def end(self):
        """Ending date for the date range on which we are to report."""
        return self.parse_date(self.fields.getvalue("end"))

    @cached_property
    def start(self):
        """Start date for the date range on which we are to report."""
        return self.parse_date(self.fields.getvalue("start"))


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
