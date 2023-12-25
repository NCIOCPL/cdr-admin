#!/usr/bin/env python

"""Let the user pick a set of help pages."""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Access to the database and HTML page creation."""

    FILTER = "name:Help Table of Contents"
    SUBTITLE = HELP = "CDR Help"
    PAGES = (
        (365, "User Help"),
        (354511, "Operating Instructions"),
        (256207, "System Information"),
    )
    CSS = "\n".join([
        "form li { list-style-type: none; }",
    ])

    def populate_form(self, page):
        """Show the user the available help pages.

        Required positional argument:
          page - instance of the cdrcgi.HTMLPage class
        """

        fieldset = page.fieldset("Choose Help Page Set")
        checked = True
        for id, label in self.PAGES:
            opts = dict(value=id, label=label, checked=checked)
            fieldset.append(page.radio_button("id", **opts))
            checked = False
        page.form.append(fieldset)

    @cached_property
    def report(self):
        """Override to bypass the form/table module."""

        opts = dict(
            banner=self.title,
            subtitle=self.doc.title.split(";")[0],
            no_results=None,
            page_opts=dict(session=self.session),
        )
        report = self.Reporter(self.title, [], **opts)
        for menu_list in self.lists:
            report.page.form.append(menu_list)
        report.page.add_css(self.CSS)
        return report

    @cached_property
    def lists(self):
        """Nested lists of menu links."""

        root = self.doc.filter(self.FILTER).result_tree.getroot()
        return root.findall("body/ul")

    @cached_property
    def doc(self):
        """The documentation table of contents document to display."""
        return Doc(self.session, id=self.id)

    @cached_property
    def id(self):
        """ID of the table of contents document to render."""
        return self.fields.getvalue("id")

    @cached_property
    def no_results(self):
        """Suppress warning that we have no tables. We know."""
        return None


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
