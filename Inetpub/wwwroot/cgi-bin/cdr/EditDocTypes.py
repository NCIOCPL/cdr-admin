#!/usr/bin/env python

"""Menu for editing CDR document types.
"""

from cdrcgi import Controller, navigateTo
from cdrapi.docs import Doctype

class Control(Controller):
    """Encapsulates processing logic for building the menu page."""

    ADD_NEW_DOCTYPE = "Add New Document Type"
    EDIT_DOCTYPE = "EditDocType.py"
    SUBTITLE = "Manage Document Types"

    def run(self):
        """Override base class to add action for new button."""
        if self.request == self.ADD_NEW_DOCTYPE:
            navigateTo(self.EDIT_DOCTYPE, self.session.name)
        else:
            Controller.run(self)

    def populate_form(self, page):
        """Add doctype editing links and some custom styling to the page."""

        page.body.set("class", "admin-menu")
        fieldset = page.fieldset("Existing Document Types (click to edit)")
        fieldset.set("class", "flexlinks")
        ul = page.B.UL()
        script = self.EDIT_DOCTYPE
        for doctype in Doctype.list_doc_types(self.session):
            link = page.menu_link(script, doctype, doctype=doctype)
            ul.append(page.B.LI(link))
        fieldset.append(ul)
        page.form.append(fieldset)
        page.add_css(".flexlinks ul { height: 125px }")

    @property
    def subtitle(self):
        """Dynamically determine what to display under the main banner."""

        if not hasattr(self, "_subtitle"):
            action = self.fields.getvalue("deleted")
            if action:
                self._subtitle = f"Successfully deleted type {action!r}"
            else:
                self._subtitle = "Manage Document Types"
        return self._subtitle

    @property
    def buttons(self):
        """Override to specify custom buttons for this page."""
        return self.ADD_NEW_DOCTYPE, self.DEVMENU, self.ADMINMENU, self.LOG_OUT


if __name__ == "__main__":
    """Don't execute the script if we're loaded as a module."""
    Control().run()
