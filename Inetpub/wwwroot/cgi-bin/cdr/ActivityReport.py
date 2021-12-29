#!/usr/bin/env python

"""
Report on audit trail content.
BZIssue::1283 - add support for searching by user
"""

import datetime
import cdr
from cdrcgi import Controller
from cdrapi import db


class ActivityReport(Controller):

    SUBTITLE = "Document Activity Report"
    COLS = "Who", "When", "Action", "DocType", "DocID", "DocTitle", "Comment"
    TODAY = datetime.date.today()

    def populate_form(self, page):
        end_date = self.TODAY
        start_date = str(end_date - datetime.timedelta(6))
        fieldset = page.fieldset("Report Parameters")
        fieldset.append(page.text_field("user"))
        fieldset.append(page.select("doctype", options=[""]+self.doctypes))
        fieldset.append(page.date_field("start_date", value=start_date))
        fieldset.append(page.date_field("end_date", value=str(end_date)))
        page.form.append(fieldset)

    def build_tables(self):
        """Assemble the report's table."""

        # Force date value.
        start_date = str(self.start_date or cdr.URDATE)[:10]
        end_date = str(self.end_date or datetime.date.today())[:10]
        date_range = f"From {start_date} to {end_date}"

        # Build the report's query.
        query = db.Query("audit_trail a", "u.name", "u.fullname", "v.name",
                         "a.dt", "t.name", "d.id", "d.title", "a.comment")
        query.order("a.dt DESC")
        query.join("usr u", "u.id = a.usr")
        query.join("all_docs d", "d.id = a.document")
        query.join("doc_type t", "t.id = d.doc_type")
        query.join("action v", "v.id = a.action")
        if self.user:
            query.where(query.Condition("u.name", self.user))
        if self.doctype:
            query.where(query.Condition("t.name", self.doctype))
            caption = f"{self.doctype} Documents -- {self.TODAY}"
        else:
            caption = f"All Document Types -- {self.TODAY}"
        query.where(query.Condition("a.dt", start_date, ">="))
        query.where(query.Condition("a.dt", f"{end_date} 23:59:59", "<="))

        # Collect the report's values.
        cursor = self.cursor
        query.execute(cursor)
        rows = []
        for user, name, action, when, dt, id, title, cmt in cursor.fetchall():
            who = f"{name} ({user})"
            when = str(when)[:19]
            cdrid = f"{id:010d}"
            url = f"QcReport.py?DocId={cdrid}&Session={self.session}"
            url += "&DocVersion=-1"
            link = self.Reporter.Cell(cdrid, href=url)
            title = f"{title[:20]} ..."
            row = who, when, action, dt, link, title, cmt
            rows.append(row)
        caption = [caption, date_range]
        return self.Reporter.Table(rows, caption=caption, columns=self.COLS)

    def show_report(self):
        """Override to provide a hook for some custom style rules."""
        self.report.page.body.set("id", "activity-report")
        self.report.send(self.format)

    @property
    def start_date(self):
        if not hasattr(self, "_start_date"):
            self._start_date = self.fields.getvalue("start_date")
            if self._start_date:
                if not cdr.strptime(self._start_date, "%Y-%m-%d"):
                    msg = "Start Date must be valid date in YYYY-MM-DD format"
                    self.bail(msg)
        return self._start_date

    @property
    def end_date(self):
        if not hasattr(self, "_end_date"):
            self._end_date = self.fields.getvalue("end_date")
            if self._end_date:
                if not cdr.strptime(self._end_date, "%Y-%m-%d"):
                    msg = "Start Date must be valid date in YYYY-MM-DD format"
                    self.bail(msg)
        return self._end_date

    @property
    def doctypes(self):
        if not hasattr(self, "_doctypes"):
            self._doctypes = cdr.getDoctypes(self.session)
        return self._doctypes

    @property
    def doctype(self):
        if not hasattr(self, "_doctype"):
            self._doctype = self.fields.getvalue("doctype")
            if self._doctype and self._doctype not in self.doctypes:
                self.bail()
        return self._doctype

    @property
    def user(self):
        return self.fields.getvalue("user")


if __name__ == "__main__":
    ActivityReport().run()
