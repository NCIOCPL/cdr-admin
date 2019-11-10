#!/usr/bin/env python

"""Show recently published media documents.

Split out from PubStatsByDate.py.
"""

from cdrcgi import Controller
import datetime


class Control(Controller):
    """Access to the database and report-generation tools."""

    SUBTITLE = "Media Doc Publishing Report"
    AUDIENCES = "Patients", "Health Professionals"
    PATHS = (
        "/Media/MediaContent/Captions/MediaCaption/@audience",
        "/Media/MediaContent/ContentDescriptions/ContentDescription/@audience",
    )
    COLUMNS = (
        "CDR ID",
        "Media Title",
        "First Pub Date",
        "Version Date",
        "Last Version Publishable",
        "Blocked from VOL",
    )
    FIELDS = (
        "t.doc_id",
        "t.value AS title",
        "d.first_pub",
        "v.dt",
        "b.value as blocked",
        "v.publishable",
    )

    def build_tables(self):
        """Assemble the published media documents table."""

        start = str(self.start)[:10]
        end = str(self.end)[:10]
        caption = f"Media Documents Published Between {start} and {end}"
        opts = dict(caption=caption, columns=self.COLUMNS)
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Ask the user for the report's parameters.

        Pass:
            page - HTMLPage object where we put the form
        """

        end = datetime.date.today()
        start = end - datetime.timedelta(7)
        fieldset = page.fieldset("Date Range")
        fieldset.append(page.date_field("start", value=start))
        fieldset.append(page.date_field("end", value=end))
        page.form.append(fieldset)
        page.form.append(page.hidden_field("doctype", "Media"))
        page.form.append(page.hidden_field("VOL", "Y"))
        fieldset = page.fieldset("Audience(s)")
        for audience in self.AUDIENCES:
            opts = dict(value=audience, checked=True)
            fieldset.append(page.checkbox("audience", **opts))
        page.form.append(fieldset)

    @property
    def audience(self):
        """Audience selected from the form, if only one."""

        if not hasattr(self, "_audience"):
            self._audience = None
            audiences = self.fields.getlist("audience")
            if len(audiences) == 1:
                self._audience = audiences[0]
        return self._audience

    @property
    def end(self):
        """End of the date range for the report."""

        if not hasattr(self, "_end"):
            end = self.fields.getvalue("end", str(self.started))[:10]
            self._end = f"{end} 23:59:59"
        return self._end

    @property
    def rows(self):
        """Values for the report table."""

        subquery = self.Query("pub_proc_doc d", "d.doc_id").unique()
        subquery.join("pub_proc p", "p.id = d.pub_proc")
        subquery.where(subquery.Condition("p.started", self.start, ">="))
        subquery.where(subquery.Condition("p.started", self.end, "<="))
        subquery.where("p.pub_subset LIKE 'Push%'")
        subquery.where("p.status = 'Success'")
        subquery.where("d.removed = 'N'")
        last_ver = self.Query("doc_version", "MAX(num)").where("id = v.id")
        query = self.Query("query_term t", *self.FIELDS).unique()
        query.order("t.value")
        query.join("doc_version v", "t.doc_id = v.id")
        query.join("document d", "v.id = d.id")
        query.join("query_term c", "t.doc_id = c.doc_id")
        query.outer("query_term b", "t.doc_id = b.doc_id",
                    "b.path = '/Media/@BlockedFromVOL'")
        query.where("t.path = '/Media/MediaTitle'")
        query.where("c.path = '/Media/MediaContent/Categories/Category'")
        query.where("c.value NOT IN ('pronunciation', 'meeting recording')")
        query.where(query.Condition("d.id", subquery, "IN"))
        query.where(query.Condition("v.num", last_ver))
        if self.audience:
            query.join("query_term_pub a", "a.doc_id = d.doc_id")
            query.where(query.Condition("a.path", self.PATHS, "IN"))
            query.where(query.Condition("a.value", self.audience))
        rows = []
        for row in query.execute(self.cursor).fetchall():
            #for id, title, first, verDt, audDt, volFlag, ver, \
            #    publishable in mediaRecords:
            url = f"GetCdrImage.py?id=CDR{row.doc_id}.jpg"
            first_pub = str(row.first_pub)[:10] if row.first_pub else ""
            version_date = str(row.dt)[:10] if row.dt else ""
            blocked = row.blocked[0] if row.blocked else ""
            rows.append([
                self.Reporter.Cell(row.doc_id, href=url, center=True),
                row.title,
                self.Reporter.Cell(first_pub, center=True),
                self.Reporter.Cell(version_date, center=True),
                self.Reporter.Cell(row.publishable, center=True),
                self.Reporter.Cell(blocked, center=True),
            ])
        return rows

    @property
    def start(self):
        """Beginning of the date range for the report."""

        if not hasattr(self, "_start"):
            self._start = self.fields.getvalue("start", "2001-01-01")[:10]
        return self._start


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
