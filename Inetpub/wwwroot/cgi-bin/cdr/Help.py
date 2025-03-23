#!/usr/bin/env python

"""Let the user pick a set of help pages."""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Access to the database and HTML page creation."""

    FILTER = "name:Help Table of Contents"
    SUBTITLE = "CDR Help"
    PAGES = (
        (365, "User Help"),
        (354511, "Operating Instructions"),
        (256207, "System Information"),
    )
    CSS = """\
#help-menu a, #help-menu a:active, #help-menu a:visited, #help-menu a:hover {
  color: #005ea2; text-decoration: none;
}
#help-menu a:hover { text-decoration: underline; }
"""

    def populate_form(self, page):
        """Show help menu or available menus.

        Required positional argument:
          page - instance of the cdrcgi.HTMLPage class
        """

        if self.id:
            page.form.append(self.menu)
            page.add_css(self.CSS)
        else:
            fieldset = page.fieldset("Choose Help Page Set")
            checked = True
            for id, label in self.PAGES:
                opts = dict(value=id, label=label, checked=checked)
                fieldset.append(page.radio_button("id", **opts))
                checked = False
            page.form.append(fieldset)

    def show_report(self):
        """Redirect back to the form."""
        self.show_form()

    @cached_property
    def buttons(self):
        """Sequence of names for request buttons to be provided."""
        return [] if self.id else [self.SUBMIT]

    @cached_property
    def doc(self):
        """The documentation table of contents document to display."""
        return Doc(self.session, id=self.id)

    @cached_property
    def id(self):
        """ID of the table of contents document to render."""
        return self.fields.getvalue("id")

    @cached_property
    def menu(self):
        """Menu of help pages."""

        root = self.doc.filter(self.FILTER).result_tree.getroot()
        self.logger.info("root=%s", list(root.find("body")))
        return root.find("body/main/div")

    @cached_property
    def same_window(self):
        """Don't open new tabs."""
        return [self.SUBMIT]

    @cached_property
    def subtitle(self):
        """Pick an appropriate value depending on whether a menu is chosen."""

        if self.id:
            subtitle = dict(self.PAGES).get(self.doc.id)
            if subtitle:
                return subtitle
        return self.SUBTITLE


# Don't execute the script if loaded as a module.
if __name__ == "__main__":
    Control().run()
