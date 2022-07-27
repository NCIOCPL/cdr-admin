#!/usr/bin/env python

from copy import deepcopy
from urllib.parse import urlencode
from cdrcgi import Controller, Reporter, navigateTo, DOCID, SESSION, REQUEST
from cdrapi.docs import FilterSet


class Control(Controller):

    COMPARE = "Compare With PROD"
    PARAMS = "Filter Params"
    SUBTITLE = "Manage Filters"
    # LOGLEVEL = "DEBUG"
    LOGNAME = "EditFilters"

    @property
    def buttons(self):
        """Figure out which buttons to show."""

        buttons = [
            self.PARAMS,
            self.ADMINMENU,
            self.LOG_OUT,
        ]
        if not self.session.tier.name == "PROD":
            buttons.insert(0, self.COMPARE)
        return buttons

    def build_tables(self):
        parms = {SESSION: self.session, REQUEST: "View", "full": "full"}
        ids = []
        rows = []
        for doc in FilterSet.get_filters(self.session):
            parms[DOCID] = doc.cdr_id
            url = f"EditFilter.py?{urlencode(parms)}"
            id_cell = Reporter.Cell(doc.cdr_id, href=url)
            ids.append((doc.id, id_cell, doc.title))
            rows.append((id_cell, doc.title))
        columns = (
            Reporter.Column("CDR ID", classes="id-col"),
            Reporter.Column("Filter Title", classes="title-col"),
        )
        caption = f"{len(rows):d} CDR Filters (Sorted By Title)"
        opts = dict(caption=caption, columns=columns, id="titlesort")
        opts["logger"] = self.logger
        tables = [Reporter.Table(rows, **opts)]
        rows = [(deepcopy(row[1]), row[2]) for row in sorted(ids)]
        opts["caption"] = f"{len(rows):d} CDR Filters (Sorted By CDR ID)"
        opts["id"] = "idsort"
        tables.append(Reporter.Table(rows, **opts))
        return tables

    def run(self):
        """Support our custom commands and bypass a form."""

        if not self.request:
            self.show_report()
        elif self.request == self.COMPARE:
            navigateTo("FilterDiffs.py", self.session.name)
        elif self.request == self.PARAMS:
            navigateTo("GetXsltParams.py", self.session.name)
        else:
            Controller.run(self)

    @property
    def report(self):
        buttons = []
        for button in self.buttons:
            buttons.append(self.HTMLPage.button(button))
        if not hasattr(self, "_report"):
            opts = dict(
                banner=self.title,
                subtitle=self.subtitle,
                page_opts=dict(
                    buttons=buttons,
                    action=self.script,
                    session=self.session,
                ),
            )
            tables = self.build_tables()
            self._report = Reporter(self.title, tables, **opts)
            self._report.page.add_script("""\
function toggle(show, hide) {
    jQuery(show).show();
    jQuery(hide).hide();
}
jQuery(function() {
    jQuery("#idsort .title-col").click(function() {
        toggle("#titlesort", "#idsort");
    });
    jQuery("#titlesort .id-col").click(function() {
        toggle("#idsort", "#titlesort");
    });
    jQuery("#idsort .title-col").addClass("clickable")
    jQuery("#titlesort .id-col").addClass("clickable")
    jQuery("#idsort").hide();
    jQuery("#titlesort").show();
    console.log('ready');
});""")

        return self._report


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
