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

    def show_form(self):
        """Redirect from the unnecessary form straight to the report."""
        self.show_report()

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
