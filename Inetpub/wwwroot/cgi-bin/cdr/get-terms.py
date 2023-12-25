#!/usr/bin/env python
"""JSON API for fetching the names and IDs of the CDR Term documents.
"""

from collections import defaultdict
from functools import cached_property
from json import dumps
from cdrcgi import Controller


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "get-terms API service"
    LOGNAME = "testing"

    def run(self):
        """Overridden because this is not a standard report."""

        query = self.Query("query_term n", "n.doc_id", "n.value").order(1)
        query.join("pub_proc_cg c", "c.id = n.doc_id").unique()
        query.where("n.path = '/Term/PreferredName'")
        terms = defaultdict(list)
        for id, name in query.execute(self.cursor).fetchall():
            for type in self.types.get(id, []):
                type = type.strip()
                if type:
                    if not self.limit or len(terms[type]) < self.limit:
                        terms[type].append(dict(id=id, name=name))
        self.send_page(dumps(terms, indent=2), mime_type="application/json")

    @cached_property
    def limit(self):
        """Optional throttle on the number of terms to return."""
        return int(self.fields.getvalue("limit", "0"))

    @cached_property
    def types(self):
        """Dictionary of term types indexed by CDR Term document ID."""

        query = self.Query("query_term", "doc_id", "value")
        query.where("path = '/Term/TermType/TermTypeName'")
        types = defaultdict(list)
        for id, type in query.execute(self.cursor).fetchall():
            types[id].append(type.strip())
        return types


if __name__ == "__main__":
    """Only execute if invoked directly, not imported as a module."""

    control = Control()
    try:
        control.run()
    except Exception as e:
        control.logger.exception("failure getting terms")
        control.send_page(f"Failure fetching terms: {e}", text_type="plain")
