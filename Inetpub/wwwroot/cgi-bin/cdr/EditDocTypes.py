#!/usr/bin/env python

"""Menu for editing CDR document types.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doctype


class Control(Controller):
    """Encapsulates processing logic for building the menu page."""

    ADD_NEW_DOCTYPE = "Add New Document Type"
    EDIT_DOCTYPE = "EditDocType.py"
    SUBTITLE = "Manage Document Types"

    def run(self):
        """Override base class to add action for new button."""
        if self.request == self.ADD_NEW_DOCTYPE:
            self.navigate_to(self.EDIT_DOCTYPE, self.session.name)
        else:
            Controller.run(self)

    def populate_form(self, page):
        """Add doctype editing links and some custom styling to the page."""

        page.body.set("class", "admin-menu")
        fieldset = page.fieldset("Existing Document Types (click to edit)")
        fieldset.set("id", "doc-type-list")
        ul = page.B.UL()
        script = self.EDIT_DOCTYPE
        for doctype in Doctype.list_doc_types(self.session):
            link = page.menu_link(script, doctype, doctype=doctype)
            if not self.deleted and not self.returned:
                link.set("target", "_blank")
            ul.append(page.B.LI(link))
        fieldset.append(ul)
        page.form.append(fieldset)
        page.add_css("""
#doc-type-list ul { list-style-type: none; column-width: 15rem; }
#doc-type-list a { text-decoration: none; }
""")

    @cached_property
    def alerts(self):
        """Let the user know if we successfully deleted a document type."""

        if self.deleted:
            message = f"Successfully deleted document type {self.deleted!r}."
            return [dict(message=message, type="success")]
        return []

    @property
    def buttons(self):
        """Override to specify custom button for this page."""
        return [self.ADD_NEW_DOCTYPE]

    @cached_property
    def deleted(self):
        """Name of document type which was just deleted, if appropriate."""
        return self.fields.getvalue("deleted")

    @cached_property
    def returned(self):
        """True if the user clicked a Save on the editing form."""
        return True if self.fields.getvalue("returned") else False

    @cached_property
    def same_window(self):
        """Don't multiply browser tabs recursively."""
        return self.buttons if self.deleted or self.returned else []


if __name__ == "__main__":
    """Don't execute the script if we're loaded as a module."""
    Control().run()
