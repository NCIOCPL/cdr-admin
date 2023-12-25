#!/usr/bin/env python

"""Menu of existing filter sets.
"""

from functools import cached_property
from cdrcgi import Controller
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
        fieldset.set("class", "flexlinks usa-fieldset")
        script = self.EDIT_FILTER_SET
        ul = page.B.UL()
        ul.set("class", "usa-list usa-list--unstyled margin-top-2")
        for id, name in FilterSet.get_filter_sets(self.session):
            link = page.menu_link(script, name, id=id)
            link.set("target", "_blank")
            ul.append(page.B.LI(link))
        fieldset.append(ul)
        page.form.append(fieldset)
        if self.deleted:
            message = f"Successfully deleted {self.deleted}."
            self.alerts.append(dict(message=message, type="success"))

    def run(self):
        """Override base class to add action for new button."""

        if self.request == self.ADD:
            self.navigate_to(self.EDIT_FILTER_SET, self.session.name)
        elif self.request == self.DEEP:
            self.navigate_to(self.SHOW_SETS, self.session.name)
        elif self.request == self.REPORT:
            opts = dict(depth="shallow")
            self.navigate_to(self.SHOW_SETS, self.session.name, **opts)
        else:
            Controller.run(self)

    @property
    def buttons(self):
        """Override to specify custom buttons for this page."""
        return (self.DEEP, self.REPORT, self.ADD)

    @cached_property
    def deleted(self):
        """Name of set which has just been deleted."""
        return self.fields.getvalue("deleted")


if __name__ == "__main__":
    """Don't execute the script if we're loaded as a module."""
    Control().run()
