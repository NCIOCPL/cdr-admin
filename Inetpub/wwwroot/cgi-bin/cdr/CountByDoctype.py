#!/usr/bin/env python

"""Generate report of statistics on the most recent weekly export job.
"""

from functools import cached_property
from cdrcgi import Controller


class Control(Controller):
    """Report logic."""

    SUBTITLE = "Publishing Count By Doctype"

    def populate_form(self, page):
        """Show the table directly.

        Required positional argument:
          page - HTMLPage instance
        """

        rows = []
        total = 0
        for doc_type in sorted(self.counts):
            count = self.counts[doc_type]
            total += count
            row = (
                doc_type,
                self.Reporter.Cell(count, right=True),
            )
            rows.append(row)
        row = (
            self.Reporter.Cell("TOTAL", bold=True),
            self.Reporter.Cell(total, bold=True, right=True)
        )
        rows.append(row)
        columns = "Document Type", "Count"
        caption = f"Exported By The Latest Weekly Export Job (#{self.job})"
        table = self.Reporter.Table(rows, columns=columns, caption=caption)
        page.form.append(table.node)
        page.add_css(
            "form table { width: 60%; }\n"
            "th:last-child { text-align: right; }\n"
        )

    @property
    def buttons(self):
        """No buttons needed."""
        return []

    @cached_property
    def counts(self):
        """Find the number of documents publishing for each document type."""

        query = self.Query("doc_type t", "t.name", "COUNT(*) AS n")
        query.join("document d", "d.doc_type = t.id")
        query.join("pub_proc_doc p", "p.doc_id = d.id")
        query.where(query.Condition("pub_proc", self.job))
        query.where("p.failure IS NULL")
        query.group("t.name")
        rows = query.execute(self.cursor).fetchall()
        return dict([tuple(row) for row in rows])

    @property
    def job(self):
        """Last successful full export publishing job."""

        if not hasattr(self, "_job"):
            query = self.Query("pub_proc", "MAX(id) AS id")
            query.where("pub_subset = 'Export'")
            query.where("status = 'Success'")
            self._job = query.execute(self.cursor).fetchall()[0].id
        return self._job


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
