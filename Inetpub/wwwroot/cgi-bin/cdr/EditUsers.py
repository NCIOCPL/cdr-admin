#!/usr/bin/env python

"""Menu for editing CDR users.
"""

from functools import cached_property
from cdrcgi import Controller


class Control(Controller):
    """Encapsulates processing logic for building the menu page."""

    SUBTITLE = "Manage Users"
    LOGNAME = "ManageUsers"
    ADD_NEW_USER = "Add New User"
    EDIT_USER = "EditUser.py"

    def populate_form(self, page):
        """Add user editing links and custom formatting to the page."""

        page.body.set("class", "admin-menu")
        fieldset = page.fieldset("Existing Users (click to edit)")
        fieldset.set("id", "user-list")
        ul = page.B.UL()
        script = self.EDIT_USER
        for user in self.users:
            display = user.fullname or user.name
            link = page.menu_link(script, display, usr=user.name)
            if user.fullname:
                link.set("title", user.name)
            if not self.deleted and not self.returned:
                link.set("target", "_blank")
            ul.append(page.B.LI(link))
        fieldset.append(ul)
        page.form.append(fieldset)
        page.add_css("""
#user-list ul { list-style-type: none; column-width: 15rem; }
#user-list a { text-decoration: none; }
""")

    def run(self):
        """Override base class to add action for new button."""

        if self.request == self.ADD_NEW_USER:
            self.navigate_to(self.EDIT_USER, self.session.name)
        else:
            Controller.run(self)

    @cached_property
    def alerts(self):
        """Let the user know if we successfully inactivated a user account."""

        if self.deleted:
            message = f"Successfully retired account for user {self.deleted}."
            return [dict(message=message, type="success")]
        return []

    @property
    def buttons(self):
        """Override to specify custom button for this page."""
        return [self.ADD_NEW_USER]

    @cached_property
    def deleted(self):
        """Name of user which was just inactivated, if appropriate."""
        return self.fields.getvalue("deleted")

    @cached_property
    def returned(self):
        """True if the clicked the User Menu button on the editing form."""
        return True if self.fields.getvalue("returned") else False

    @cached_property
    def same_window(self):
        """Don't multiply browser tabs recursively."""
        return self.buttons if self.deleted or self.returned else []

    @cached_property
    def users(self):
        """Users sorted by the best name we have."""

        users = []
        for name in self.session.list_users():
            users.append(self.session.User(self.session, name=name))
        return sorted(users, key=lambda u: (u.fullname or u.name).lower())


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
