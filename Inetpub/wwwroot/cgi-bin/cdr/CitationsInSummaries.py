#!/usr/bin/env python

""" Report all citations linked by a summary document.
"""

from cdrcgi import Controller, Reporter, BASE
from cdrapi import db
from cdrapi.settings import Tier


class Control(Controller):
    SUBTITLE = "Citations In Summaries"
    COLS = (
        Reporter.Column("CDR-ID", width="60px"),
        Reporter.Column("Citation Title", width="1000px"),
    )
    HOST = Tier("PROD").hosts["APPC"]
    URL = f"https://{HOST}{BASE}/QcReport.py?Session=guest&DocId={{:d}}"
    URL += "&DocVersion=-1"
    INSTRUCTIONS = (
        "Press Submit to generate an Excel report listing all of the "
        "CDR Citation documents which are linked by at least one active "
        "CDR Summary document. Each Citation document is listed no more "
        "than once, regardless of how many links to it are found. The "
        "report table contains two columns, the first of which shows the "
        "CDR ID for the Citation document (linked to its QC report on "
        "the production server), and the second of which shows the CDR "
        "title for the document."
    )

    def populate_form(self, page):
        """Explain how the report works.

        Required positional argument:
          page - HTMLPage instance
        """

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)

    def build_tables(self):
        query = db.Query("active_doc d", "d.id", "d.title").order("d.id DESC")
        query.join("query_term q", "q.int_val = d.id")
        query.join("active_doc s", "s.id = q.doc_id")
        query.where("q.path LIKE '/Summary/%CitationLink/@cdr:ref'")
        rows = []
        for doc_id, title in query.unique().execute():
            url = self.URL.format(doc_id)
            row = Reporter.Cell(doc_id, center=True, href=url), title.strip()
            rows.append(row)
        opts = dict(
            columns=self.COLS,
            caption=self.SUBTITLE,
            sheet_name=self.SUBTITLE,
        )
        return Reporter.Table(rows, **opts)

    @property
    def format(self):
        return "excel"


Control().run()
