#!/usr/bin/env python3

"""Show linking summaries updated for a title change in the linked summary.
"""

from cdrapi.docs import Doc
from cdrcgi import Controller
from re import compile


class Control(Controller):
    """Top-level driver for the report's logic."""

    SUBTITLE = "Updated SummaryRef Titles"
    LOGNAME = "updated-summaryref-titles"
    COLS = "Linking Doc ID", "Linked Doc ID", "Updated"
    CAPTION = "Updates"
    EXPRESSION = compile(r"for (CDR\d+) (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)")
    INSTRUCTIONS = (
        "This report shows summary documents in which the denormalized "
        "titles in SummaryRef elements have been updated by a global change "
        "job to reflect modifications in the titles of the linked summaries. "
        "Each row in the report has three columns, showing the CDR ID of the "
        "linking and linked summary documents, as well as the date and time "
        "when each linking document was modified."
    )

    def populate_form(self, page):
        """Explain the report.

        Required positional argument:
          page - instance of the HTMLPage class
        """

        if not self.fields.getvalue("prompt"):
            self.show_report()
        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)

    def build_tables(self):
        """Assemble the report table."""

        query = self.Query("doc_version", "id", "comment").unique()
        query.where("comment LIKE 'Updating SummaryRef titles (OCECDR-5068)%'")
        query.order("comment DESC", "id")
        rows = []
        for id, comment in query.execute(self.cursor).fetchall():
            match = self.EXPRESSION.search(comment)
            if match:
                row = Doc.normalize_id(id), match.group(1), match.group(2)
                rows.append(row)
        return self.Reporter.Table(rows, cols=self.COLS, caption=self.CAPTION)


if __name__ == "__main__":
    Control().run()
