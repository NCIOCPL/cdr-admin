#!/usr/bin/env python

"""Menu for editing CDR linking tables.
"""

from cdrcgi import Controller, navigateTo, REQUEST


class Control(Controller):
    """Encapsulates processing logic for building the menu page."""

    SUBTITLE = "Manage Link Types"
    ADD_NEW_LINK_TYPE = "Add New Link Type"
    EDIT_LINK_TYPE = "EditLinkType.py"
    SHOW_ALL = "Show All Link Types"
    SHOW_ALL_LINK_TYPES = "ShowAllLinkTypes.py"

    def populate_form(self, page):
        """Add link type editing links and custom formatting to the page."""

        page.body.set("class", "admin-menu")
        fieldset = page.fieldset("Existing Link Types (click to edit)")
        fieldset.set("id", "link-type-list")
        ul = page.B.UL()
        script = self.EDIT_LINK_TYPE
        for id, name in self.link_types:
            ul.append(page.B.LI(page.menu_link(script, name, id=id)))
        fieldset.append(ul)
        page.form.append(fieldset)
        page.add_css("""
#link-type-list ul { list-style-type: none; column-width: 15rem; }
#link-type-list a { text-decoration: none; }
""")

    def run(self):
        """Override base class to add action for new button."""

        if self.request == self.ADD_NEW_LINK_TYPE:
            opts = dict(linkact="addlink")
            navigateTo(self.EDIT_LINK_TYPE, self.session.name, **opts)
        elif self.request == self.SHOW_ALL:
            navigateTo(self.SHOW_ALL_LINK_TYPES, self.session.name)
        else:
            Controller.run(self)

    def show_form(self):
        """Populate an HTML page with a form and fields and send it."""

        self.populate_form(self.form_page)
        B = self.form_page.B
        classes = B.CLASS("button usa-button")
        opts = dict(type="submit", name=REQUEST)
        for button in self.buttons:
            button = B.INPUT(classes, value=button, **opts)
            self.form_page.form.append(button)
        self.form_page.send()

    @property
    def buttons(self):
        """Override to specify custom buttons for this page."""

        return (
            self.ADD_NEW_LINK_TYPE,
            self.SHOW_ALL,
        )

    @property
    def link_types(self):
        if not hasattr(self, "_link_types"):
            query = self.Query("link_type", "id", "name").order("name")
            rows = query.execute(self.cursor).fetchall()
            self._link_types = [tuple(row) for row in rows]
        return self._link_types


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
