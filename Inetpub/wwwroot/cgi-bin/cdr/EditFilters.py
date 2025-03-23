#!/usr/bin/env python

from copy import deepcopy
from urllib.parse import urlencode
from cdrcgi import Controller, Reporter
from cdrapi.docs import FilterSet


class Control(Controller):

    COMPARE = "Compare With PROD"
    PARAMS = "Filter Params"
    SUBTITLE = "Manage Filters"
    LOGNAME = "EditFilters"

    @property
    def buttons(self):
        """Figure out which buttons to show."""

        if self.session.tier.name == "PROD":
            return [self.PARAMS]
        return [self.COMPARE, self.PARAMS]

    def populate_form(self, page):
        """Show table of filters.

        Create two tables, one sorted by ID, the other by title.
        One will be visible, the other hidden, controlled by clicking
        on the header for the column to be used for sorting.

        Required positional argument:
          page - object to be populated
        """

        parms = {
            self.SESSION: self.session,
            self.REQUEST: "View",
            "full": "full",
        }
        ids = []
        rows = []
        for doc in FilterSet.get_filters(self.session):
            parms[self.DOCID] = doc.cdr_id
            url = f"EditFilter.py?{urlencode(parms)}"
            id_cell = Reporter.Cell(doc.cdr_id, href=url, target="_blank")
            ids.append((doc.id, id_cell, doc.title))
            rows.append((id_cell, doc.title))
        columns = (
            Reporter.Column("CDR ID", classes="id-col"),
            Reporter.Column("Filter Title", classes="title-col"),
        )
        caption = f"{len(rows):d} CDR Filters (Sorted By Title)"
        opts = dict(caption=caption, columns=columns, id="titlesort")
        opts["logger"] = self.logger
        table = Reporter.Table(rows, **opts)
        page.form.append(table.node)
        rows = [(deepcopy(row[1]), row[2]) for row in sorted(ids)]
        opts["caption"] = f"{len(rows):d} CDR Filters (Sorted By CDR ID)"
        opts["id"] = "idsort"
        table = Reporter.Table(rows, **opts)
        page.form.append(table.node)
        page.add_css("th.clickable { cursor: pointer; }")
        page.head.append(page.B.SCRIPT(src="/js/EditFilters.js"))

    def run(self):
        """Support our custom commands and bypass a form."""

        if self.request == self.COMPARE:
            self.navigate_to("FilterDiffs.py", self.session.name)
        elif self.request == self.PARAMS:
            self.navigate_to("GetXsltParams.py", self.session.name)
        else:
            Controller.run(self)


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
