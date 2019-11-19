#!/usr/bin/env python

""" Report all citations linked by a summary document.
"""

from cdrcgi import Controller, Reporter, BASE
from cdrapi import db
from cdrapi.settings import Tier

class Control(Controller):
    TITLE = "Citations In Summaries"
    COLS = (
        Reporter.Column("CDR-ID", width="60px"),
        Reporter.Column("Citation Title", width="1000px"),
    )
    HOST = Tier("PROD").hosts["APPC"]
    URL = f"https://{HOST}{BASE}/QcReport.py?Session=guest&DocId={{:d}}"
    URL += "&DocVersion=-1"
    def run(self):
        self.show_report()
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
            caption=self.TITLE,
            sheet_name=self.TITLE,
        )
        return Reporter.Table(rows, **opts)

    @property
    def format(self):
        return "excel"

Control().run()
