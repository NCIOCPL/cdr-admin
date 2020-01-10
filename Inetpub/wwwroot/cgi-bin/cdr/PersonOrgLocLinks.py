#!/usr/bin/env python

"""Report on Person docs linking to Organization address fragments.

Not on the admin menus (invoked from XMetaL).
"""

from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Report logic."""

    SUBTITLE = "Person Document Linking to Organization Address Fragments"
    LOCS = "/Person/PersonLocations"
    PATH = f"{LOCS}/OtherPracticeLocation/OrganizationLocation/@cdr:ref"

    def run(self):
        """Override routing because there is no form for this report."""
        self.show_report()

    def build_tables(self):
        """Return the single table for this report."""
        return self.table

    @property
    def columns(self):
        """Column header definitions for the report."""

        return (
            self.Reporter.Column("Doc ID", width="150px"),
            self.Reporter.Column("Title", width="500px"),
        )

    @property
    def docs(self):
        """Person documents which link to this address fragment."""

        if not hasattr(self, "_docs"):
            query = self.Query("query_term", "doc_id")
            query.where(f"path = '{self.PATH}'")
            query.where(query.Condition("value", self.target))
            self._docs = []
            for row in query.execute(self.cursor).fetchall():
                self._docs.append(Doc(self.session, id=row.doc_id))
        return self._docs

    @property
    def rows(self):
        """Table rows for the report."""

        if not hasattr(self, "_rows"):
            self._rows = []
            for link in sorted(self.docs):
                row = [
                    self.Reporter.Cell(link.cdr_id, center=True),
                    link.title,
                ]
                self._rows.append(row)
            args = len(self.docs), self.target
            self.logger.info("found %d rows linking to %s", *args)
        return self._rows

    @property
    def table(self):
        """This report has only one table."""

        if not hasattr(self, "_table"):
            args = len(self.rows), self.target
            caption = "{:d} Person Documents Linking to {}".format(*args)
            opts = dict(columns=self.columns, caption=caption)
            self._table = self.Reporter.Table(self.rows, **opts)
        return self._table

    @property
    def target(self):
        """Address fragment link target string."""
        return self.fields.getvalue("FragLink")


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
