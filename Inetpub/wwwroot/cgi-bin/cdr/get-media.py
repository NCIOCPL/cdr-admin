#!/usr/bin/env python
"""JSON API for fetching lists of CDR Media documents.
"""

from collections import defaultdict
from functools import cached_property
from json import dumps
from cdrcgi import Controller


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "get-media API service"
    LOGNAME = "testing"

    def run(self):
        """Overridden because this is not a standard report."""

        query = self.Query("document d", "d.id", "d.title").order(1)
        query.join("pub_proc_cg c", "c.id = d.id")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'Media'")
        query.log()
        docs = defaultdict(lambda: defaultdict(list))
        for id, title in query.execute(self.cursor).fetchall():
            pieces = [piece.strip() for piece in title.split(";")]
            language = "es" if pieces[0].endswith("-Spanish") else "en"
            format = pieces[-1]
            node = docs[language][format]
            if self.limit and len(node) >= self.limit:
                continue
            node.append(dict(id=id, title=title))
        self.logger.info("loaded %d media documents", len(docs))
        self.send_page(dumps(docs, indent=2), mime_type="application/json")

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
