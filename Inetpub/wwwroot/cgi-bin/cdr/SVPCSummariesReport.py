#!/usr/bin/env python

"""Report on summary documents marked as SVPC summaries.

See https://tracker.nci.nih.gov/browse/OCECDR-5163.
"""

from datetime import date
from functools import cached_property
from urllib.parse import urlparse
from dateutil.relativedelta import relativedelta
from cdr import URDATE
from cdrcgi import Controller


class Control(Controller):

    SUBTITLE = "SVPC Summaries Report"
    LOGNAME = "SVPCSummariesReport"
    OPTS = dict(
        nonpub="Include non-publishable summaries",
        partner="Include linked partner summaries",
        desc="Include description of SVPC summary",
        url="Include summary URL",
        publishable="Display whether the summary is publishable",
    )

    def populate_form(self, page):
        """Add the fields to the report form.

        Pass:
            page - HTMLPage object where the fields go
        """

        end = date.today()
        start = end - relativedelta(months=2)
        fieldset = page.fieldset("Date Range")
        fieldset.append(page.date_field("start", value=start))
        fieldset.append(page.date_field("end", value=end))
        page.form.append(fieldset)
        fieldset = page.fieldset("Language")
        fieldset.append(page.radio_button("lang", value="Any", checked=True))
        fieldset.append(page.radio_button("lang", value="English"))
        fieldset.append(page.radio_button("lang", value="Spanish"))
        page.form.append(fieldset)
        fieldset = page.fieldset("Options")
        for value, label in self.OPTS.items():
            fieldset.append(page.checkbox("opts", value=value, label=label))
        page.form.append(fieldset)
        page.add_output_options("html")

    def build_tables(self):
        """Assemble the report's table."""

        rows = [summary.row for summary in self.summaries]
        return self.Reporter.Table(rows, caption=self.caption, cols=self.cols)

    @cached_property
    def caption(self):
        """Information for the top of the report table."""

        nonpub = "included" if "nonpub" in self.opts else "excluded"
        return [
            f"SVPC Summaries ({len(self.summaries)})",
            f"Language: {self.language}",
            f"Date Range: {self.start} - {self.end[:10]}",
            f"Non-publishable summaries: {nonpub}",
        ]

    @cached_property
    def cols(self):
        """Column headers for the report table."""

        Column = self.Reporter.Column
        cols = [
            Column("CDR ID", width="75px"),
            Column("Title", width="400px"),
            Column("Summary Type", width="150px"),
            Column("Publication Date", width="100px"),
        ]
        if "partner" in self.opts:
            cols.append(Column("Partner Documents", width="350px"))
        if "desc" in self.opts:
            cols.append(Column("Description", width="350px"))
        if "url" in self.opts:
            cols.append(Column("URL", width="300px"))
        if "publishable" in self.opts:
            cols.append(Column("Publishable?", width="100px"))
        return cols

    @cached_property
    def end(self):
        """End of the date range used for filtering the rpoert."""
        end = str(self.parse_date(self.fields.getvalue("end")) or date.today())
        if len(end) == 10:
            end += " 23:59:59"
        return end

    @cached_property
    def language(self):
        """Language selected for filtering the report."""
        return self.fields.getvalue("lang")

    @cached_property
    def opts(self):
        """Report options."""
        return self.fields.getlist("opts")

    @cached_property
    def start(self):
        """Beginning of the date range used for filtering the rpoert."""
        return str(self.parse_date(self.fields.getvalue("start")) or URDATE)

    @cached_property
    def summaries(self):
        """SVPC summaries which meet the report selection criteria."""

        table = "query_term" if "nonpub" in self.opts else "query_term_pub"
        cols = [
            "s.doc_id",
            "t.value AS title",
            "y.value AS summary_type",
            "p.completed AS pub_date",
        ]
        if "desc" in self.opts:
            cols.append("d.value as description")
        if "url" in self.opts:
            cols.append("u.value as url")
        if "publishable" in self.opts:
            cols.append("a.active_status")
            cols.append("v.id AS publishable_id")
        query = self.Query(f"{table} s", *cols).order("s.doc_id").unique()
        query.where("s.path = '/Summary/@SVPC'")
        query.where("s.value = 'Yes'")
        query.join("all_docs a", "a.id = s.doc_id")
        query.join(f"{table} t", "t.doc_id = s.doc_id")
        query.where("t.path = '/Summary/SummaryTitle'")
        query.join(f"{table} y", "y.doc_id = s.doc_id")
        query.where("y.path = '/Summary/SummaryMetaData/SummaryType'")
        if "desc" in self.opts:
            path = "/Summary/SummaryMetaData/SummaryDescription"
            query.join(f"{table} d", "d.doc_id = s.doc_id")
            query.where(f"d.path = '{path}'")
        if "url" in self.opts:
            path = "/Summary/SummaryMetaData/SummaryURL/@cdr:xref"
            query.join(f"{table} u", "u.doc_id = s.doc_id")
            query.where(f"u.path = '{path}'")
        if self.language != "Any":
            query.join(f"{table} l", "l.doc_id = s.doc_id")
            query.where("l.path = '/Summary/SummaryMetaData/SummaryLanguage'")
            query.where(f"l.value = '{self.language}'")
        query.outer("pub_proc_cg c", "c.id = s.doc_id")
        query.outer("pub_proc p", "p.id = c.pub_proc")
        query.where(f"(p.completed IS NULL OR p.completed >= '{self.start}')")
        query.where(f"(p.completed IS NULL OR p.completed <= '{self.end}')")
        if "publishable" in self.opts:
            query.outer("doc_version v",
                        "v.id = s.doc_id AND v.publishable = 'Y'")
        if "nonpub" not in self.opts:
            query.where("a.active_status = 'A'")
        query.log()
        rows = query.execute(self.cursor).fetchall()
        return [Summary(self, row) for row in rows]


class Summary:
    """An SVPC summary selected for the report."""

    def __init__(self, control, row):
        """Capture the values passed to the constructor.

        Pass:
            control - access to the database and to the report options
            row - values from the database for this summary
        """
        self.__control = control
        self.__row = row

    @cached_property
    def partner_docs(self):
        """IDs of partner summaries into which this SVPC summary is merged."""

        query = self.__control.Query("query_term p", "p.doc_id", "t.value")
        query.where("p.path = '/Summary/@PartnerMergeSet'")
        query.where("p.value = 'Yes'")
        query.join("query_term s", "s.doc_id = p.doc_id")
        query.where("s.path = '/Summary/SummaryModuleLink/@cdr:ref'")
        query.where(f"s.int_val = {self.__row.doc_id}")
        query.join("query_term t", "t.doc_id = p.doc_id")
        query.where("t.path = '/Summary/SummaryTitle'")
        query.order("p.doc_id")
        docs = []
        for row in query.execute(self.__control.cursor).fetchall():
            docs.append(f"{row.doc_id} ({row.value})")
        return docs

    @cached_property
    def publication_date(self):
        """When the SVPC summary was published (if ever)."""

        pub_date = self.__row.pub_date
        if not pub_date:
            return ""
        return self.__control.Reporter.Cell(str(pub_date)[:10], center=True)

    @cached_property
    def publishable(self):
        """Indication as to whether the SVPC document is publishable."""

        if self.__row.active_status != 'A' or not self.__row.publishable_id:
            return self.__control.Reporter.Cell("No", center=True)
        return self.__control.Reporter.Cell("Yes", center=True)

    @cached_property
    def row(self):
        """Sequence of values for the report table."""

        values = [
            self.__row.doc_id,
            self.__row.title,
            self.__row.summary_type,
            self.publication_date,
        ]
        if "partner" in self.__control.opts:
            values.append(self.partner_docs)
        if "desc" in self.__control.opts:
            values.append(self.__row.description)
        if "url" in self.__control.opts:
            values.append(self.url)
        if "publishable" in self.__control.opts:
            values.append(self.publishable)
        return values

    @cached_property
    def url(self):
        """The path portion of the summary URL."""

        url = self.__row.url
        if not url:
            return None
        if not url.startswith("http"):
            url = f"https://{url}"
        return urlparse(url).path


if __name__ == "__main__":
    Control().run()
