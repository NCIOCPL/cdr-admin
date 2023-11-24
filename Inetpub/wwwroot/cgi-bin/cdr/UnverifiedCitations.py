#!/usr/bin/env python

"""Report on citations which have not been verified.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Access to the database for report generation."""

    SUBTITLE = "Unverified Citations Report"
    COLUMNS = "Doc ID", "Citation", "Comment"
    INSTRUCTIONS = (
        "Press Submit to generate an HTML table showing the CDR ",
        "Citation",
        " documents whose ",
        "VerificationDetails/Verified",
        " element has 'No' as its string content. The report table "
        "has three columns. The first column contains the CDR document "
        "ID. The second column shows the contents of the ",
        "FormattedReference",
        " element of the QC report resulting from filtering the "
        "document. The third column cotains the text content of the ",
        "Comment",
        " element of that QC report. The report is ordered by CDR document "
        "ID, oldest documents appearing first.",
    )

    def build_tables(self):
        """Build and show the table for the report."""

        opts = dict(caption=self.caption, columns=self.COLUMNS)
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Explain how the report works.

        Required positional argument
          page - instance of the cdrcgi.HTMLPage class
        """

        fieldset = page.fieldset("Instructions")
        segments = []
        code = False
        for segment in self.INSTRUCTIONS:
            if code:
                segments.append(page.B.CODE(segment))
            else:
                segments.append(segment)
            code = not code
        fieldset.append(page.B.P(*segments))
        page.form.append(fieldset)
        page.add_css("fieldset p code { color: purple; }")

    def show_report(self):
        """Override to apply some custom styling."""

        self.report.page.add_css("table { width: 95%; }")
        self.report.send()

    @cached_property
    def caption(self):
        """String to display at the top of the report table."""
        return f"{len(self.rows)} Unverified Citations"

    @cached_property
    def citations(self):
        """Unverified citations to be reflected in the report."""

        query = self.Query("query_term", "doc_id").unique().order("doc_id")
        query.where("path = '/Citation/VerificationDetails/Verified'")
        query.where("value = 'No'")
        rows = query.execute(self.cursor).fetchall()
        return [Citation(Doc(self.session, id=row.doc_id)) for row in rows]

    @cached_property
    def rows(self):
        """Values for the report table."""
        return [citation.row for citation in self.citations]


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

    @cached_property
    def row(self):
        """Values to be displayed in the report for this citation doc."""
        return self.__doc.id, self.citation, self.comment

    @cached_property
    def citation(self):
        """Formatted bibliographic citation."""
        return Doc.get_text(self.root.find("FormattedReference"))

    @cached_property
    def comment(self):
        """Comment pulled from the filtered citation document."""
        return Doc.get_text(self.root.find("Comment"))

    @cached_property
    def root(self):
        """Top node of the filtered citation document."""
        return self.__doc.filter(*self.FILTERS).result_tree.getroot()


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
