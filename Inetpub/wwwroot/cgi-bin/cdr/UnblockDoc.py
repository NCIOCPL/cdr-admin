#!/usr/bin/env python

"""Make a blocked document active.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):

    SUBTITLE = "Unblock CDR Document"

    def populate_form(self, page):
        """Show the form and (if appropriate) processing results.

        Pass:
            page - HTMLPage where everything happens
        """

        # if we have a request, process it and display the outcome.
        if self.doc:
            if self.doc.active_status == Doc.BLOCKED:
                try:
                    self.doc.set_status(Doc.ACTIVE)
                    message = f"Successfully unblocked {self.doc.cdr_id}"
                    message = page.B.P(message, page.B.CLASS("info center"))
                except Exception as e:
                    message = page.B.P(str(e), page.B.CLASS("error center"))
            else:
                message = f"{self.doc.cdr_id} is not blocked"
                message = page.B.P(message, page.B.CLASS("error center"))
            fieldset = page.fieldset("Processing Results")
            fieldset.append(message)
            page.form.append(fieldset)

        # In any case, put up the form requesting a document ID.
        fieldset = page.fieldset("Document To Be Unblocked")
        fieldset.append(page.text_field("id", label="Document ID"))
        page.form.append(fieldset)

    @property
    def show_report(self):
        """Circle back to the form."""
        self.show_form()

    @property
    def doc(self):
        """Document to be unblocked."""

        if not hasattr(self, "_doc"):
            self._doc = self.fields.getvalue("id")
            if self._doc:
                self._doc = Doc(self.session, id=self._doc)
        return self._doc


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
