#!/usr/bin/env python

"""Report on citations which have not been verified.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Access to the database for report generation."""

    SUBTITLE = "Unverified Citations Report"
    COLUMNS = "Doc ID", "Citation", "Comment"

    def show_form(self):
        """Bypass the form; this report doesn't use one."""
        self.show_report()

    def build_tables(self):
        """Build and show the table for the report."""

        opts = dict(caption=self.caption, columns=self.COLUMNS)
        return self.Reporter.Table(self.rows, **opts)

    def show_report(self):
        """Override to apply some custom styling."""

        self.report.page.add_css("table { width: 95%; }")
        self.report.send()

    @property
    def caption(self):
        """String to display at the top of the report table."""
        return f"{len(self.rows)} Unverified Citations"

    @property
    def citations(self):
        """Unverified citations to be reflected in the report."""

        query = self.Query("query_term", "doc_id").unique().order("doc_id")
        query.where("path = '/Citation/VerificationDetails/Verified'")
        query.where("value = 'No'")
        rows = query.execute(self.cursor).fetchall()
        return [Citation(Doc(self.session, id=row.doc_id)) for row in rows]

    @property
    def rows(self):
        """Values for the report table."""

        if not hasattr(self, "_rows"):
            self._rows = [citation.row for citation in self.citations]
        return self._rows


class Citation:
    """Unverified citation to be shown on the report."""

    FILTERS = (
        "set:Denormalization Citation Set",
        "name:Copy XML for Citation QC Report",
    )

    def __init__(self, doc):
        """Save a reference to the Citation document.

        Pass:
            doc - `Doc` object for this CDR Citation document
        """

        self.__doc = doc

    @property
    def row(self):
        """Values to be displayed in the report for this citation doc."""
        return self.__doc.id, self.citation, self.comment

    @property
    def citation(self):
        """Formatted bibliographic citation."""
        return Doc.get_text(self.root.find("FormattedReference"))

    @property
    def comment(self):
        """Comment pulled from the filtered citation document."""
        return Doc.get_text(self.root.find("Comment"))

    @property
    def root(self):
        """Top node of the filtered citation document."""
        return self.__doc.filter(*self.FILTERS).result_tree.getroot()


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
