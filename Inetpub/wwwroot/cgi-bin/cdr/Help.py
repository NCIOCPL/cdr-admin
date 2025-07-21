#!/usr/bin/env python

"""Let the user pick a set of help pages."""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Access to the database and HTML page creation."""

    TOC_FILTER = "name:Help Table of Contents"
    PAGE_FILTER = "name:Documentation Help Screens Filter"
    SUBTITLE = "CDR Help"
    TOC_ID = 365
    CSS = """\
#help-menu a, #help-menu a:active, #help-menu a:visited, #help-menu a:hover {
  color: #005ea2; text-decoration: none;
}
#help-menu a:hover { text-decoration: underline; }
"""

    def populate_form(self, page):
        """Show help page or list of help pages.

        Required positional argument:
          page - instance of the cdrcgi.HTMLPage class
        """

        if self.id:
            self.send_page(self.help_page)
        else:
            page.form.append(self.toc)
            page.add_css(self.CSS)

    def show_report(self):
        """Redirect back to the form."""
        self.show_form()

    @cached_property
    def buttons(self):
        """No buttons needed."""
        return []

    @cached_property
    def doc(self):
        """The document for the help page to display."""
        return Doc(self.session, id=self.id)

    @cached_property
    def help_page(self):
        """Rendered HTML for the help page."""
        return str(self.doc.filter(self.PAGE_FILTER).result_tree)

    @cached_property
    def id(self):
        """ID of the help page to render."""
        return self.fields.getvalue("id")

    @cached_property
    def same_window(self):
        """Don't open new tabs."""
        return [self.SUBMIT]

    @cached_property
    def toc(self):
        """Menu of help pages."""

        doc = Doc(self.session, id=self.TOC_ID)
        root = doc.filter(self.TOC_FILTER).result_tree.getroot()
        return root.find("body/main/div")


# Don't execute the script if loaded as a module.
if __name__ == "__main__":
    Control().run()
