#!/usr/bin/env python

"""Help the users find the menu choices.
"""

from functools import cached_property
from cdrcgi import Controller


class Control(Controller):
    """Show the CDR Admin menu hierarchies."""

    SUBTITLE = "Show Menu Hierarchy"
    LOGNAME = "show-menu-hierarchy"
    CSS = """\
fieldset ul { list-style: none; }
fieldset > ul > li { margin-top: 1rem; }
fieldset > ul > li > span { font-weight: bold; }
"""

    def populate_form(self, page):
        """Ask the user for the report parameters.

        Pass:
            page - HTMLPage object where the fields go
        """

        menus = page.user_menus
        menu = None
        if len(menus) == 1:
            menu = menus[0]
        elif self.menu:
            for m in menus:
                if m["label"] == self.menu:
                    menu = m
                    break
            if menu is None:
                message = f"Menu {self.menu} is not available."
                alert = {"message": message, "type": "warning"}
                self.alerts.append(alert)
        if menu:
            fieldset = page.fieldset(menu["label"])
            fieldset.append(self.make_list(menu["children"], page))
        else:
            fieldset = page.fieldset("Choose Menu")
            choices = page.B.UL()
            for menu in menus:
                label = menu["label"]
                link = page.menu_link(self.script, label, menu=label)
                choices.append(page.B.LI(link))
            fieldset.append(choices)
        page.form.append(fieldset)
        page.add_css(self.CSS)

    @cached_property
    def menu(self):
        """Name of the menu to display."""
        return self.fields.getvalue("menu")

    def make_list(self, children, page):
        """Create a possible nested list of menu choices.

        Pass:
            children - list of items in a menu
            page - HTMLPage object

        Return:
            lxml object for a UL element
        """

        ul = page.B.UL()
        for child in children:
            content = [page.B.SPAN(child["label"])]
            grandchildren = child.get("children")
            if grandchildren:
                content.append(self.make_list(grandchildren, page))
            ul.append(page.B.LI(*content))
        return ul

    @cached_property
    def buttons(self):
        """No buttons are needed on this page."""
        return []


# Only execute if loaded as a script.
if __name__ == "__main__":
    Control().run()
