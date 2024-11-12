#!/usr/bin/env python

"""Make a blocked document active.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):

    SUBTITLE = "Unblock CDR Document"

    def populate_form(self, page):
        """Show the form and (if appropriate) processing results.

        Pass:
            page - HTMLPage where everything happens
        """

        fieldset = page.fieldset("Document To Be Unblocked")
        fieldset.append(page.text_field("id", label="Document ID"))
        page.form.append(fieldset)

    def show_report(self):
        """Process the request and circle back to the form."""

        if not self.doc:
            message = "A CDR document ID is required."
            self.alerts.append(dict(message=message, type="error"))
        else:
            try:
                if self.doc.active_status == Doc.BLOCKED:
                    self.doc.set_status(Doc.ACTIVE)
                    message = f"Successfully unblocked {self.doc.cdr_id}."
                    self.alerts.append(dict(message=message, type="success"))
                else:
                    message = f"{self.doc.cdr_id} is not blocked."
                    self.alerts.append(dict(message=message, type="warning"))
            except Exception as e:
                message = f"Unblock failed: {e}"
                self.alerts.append(dict(message=message, type="error"))
        self.show_form()

    @cached_property
    def doc(self):
        """Document to be unblocked."""

        id = self.fields.getvalue("id")
        return Doc(self.session, id=id) if id else None

    @cached_property
    def same_window(self):
        """Don't open new browser tabs."""
        return [self.SUBMIT]


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
