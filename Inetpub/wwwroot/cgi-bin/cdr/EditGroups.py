#!/usr/bin/env python

"""Menu for editing CDR groups.
"""

from cdrcgi import Controller, navigateTo


class Control(Controller):
    """Encapsulates processing logic for building the menu page."""

    ADD_NEW_GROUP = "Add New Group"
    EDIT_GROUP = "EditGroup.py"

    def run(self):
        """Override base class to add action for new button."""
        if self.request == self.ADD_NEW_GROUP:
            navigateTo(self.EDIT_GROUP, self.session.name)
        else:
            Controller.run(self)

    def populate_form(self, page):
        """Add group editing links to the page."""
        page.body.set("class", "admin-menu")
        fieldset = page.fieldset("Existing Groups (click to edit)")
        fieldset.set("class", "flexlinks")
        script = self.EDIT_GROUP
        ul = page.B.UL()
        for group in self.session.list_groups():
            link = page.menu_link(script, group, grp=group)
            ul.append(page.B.LI(link))
        fieldset.append(ul)
        page.form.append(fieldset)
        page.add_css(".flexlinks ul { height: 650px }")

    @property
    def subtitle(self):
        """Dynamically determine what to display under the main banner."""

        if not hasattr(self, "_subtitle"):
            group = self.fields.getvalue("deleted")
            if group:
                self._subtitle = f"Successfully deleted group {group!r}"
            else:
                self._subtitle = "Manage Groups"
        return self._subtitle

    @property
    def buttons(self):
        """Override to specify custom buttons for this page."""
        return self.ADD_NEW_GROUP, self.DEVMENU, self.ADMINMENU, self.LOG_OUT


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
