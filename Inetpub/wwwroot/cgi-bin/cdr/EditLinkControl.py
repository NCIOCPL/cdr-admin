#!/usr/bin/env python

"""Menu for editing CDR linking tables.
"""

from cdrcgi import Controller, navigateTo
from cdrapi.docs import LinkType

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
        fieldset.set("class", "flexlinks")
        ul = page.B.UL()
        script = self.EDIT_LINK_TYPE
        parms = dict(linkact="modlink")
        for link_type in self.link_types:
            parms["name"] = link_type
            ul.append(page.B.LI(page.menu_link(script, link_type, **parms)))
        fieldset.append(ul)
        page.form.append(fieldset)
        page.add_css(".flexlinks ul { height: 400px; }")

    def run(self):
        """Override base class to add action for new button."""

        if self.request == self.ADD_NEW_LINK_TYPE:
            opts = dict(linkact="addlink")
            navigateTo(self.EDIT_LINK_TYPE, self.session.name, **opts)
        elif self.request == self.SHOW_ALL:
            navigateTo(self.SHOW_ALL_LINK_TYPES, self.session.name)
        else:
            Controller.run(self)

    @property
    def buttons(self):
        """Override to specify custom buttons for this page."""

        return (
            self.ADD_NEW_LINK_TYPE,
            self.SHOW_ALL,
            self.DEVMENU,
            self.ADMINMENU,
            self.LOG_OUT
        )

    @property
    def link_types(self):
        if not hasattr(self, "_link_types"):
            self._link_types = LinkType.get_linktype_names(self.session)
        return self._link_types


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
