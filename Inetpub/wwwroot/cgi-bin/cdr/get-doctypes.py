#!/usr/bin/env python
"""JSON API for fetching the names and IDs of the CDR document types.
"""

from json import dumps
from cdrcgi import Controller


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "get-doctypes API service"
    LOGNAME = "testing"

    def run(self):
        """Overridden because this is not a standard report."""

        query = self.Query("doc_type", "id", "name")
        query.where("active = 'Y'")
        types = {}
        for id, name in query.execute(self.cursor).fetchall():
            if name:
                types[name] = id
        self.send_page(dumps(types, indent=2), mime_type="application/json")


if __name__ == "__main__":
    """Only execute if invoked directly, not imported as a module."""

    control = Control()
    try:
        control.run()
    except Exception as e:
        control.logger.exception("failure getting doctypes")
        control.send_page(f"Failure fetching doctypes: {e}", text_type="plain")
