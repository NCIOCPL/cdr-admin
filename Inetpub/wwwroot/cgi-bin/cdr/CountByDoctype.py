#!/usr/bin/env python

"""Generate report of statistics on the most recent weekly export job.
"""

from cdrcgi import Controller


class Control(Controller):
    """Report logic."""

    def populate_form(self, page):
        """Skip the form, which isn't needed for this report."""
        self.show_report()

    def build_tables(self):
        """Create the only table needed for the report."""

        rows = []
        total = 0
        for doc_type in self.counts:
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
        caption = f"Documents Exported By Job {self.job}"
        table = self.Reporter.Table(rows, columns=columns, caption=caption)
        return table

    @property
    def counts(self):
        """Find the number of documents publishing for each document type."""

        if not hasattr(self, "_counts"):
            query = self.Query("doc_type t", "t.name", "COUNT(*) AS n")
            query.join("document d", "d.doc_type = t.id")
            query.join("pub_proc_doc p", "p.doc_id = d.id")
            query.where(query.Condition("pub_proc", self.job))
            query.where("p.failure IS NULL")
            query.group("t.name")
            rows = query.execute(self.cursor).fetchall()
            self._counts = dict([tuple(row) for row in rows])
        return self._counts

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
