#!/usr/bin/env python
"""
Report listing all URLs for a particular document type

The SQL came from an ad-hoc query which had been requested to convert
into a regular report.  The report, however, will be run by document
type. (Eliminating Filter type from possible doc types)
"""
from lxml import etree
import cdr
import cdrcgi
from cdrapi import db as cdrdb


class Control(cdrcgi.Control):
    """
       Collect and verify the user options for the report
    """

    TITLE = "URL List Report"

    def __init__(self):
        "Make sure the values make sense and haven't been hacked"

        cdrcgi.Control.__init__(self, self.TITLE)
        self.doctypes = cdr.getDoctypes(self.session)
        self.doctype = self.fields.getvalue("doctype")
        if self.doctype and self.doctype not in self.doctypes:
            cdrcgi.bail(cdrcgi.TAMPERING)

        query = cdrdb.Query("query_term q", "DISTINCT t.name", "d.doc_type")
        query.join("document d", "d.id = q.doc_id")
        query.join("doc_type t", "d.doc_type = t.id")
        query.where(query.Or("path LIKE '%ExternalRef%'",
                             "path LIKE '%DrugReferenceLink%'"))
        query.order("t.name")
        self.logger.info("Doc Type query\n{}".format(query))

        rows = query.execute(self.cursor).fetchall()
        self.usedDoctypes = [docType for docType, count in rows
                                     if docType != 'Filter']
        

    def populate_form(self, form):
        """
           Show form with doctypes containing links as selection picklist
        """
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Select Document Type For Report"))
        form.add_select("doctype", "Doc Type", self.usedDoctypes)
        form.add("</fieldset>")
        form.add_output_options('html')


    def build_tables(self):
        """
           Show the report's only table

           We're using separate SQL queries depending on the doc-type.
           This used to be a single query connected using a UNION 
           statement but CIAT decided they only need the report by 
           individual doc-type, so I'm splitting it but keeping the
           same columns for all three types.
        """

        # CIS query
        # ---------
        if self.doctype == 'Summary':
            query = cdrdb.Query("query_term i", # "dt.name AS 'name'",
                                                "i.doc_id AS 'CDR-ID'",
                                                "t.value AS value1",
                                                "i.value AS value2",
                                                "d.value AS value3",
                                                "s.value AS value4")
            query.join("query_term t", "i.doc_id = t.doc_id",
                       "t.path = '/Summary/SummaryTitle'")
            query.join("document x", "x.id = i.doc_id")
            query.join("doc_type dt", "dt.id = x.doc_type")
            query.outer("query_term s", "s.doc_id = i.doc_id",
                        "s.path like '%/ExternalRef/@SourceTitle'",
                        "s.node_loc = i.node_loc")
            query.join("query_term d", "d.doc_id = i.doc_id",
                       "d.path like '%/ExternalRef'",
                       "d.node_loc = i.node_loc")
            query.where("i.path like '%/ExternalRef/@cdr:xref'")

        # DIS query    
        # ---------
        elif self.doctype == 'DrugInformationSummary':
            query = cdrdb.Query("query_term a", # "'DrugInformationSummary'",
                                                "a.doc_id AS 'CDR-ID'",
                                                "b.value AS 'Title'",
                                                "a.value AS 'URL'",
                                                "NULL AS 'Display Text'",
                                                "NULL AS 'Source Title'")
            query.join("query_term b", "a.doc_id = b.doc_id")
            query.where("a.path LIKE '/DrugInformationSummary/DrugReference/DrugReferenceLink/@cdr:xref'")
            query.where("b.path LIKE '/DrugInformationSummary/Title'")
            query.where("a.value is NOT NULL")

        # Everything else query
        # ---------------------
        else:
            query = cdrdb.Query("query_term i", 
                                                "i.doc_id AS 'CDR-ID'",
                                                "t.title AS value1",
                                                "i.value AS value2",
                                                "d.value AS value3",
                                                "s.value AS value4")
            query.join("document t", "i.doc_id = t.id")
            query.join("doc_type dt", "dt.id = t.doc_type",
                       "dt.name NOT IN ('Summary')")
            query.outer("query_term s", 
                        "s.doc_id = i.doc_id",
                        "s.path like '%/ExternalRef/@SourceTitle'",
                        "s.node_loc = i.node_loc")
            query.join("query_term d", "d.doc_id = i.doc_id",
                       "d.node_loc = i.node_loc",
                       "d.path like '%/ExternalRef'")
            query.where("i.path like '%/ExternalRef/@cdr:xref'")
            query.where("dt.name = '{}'".format(self.doctype))
        query.order(1)

        # Log the query we're going to run
        # --------------------------------
        self.logger.info("Doc Type: {}".format(self.doctype))
        self.logger.info("Doc Type query\n{}".format(query))

        # Run query and get data
        # ----------------------
        rows = query.execute(self.cursor).fetchall()
            
        # Setting up report columns
        # -------------------------
        columns = (
            cdrcgi.Report.Column("Doc ID"),
            cdrcgi.Report.Column("Doc Title"),
            cdrcgi.Report.Column("URL"),
            cdrcgi.Report.Column("Display Text"),
            cdrcgi.Report.Column("Source Title")
        )
        
        # Set table caption and print report
        # ----------------------------------
        caption = "Document Type: {}".format(self.doctype)
        return [cdrcgi.Report.Table(columns, rows, caption=caption)]

if __name__ == "__main__":
    try:
        Control().run()
    except Exception as e:
        cdrcgi.bail(str(e))
