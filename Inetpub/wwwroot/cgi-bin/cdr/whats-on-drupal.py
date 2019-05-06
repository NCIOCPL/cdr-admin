#!/usr/bin/env python

"""
Show which Summaries (DIS & CIS) are on the Drupal CMS
"""

from cdrapi.docs import Doc
from cdrapi.publishing import DrupalClient
from cdrapi.users import Session
from cdrcgi import Control, Report

class DrupalSummaries(Control):
    TITLE = "PDQ Summaries on Drupal"
    def __init__(self):
        Control.__init__(self, self.PAGE_TITLE, self.TITLE)
        session = Session(self.session)
        host = session.tier.hosts.get("DRUPAL")
        self.host = self.fields.getvalue("host") or host
        self.base = "https://{}".format(self.host)
        self.client = DrupalClient(session, base=self.base)
    def populate_form(self, form):
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Drupal Server"))
        form.add_text_field("host", "Server", value=self.host)
        form.add("</fieldset>")
        form.add_output_options("html", None)
    def build_tables(self):
        catalog = self.client.list()
        headers = "CDR ID", "Title", "Type", "Language" #, "Created", "Changed"
        cols = [Report.Column(header) for header in headers]
        rows = []
        for summary in catalog:
            summary_type = "DIS" if "drug" in summary.type else "CIS"
            title = self.lookup_title(summary.cdr_id)
            language = "English" if summary.langcode == "en" else "Spanish"
            row = (
                "CDR{:d}".format(summary.cdr_id),
                title,
                summary_type,
                language,
                #str(summary.created),
                #str(summary.changed),
            )
            rows.append(row)
        table = Report.Table(cols, rows)
        return [table]
    def lookup_title(self, cdr_id):
        doc = Doc(self.client.session, id=cdr_id)
        return doc.title.split(";")[0].strip()

DrupalSummaries().run()
