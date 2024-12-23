#!/usr/bin/env python
"""Show all URLs for a particular document type.

The SQL came from an ad-hoc query which had been requested to convert
into a regular report.  The report, however, will be run by document
type. (Eliminating Filter type from possible doc types)
"""

from functools import cached_property
from cdrcgi import Controller, BasicWebPage


class Control(Controller):
    """Access to the database and report-generation functionality."""

    SUBTITLE = "URL List Report"
    LOGNAME = "URLListReport"
    COLUMNS = "Doc ID", "Doc Title", "URL", "Display Text", "Source Title"
    QUERIES = dict(Summary="cis_query", DrugInformationSummary="dis_query",
                   GlossaryTermConcept="gtc_query")
    DEFAULT_QUERY = "default_query"

    def populate_form(self, page):
        """Show form with doctypes containing links as selection picklist.

        Pass:
            page - HTMLPage object where the fields go
        """

        fieldset = page.fieldset("Select Document Type For Report")
        checked = True
        for doctype in self.doctypes:
            opts = dict(value=doctype, label=doctype, checked=checked)
            fieldset.append(page.radio_button("doctype", **opts))
            checked = False
        page.form.append(fieldset)
        page.add_output_options(default="html")

    def build_tables(self):
        """Show the report's only table."""

        opts = dict(columns=self.COLUMNS, caption=self.caption)
        return self.Reporter.Table(self.rows, **opts)

    def show_report(self):
        """Report tables are too wide for the standard HTML layout."""

        if self.format == "excel":
            return self.report.send("excel")
        report = BasicWebPage()
        report.wrapper.append(report.B.H1(self.SUBTITLE))
        report.wrapper.append(self.build_tables().node)
        report.wrapper.append(self.footer)
        report.head.append(report.B.STYLE("table { width: 100%; }"))
        report.send()

    @cached_property
    def caption(self):
        """String to be displayed directly above the table."""
        return f"Document Type: {self.doctype}"

    @cached_property
    def cis_query(self):
        """Query for Cancer Information Summaries."""

        fields = "t.doc_id", "t.value", "x.value", "e.value", "s.value"
        query = self.Query("query_term t", *fields).order("t.doc_id")
        query.join("query_term e", "e.doc_id = t.doc_id")
        query.join("query_term x", "x.doc_id = e.doc_id",
                   "x.node_loc = e.node_loc")
        query.outer("query_term s", "s.doc_id = e.doc_id",
                    "s.node_loc = e.node_loc",
                    "s.path LIKE '/Summary%/ExternalRef/@SourceTitle'")
        query.where("t.path = '/Summary/SummaryTitle'")
        query.where("e.path LIKE '/Summary%/ExternalRef'")
        query.where("x.path LIKE '/Summary%/ExternalRef/@cdr:xref'")
        return query

    @cached_property
    def default_query(self):
        """Query for all non-summary document types."""

        fields = "d.id", "d.title", "x.value", "e.value", "s.value"
        query = self.Query("document d", *fields).order("d.id")
        query.join("doc_type t", "t.id = d.doc_type")
        query.join("query_term e", "e.doc_id = d.id")
        query.join("query_term x", "x.doc_id = e.doc_id",
                   "x.node_loc = e.node_loc")
        # Not sure we want to join on x.doc_id instead of s.doc_id
        # I'm leaving it as originally coded
        query.outer("query_term s", "x.doc_id = e.doc_id",
                    "s.node_loc = e.node_loc",
                    "s.path LIKE '%/ExternalRef/@SourceTitle'")
        query.where(query.Condition("t.name", self.doctype))
        query.where("e.path LIKE '%/ExternalRef'")
        query.where("x.path LIKE '%/ExternalRef/@cdr:xref'")
        return query

    @cached_property
    def dis_query(self):
        """Query for Drug Information Summaries."""

        fields = "t.doc_id", "t.value", "x.value", "NULL", "NULL"
        query = self.Query("query_term t", *fields).order("t.doc_id")
        query.join("query_term x", "x.doc_id = t.doc_id")
        query.where("t.path = '/DrugInformationSummary/Title'")
        query.where("x.path LIKE '/Drug%/DrugReferenceLink/@cdr:xref'")
        query.where("x.value IS NOT NULL")
        return query

    @cached_property
    def gtc_query(self):
        """Query for GlossaryTermConcept.
           Users need to find URLs for ExternalRef and RelatedExternalRef."""

        fields = "d.id", "d.title", "x.value", "e.value", "s.value"
        query = self.Query("document d", *fields).order("d.id")
        query.join("doc_type t", "t.id = d.doc_type")
        query.join("query_term e", "e.doc_id = d.id")
        query.join("query_term x", "x.doc_id = e.doc_id",
                   "x.node_loc = e.node_loc")
        query.outer("query_term s", "s.doc_id = e.doc_id",
                    "s.node_loc = e.node_loc",
                    "s.path LIKE '%/%ExternalRef/@SourceTitle'")
        query.where(query.Condition("t.name", self.doctype))
        query.where("e.path LIKE '%/%ExternalRef'")
        query.where("x.path LIKE '%/%ExternalRef/@cdr:xref'")
        return query

    @cached_property
    def doctype(self):
        """Document type selected by the user from the form."""
        return self.fields.getvalue("doctype")

    @cached_property
    def doctypes(self):
        """ID/name tuples for the radio buttons on the form.

        Note that we're not using the first column in the results set,
        but there's a bug in SQL Server which causes the query to run
        more than two orders of magnitude slower without it!
        """

        query = self.Query("doc_type t", "d.doc_type", "t.name").unique()
        query.order("t.name")
        query.join("document d", "d.doc_type = t.id")
        query.join("query_term l", "l.doc_id = d.id")
        query.where("path LIKE '%ExternalRef%'")
        query.where("t.name <> 'Filter'")
        query.log()
        rows = query.execute(self.cursor).fetchall()
        doctypes = [row.name for row in rows] + ["DrugInformationSummary"]
        return sorted(set(doctypes))

    @cached_property
    def rows(self):
        """Values for the report table.

        We're using separate SQL queries depending on the doc-type.
        This used to be a single query connected using a UNION
        statement but CIAT decided they only need the report by
        individual doc-type, so I'm splitting it but keeping the same
        columns for all three types.
        """

        name = self.QUERIES.get(self.doctype, self.DEFAULT_QUERY)
        query = getattr(self, name)
        self.logger.debug(query)
        return query.execute(self.cursor).fetchall()


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
