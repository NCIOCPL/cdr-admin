#!/usr/bin/env python

"""Menu of existing filter sets.
"""

from cdrcgi import Controller, navigateTo
from cdrapi.docs import FilterSet


class Control(Controller):
    """Encapsulates processing logic for building the menu page."""

    SUBTITLE = "Manage Filter Sets"
    ADD = "New Filter Set"
    REPORT = "Report"
    DEEP = "Deep Report"
    EDIT_FILTER_SET = "EditFilterSet.py"
    SHOW_SETS = "ShowFilterSets.py"

    def populate_form(self, page):
        """Add the links editing the filter sets.

        Pass:
            page - HTMLPage object to which we attach the links
        """

        page.body.set("class", "admin-menu")
        fieldset = page.fieldset("Filter Sets (click to edit)")
        fieldset.set("class", "flexlinks")
        script = self.EDIT_FILTER_SET
        ul = page.B.UL()
        for id, name in FilterSet.get_filter_sets(self.session):
            ul.append(page.B.LI(page.menu_link(script, name, id=id)))
        fieldset.append(ul)
        page.form.append(fieldset)

    def run(self):
        """Override base class to add action for new button."""

        if self.request == self.ADD:
            navigateTo(self.EDIT_FILTER_SET, self.session.name)
        elif self.request == self.DEEP:
            navigateTo(self.SHOW_SETS, self.session.name)
        elif self.request == self.REPORT:
            navigateTo(self.SHOW_SETS, self.session.name, depth="shallow")
        else:
            Controller.run(self)

    @property
    def buttons(self):
        """Override to specify custom buttons for this page."""

        return (
            self.DEEP,
            self.REPORT,
            self.ADD,
            self.DEVMENU,
            self.ADMINMENU,
            self.LOG_OUT
        )

    @property
    def subtitle(self):
        """Dynamically determine what to display under the main banner."""

        if not hasattr(self, "_subtitle"):
            set_name = self.fields.getvalue("deleted")
            if set_name:
                self._subtitle = f"Successfully deleted {set_name!r}"
            else:
                self._subtitle = self.SUBTITLE
        return self._subtitle


if __name__ == "__main__":
    """Don't execute the script if we're loaded as a module."""
    Control().run()
