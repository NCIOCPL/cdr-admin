#!/usr/bin/env python

"""Menu for editing CDR users.
"""

from cdrcgi import Controller, navigateTo


class Control(Controller):
    """Encapsulates processing logic for building the menu page."""

    ADD_NEW_USER = "Add New User"
    EDIT_USER = "EditUser.py"

    def populate_form(self, page):
        """Add user editing links and custom formatting to the page."""

        page.body.set("class", "admin-menu")
        fieldset = page.fieldset("Existing Users (click to edit)")
        fieldset.set("class", "flexlinks")
        ul = page.B.UL()
        script = self.EDIT_USER
        for user in self.users:
            display = user.fullname or user.name
            link = page.menu_link(script, display, usr=user.name)
            if user.fullname:
                link.set("title", user.name)
            ul.append(page.B.LI(link))
        fieldset.append(ul)
        page.form.append(fieldset)

    def run(self):
        """Override base class to add action for new button."""

        if self.request == self.ADD_NEW_USER:
            navigateTo(self.EDIT_USER, self.session.name)
        else:
            Controller.run(self)

    @property
    def buttons(self):
        """Override to specify custom buttons for this page."""
        return self.ADD_NEW_USER, self.DEVMENU, self.ADMINMENU, self.LOG_OUT

    @property
    def subtitle(self):
        """Dynamically determine what to display under the main banner."""

        if not hasattr(self, "_subtitle"):
            user = self.fields.getvalue("deleted")
            if user:
                self._subtitle = f"Successfully retired account for {user!r}"
            else:
                self._subtitle = "Manage Users"
        return self._subtitle

    @property
    def users(self):
        """Users sorted by the best name we have."""

        if not hasattr(self, "_users"):
            users = []
            for name in self.session.list_users():
                users.append(self.session.User(self.session, name=name))
            users = sorted(users, key=lambda u: (u.fullname or u.name).lower())
            self._users = users
        return self._users


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
