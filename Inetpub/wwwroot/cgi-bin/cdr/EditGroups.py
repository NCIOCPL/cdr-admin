#!/usr/bin/env python

"""Menu for editing CDR groups.
"""

from functools import cached_property
from cdrcgi import Controller


class Control(Controller):
    """Encapsulates processing logic for building the menu page."""

    SUBTITLE = "Manage Groups"
    LOGNAME = "ManageGroups"
    ADD_NEW_GROUP = "Add New Group"
    EDIT_GROUP = "EditGroup.py"

    def run(self):
        """Override base class to add action for new button."""
        if self.request == self.ADD_NEW_GROUP:
            self.navigate_to(self.EDIT_GROUP, self.session.name)
        else:
            Controller.run(self)

    def populate_form(self, page):
        """Add group editing links to the page."""
        page.body.set("class", "admin-menu")
        fieldset = page.fieldset("Existing Groups (click to edit)")
        fieldset.set("id", "group-list")
        script = self.EDIT_GROUP
        ul = page.B.UL()
        for group in self.session.list_groups():
            link = page.menu_link(script, group, grp=group)
            if not self.deleted and not self.returned:
                link.set("target", "_blank")
            ul.append(page.B.LI(link))
        fieldset.append(ul)
        page.form.append(fieldset)
        page.add_css("""
#group-list ul { list-style-type: none; column-width: 15rem; }
#group-list a { text-decoration: none; }
""")

    @cached_property
    def alerts(self):
        """Let the user know if we successfully deleted an action."""

        if self.deleted:
            message = f"Successfully deleted group {self.deleted!r}."
            return [dict(message=message, type="success")]
        return []

    @property
    def buttons(self):
        """Override to specify custom button for this page."""
        return [self.ADD_NEW_GROUP]

    @cached_property
    def deleted(self):
        """Name of group which was just deleted, if appropriate."""
        return self.fields.getvalue("deleted")

    @cached_property
    def returned(self):
        """True if user clicked the Group Menu button on the editing form."""
        return True if self.fields.getvalue("returned") else False

    @cached_property
    def same_window(self):
        """Don't multiply browser tabs recursively."""
        return self.buttons if self.deleted or self.returned else []


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
