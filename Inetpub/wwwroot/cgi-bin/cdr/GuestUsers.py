#!/usr/bin/env python

"""Main menu for guest users.
"""

from cdrcgi import Controller


class Control(Controller):

    SUBTITLE = "Guest Users"

    def populate_form(self, page):
        """Add the menu items for guest users."""

        page.body.set("class", "admin-menu")
        ol = page.B.OL()
        page.body.append(ol)
        for display, script in (
            ("Advanced Search", "AdvancedSearch.py"),
            ("Terminology Reports", "TerminologyReports.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))

    @property
    def buttons(self):
        """No buttons are displayed for guest users."""
        return []


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
