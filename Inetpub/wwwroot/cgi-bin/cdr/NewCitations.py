#!/usr/bin/env python

"""Report on Citation documents created during a specified date range.
"""

from cdrcgi import Controller
import datetime
from urllib.parse import urlencode


class Control(Controller):
    """Access to the database and form/report building tools."""

    SUBTITLE = "New Citations Report"
    URL = "https://www.ncbi.nlm.nih.gov/entrez/query.fcgi"

    def build_tables(self):
        """Assemble and return the table for this report."""

        opts = dict(caption=self.caption, columns=self.columns)
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Add a date range to the form.

        Pass:
            page - HTMLPage on which the fields are placed
        """

        end = datetime.date.today()
        start = end - datetime.timedelta(6)
        fieldset = page.fieldset("Report Options")
        opts = dict(label="Start Date", value=start)
        fieldset.append(page.date_field("start", **opts))
        opts = dict(label="End Date", value=end)
        fieldset.append(page.date_field("end", **opts))
        page.form.append(fieldset)

    @property
    def caption(self):
        """String to be displayed above the report table."""

        base = f"{len(self.rows)} Documents Created"
        return self.add_date_range_to_caption(base, self.start, self.end)

    @property
    def columns(self):
        """Column headers for the report table."""

        return (
            self.Reporter.Column("CDR ID"),
            self.Reporter.Column("Document Title"),
            self.Reporter.Column("Created By"),
            self.Reporter.Column("Creation Date", width="80px"),
            self.Reporter.Column("Last Version Pub?"),
            self.Reporter.Column("PMID")
        )

    @property
    def end(self):
        """Date range end selected on the form."""

        try:
            end = self.fields.getvalue("end")
            return self.parse_date(end)
        except Exception:
            self.logger.exception("invalid end date")
            self.bail("Invalid ending date")

    @property
    def start(self):
        """Date range beginning selected on the form."""

        try:
            start = self.fields.getvalue("start")
            return self.parse_date(start)
        except Exception:
            self.logger.exception("invalid start date")
            self.bail("Invalid starting date")

    @property
    def rows(self):
        """Values for the report table.

        We're somewhat constrained by limitations in SQL Server, which
        doesn't know how to handle placeholders in a joined virtual
        table. So we have to embed our date/time values in the query
        string directly. This is safe, because we have scrubbed those
        values with the `parse_date()` method.
        """

        fields = "d.id", "c.dt", "c.usr", "MAX(v.num) AS ver"
        subquery = self.Query("document d", *fields)
        subquery.join("doc_type t", "t.id = d.doc_type")
        subquery.join("audit_trail c", "c.document = d.id")
        subquery.join("action a", "a.id = c.action")
        subquery.outer("doc_version v", "v.id = d.id")
        subquery.where("t.name = 'Citation'")
        subquery.where("a.name = 'ADD DOCUMENT'")
        if self.start:
            subquery.where(f"c.dt >= '{self.start}'")
        if self.end:
            subquery.where(f"c.dt <= '{self.end} 23:59:59'")
        subquery.group("d.id", "c.dt", "c.usr")
        subquery.alias("t")
        pattern = "'/Citation/PubmedArticle/{}/PMID'"
        names = "MedlineCitation", "NCBIArticle"
        paths = ",".join([pattern.format(name) for name in names])
        cols = "d.id", "d.title", "u.name", "t.dt", "v.publishable", "p.value"
        query = self.Query("document d", *cols)
        query.join(subquery, "t.id = d.id")
        query.join("open_usr u", "u.id = t.usr")
        query.outer("doc_version v", "v.id = d.id", "v.num = t.ver")
        query.outer("query_term p", "p.doc_id = d.id", f"p.path IN ({paths})")
        query.order("d.id")
        parms = dict(cmd="Retrieve", db="pubmed", dopt="Abstract")
        citations = []
        for row in query.execute(self.cursor).fetchall():
            if row.value:
                parms["list_uids"] = row.value
                url = f"{self.URL}?{urlencode(parms)}"
                pmid = self.Reporter.Cell(row.value, href=url, target="_blank")
            else:
                pmid = ""
            citations.append([
                row.id,
                row.title,
                row.name,
                str(row.dt)[:10],
                self.Reporter.Cell(row.publishable or "N/A", classes="center"),
                pmid,
            ])
        return citations


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
