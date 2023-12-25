#!/usr/bin/env python
"""JSON API for fetching the IDs and names of DrugInformationSummary documents.
"""

from functools import cached_property
from json import dumps
from cdrcgi import Controller


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "get-drug-info API service"
    LOGNAME = "testing"

    def run(self):
        """Overridden because this is not a standard report."""

        query = self.Query("query_term d", "d.doc_id", "d.value")
        query.join("pub_proc_cg c", "c.id = d.doc_id")
        query.where("d.path = '/DrugInformationSummary/Title'")
        if self.limit:
            query.limit(self.limit)
        drugs = []
        query.log()
        for row in query.unique().order(1).execute(self.cursor).fetchall():
            drug = dict(
                id=row.doc_id,
                name=row.value,
            )
            drugs.append(drug)
        self.logger.info("loaded %d drugs", len(drugs))
        self.send_page(dumps(drugs, indent=2), mime_type="application/json")

    @cached_property
    def limit(self):
        """Optional throttle on the number of drugs to return."""
        return int(self.fields.getvalue("limit", "0"))


if __name__ == "__main__":
    """Only execute if invoked directly, not imported as a module."""

    control = Control()
    try:
        control.run()
    except Exception as e:
        message = "failure getting drug info"
        control.logger.exception(message)
        control.send_page(f"{message}: {e}", text_type="plain")
