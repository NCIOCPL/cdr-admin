#!/usr/bin/env python

"""Main menu for advanced search forms.
"""

from cdrcgi import Controller


class Control(Controller):
    """Logic for dynamic construction of the top-level CDR admin menu."""

    SUBTITLE = "Main Menu"
    BOARD_MANAGERS = "Board Manager Menu Users"
    CIAT_OCCM = "CIAT/OCCM Staff Menu Users"
    DEV_SA = "Developer/SysAdmin Menu Users"
    MENUS = (
        (BOARD_MANAGERS, "BoardManagers.py", "OCC Board Managers"),
        (CIAT_OCCM, "CiatCipsStaff.py", "CIAT/OCC Staff"),
        (DEV_SA, "DevSA.py", "Developers/System Administrators"),
    )

    def populate_form(self, page):
        """Add the menu links available for this user.

        If the user only has one menu option, go there directly.
        """

        page.body.set("class", "admin-menu")
        links = []
        for group, filename, label in self.MENUS:
            if group in self.user.groups:
                script = filename
                links.append(page.B.LI(page.menu_link(script, label)))
        if not links:
            script = "GuestUsers.py"
            links = [page.B.LI(page.menu_link(script, "Guest User"))]
        if len(links) == 1:
            self.navigate_to(script, self.session.name)
        page.form.append(page.B.OL(*links))

    @property
    def buttons(self):
        """This menu only needs one button."""
        return [self.LOG_OUT]

    @property
    def user(self):
        """Access to which groups the current user belongs to."""

        if not hasattr(self, "_user"):
            opts = dict(name=self.session.user_name)
            self._user = self.session.User(self.session, **opts)
        return self._user


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
