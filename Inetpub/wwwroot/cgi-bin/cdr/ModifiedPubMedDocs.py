#!/usr/bin/env python

"""Report on citation documents which have changed.
"""

from cdrcgi import Controller


class Control(Controller):

    SUBTITLE = "Modified PubMed Documents"
    COLUMNS = "Doc ID", "Doc Title"

    def show_form(self):
        """Bypass the form, which is not needed for this report."""
        self.show_report()

    def build_tables(self):
        """Return the report's only table."""

        opts = dict(columns=self.COLUMNS, caption=self.caption)
        return self.Reporter.Table(self.rows, **opts)

    def show_report(self):
        """Override to tweak the styling."""

        self.report.page.add_css("table { min-width: 300px; }")
        self.report.send()

    @property
    def caption(self):
        """String displayed at the top of the report table."""
        return f"Modified Documents ({len(self.docs)})"

    @property
    def docs(self):
        """Modified documents for the report."""

        if not hasattr(self, "_docs"):
            query = self.Query("document d", "d.id", "d.title").unique()
            query.join("query_term q", "q.doc_id = d.id")
            query.where("q.path = '/Citation/PubmedArticle/ModifiedRecord'")
            query.where("q.value = 'Yes'")
            self._docs = query.order("d.title").execute(self.cursor).fetchall()
        return self._docs

    @property
    def rows(self):
        """Table rows for the report."""

        if not hasattr(self, "_rows"):
            params = dict(Filter="name:Citation QC Report")
            self._rows = []
            for doc in self.docs:
                cdr_id = f"CDR{doc.id:010d}"
                title = doc.title.strip()[:100]
                if len(title) > 100:
                    title += " ..."
                params["DocId"] = cdr_id
                url = self.make_url("Filter.py", **params)
                row = self.Reporter.Cell(cdr_id, href=url), title
                self._rows.append(row)
        return self._rows


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
