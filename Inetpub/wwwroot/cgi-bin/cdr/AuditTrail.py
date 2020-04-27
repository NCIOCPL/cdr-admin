#!/usr/bin/env python

"""Audit Trail report requested by Lakshmi.
"""

from cdrapi import db
from cdrapi.docs import Doc
from cdrapi.users import Session
from cdrcgi import Controller, Reporter

class Control(Controller):

    SUBTITLE = "Audit Trail"

    def run(self):
        """Bypass the wait for the Submit button if doc id is present."""
        if self.doc:
            self.show_report()
        Controller.run(self)

    @property
    def doc(self):
        """The subject of the report."""
        if not hasattr(self, "_doc"):
            doc_id = self.fields.getvalue("id")
            if doc_id:
                self._doc = Doc(Session("guest"), id=doc_id)
            else:
                self._doc = None
        return self._doc

    @property
    def limit(self):
        """How many rows should be included in the report."""
        if not hasattr(self, "_limit"):
            self._limit = int(self.fields.getvalue("rows", "150"))
        return self._limit

    def build_tables(self):
        """Get the most recent activity for this document."""

        # Create a temporary working table.
        self.cursor.execute("""\
            CREATE TABLE #audit
                     (dt DATETIME,
                     usr VARCHAR(80),
                  action VARCHAR(255))""")

        # Populate it with rows from the audit_trail table.
        self.cursor.execute("""\
            INSERT INTO #audit
                 SELECT audit_trail.dt, usr.fullname, action.name
                   FROM audit_trail
                   JOIN usr
                     ON usr.id = audit_trail.usr
                   JOIN action
                     ON action.id = audit_trail.action
                  WHERE audit_trail.document = ?""", self.doc.id)

        # Add rows for locking the document.
        self.cursor.execute("""\
            INSERT INTO #audit
                 SELECT c.dt_out, u.fullname, 'LOCK'
                   FROM checkout c
                   JOIN usr u
                     ON u.id = c.usr
                  WHERE c.id = ?""", self.doc.id)

        # Pull the rows we need for the report.
        query = db.Query("#audit", "dt", "usr", "action").order("dt DESC")
        query.limit(self.limit)
        rows = []
        for row in query.execute(self.cursor).fetchall():
            rows.append([str(row.dt)[:19], row.usr, row.action])
        caption = self.doc.cdr_id, self.doc.title
        columns = "DATE TIME", "USER NAME", "ACTION"
        return Reporter.Table(rows, columns=columns, caption=caption)

    def populate_form(self, page):
        """Ask for a document ID if we didn't get one already."""

        fieldset = page.fieldset("Report Options")
        fieldset.append(page.text_field("id"))
        fieldset.append(page.text_field("rows", value=150))
        page.form.append(fieldset)

if __name__ == "__main__":
    Control().run()
