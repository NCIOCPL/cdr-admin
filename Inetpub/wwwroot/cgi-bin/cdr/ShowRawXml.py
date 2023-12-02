#!/usr/bin/env python

"""Show unformatted XML.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Script logic."""

    LOGNAME = "ShowRawXml"

    def run(self):
        """Override the base class version: no menu and no tables."""
        self.send_page(f"{self.subtitle}\n\n{self.xml}", "plain")

    @cached_property
    def doc(self):
        """The CDR document to display."""

        id = self.fields.getvalue("id")
        if not id:
            self.logger.warning("No CDR ID provided.")
            self.bail("The 'id' parameter is required.")
        return Doc(self.session, id=id)

    @cached_property
    def subtitle(self):
        """String to be displayed under the main banner."""
        return f"CDR Document {self.doc.id}"

    @cached_property
    def xml(self):
        """This is how we can tell the ID was valid."""

        try:
            return self.doc.xml
        except Exception:
            self.logger.exception("Fetching document XML")
            self.bail(f"Failure fetching XML for {self.doc.cdr_id}.")


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
