#!/usr/bin/env python

"""Display a table containing information about all link types.
"""

from cdrcgi import Controller, navigateTo


class Control(Controller):

    SUBTITLE = "Show All Link Types"
    SUBMIT = None
    SUBMENU = "Link Menu"
    LINK_URL = "EditLinkControl.py"
    CAPTION = "All Available Linking Element Combinations"
    COLUMNS = (
        "Link Type",
	"Source Doctype",
	"Linking Element",
	"Target Doctype",
	"Pub/Ver/Cwd",
    )
    FIELDS = (
        "ltp.name AS link_type",
        "sdt.name AS source_doc_type",
        "xml.element AS linking_element",
        "tdt.name AS target_doc_type",
        "ltp.chk_type AS version_selector",
    )

    def run(self):
        """Override to provide custom routing, bypassing forms."""

        if self.request == self.SUBMENU:
            navigateTo(self.LINK_URL, self.session.name)
        elif not self.request:
            try:
                self.show_report()
            except Exception as e:
                self.logger.exception("Report failure")
                self.bail(e)
        else:
            Controller.run(self)

    def build_tables(self):
        """This report has only a single table."""
        return self.table

    @property
    def table(self):
        if not hasattr(self, "_table"):
            opts = dict(caption=self.CAPTION, columns=self.COLUMNS)
            self._table = self.Reporter.Table(self.rows, **opts)
            self._table.node.set("style", "width: 80%;")
        return self._table

    @property
    def rows(self):
        """Table rows for the report."""

        if not hasattr(self, "_rows"):
            query = self.Query("link_xml xml", *self.FIELDS).unique()
            query.join("link_type ltp", "ltp.id = xml.link_id")
            query.join("link_target ltg", "ltg.source_link_type = ltp.id")
            query.join("doc_type sdt", "sdt.id = xml.doc_type")
            query.join("doc_type tdt", "tdt.id = ltg.target_doc_type")
            rows = query.execute(self.cursor).fetchall()
            self._rows = []
            for row in rows:
                self._rows.append([
                    row.link_type,
                    row.source_doc_type,
                    row.linking_element,
                    row.target_doc_type,
                    self.Reporter.Cell(row.version_selector, center=True),
                ])
        return self._rows


if __name__ == "__main__":
    "Don't execute the script if loaded as a module."""
    Control().run()
