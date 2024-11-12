#!/usr/bin/env python

"""Menu for editing CDR linking tables.
"""

from functools import cached_property
from cdrcgi import Controller


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
            link = page.menu_link(script, name, id=id)
            link.set("target", "_blank")
            ul.append(page.B.LI(link))
        fieldset.append(ul)
        page.form.append(fieldset)
        page.add_css("""
#link-type-list ul { list-style-type: none; column-width: 15rem; }
#link-type-list a { text-decoration: none; }
#link-type-list a:visited { color: """ + page.LINK_COLOR + """; }
""")

    def run(self):
        """Override base class to add action for new button."""

        if self.request == self.ADD_NEW_LINK_TYPE:
            opts = dict(linkact="addlink")
            self.navigate_to(self.EDIT_LINK_TYPE, self.session.name, **opts)
        elif self.request == self.SHOW_ALL:
            self.navigate_to(self.SHOW_ALL_LINK_TYPES, self.session.name)
        else:
            Controller.run(self)

    def show_form(self):
        """Populate an HTML page with a form and fields and send it."""

        self.populate_form(self.form_page)
        B = self.form_page.B
        classes = B.CLASS("button usa-button")
        opts = dict(type="submit", name=self.REQUEST)
        for button in self.buttons:
            button = B.INPUT(classes, value=button, **opts)
            self.form_page.form.append(button)
        for alert in self.alerts:
            message = alert["message"]
            del alert["message"]
            self.form_page.add_alert(message, **alert)
        self.form_page.send()

    @cached_property
    def alerts(self):
        """Show a message indicating successful deletion."""

        if self.deleted:
            message = f"Successfully deleted link type {self.deleted!r}."
            return [dict(message=message, type="success")]
        return []

    @cached_property
    def buttons(self):
        """Override to specify custom buttons for this page."""
        return self.ADD_NEW_LINK_TYPE, self.SHOW_ALL

    @cached_property
    def deleted(self):
        """Name of link type which was just successfully deleted, if any."""
        return self.fields.getvalue("deleted")

    @cached_property
    def link_types(self):
        """List of existing link types for the menu."""

        query = self.Query("link_type", "id", "name").order("name")
        rows = query.execute(self.cursor).fetchall()
        return [tuple(row) for row in rows]

    @cached_property
    def returned(self):
        """True if we returned here in an automatically opened browser tab."""
        return self.fields.getvalue("returned")

    @cached_property
    def same_window(self):
        """If this browser tab was created automatically, don't open more."""
        return self.buttons if self.deleted or self.returned else []


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
