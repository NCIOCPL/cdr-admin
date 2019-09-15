#!/usr/bin/env python

"""Report on current sessions.
"""

from cdrcgi import Controller, Reporter
from cdrapi import db

class Control(Controller):

    SUBTITLE = "Current Sessions"
    FIELDS = (
        "CONVERT(VARCHAR, s.initiated, 120) AS started",
        'u.fullname AS "user"',
        "u.name",
        "u.office",
        "u.email",
        "u.phone",
        "CONVERT(VARCHAR, s.last_act, 120) AS last_activity"
    )

    def show_form(self):
        """Bypass the form."""
        self.show_report()

    def build_tables(self):
        """Serve up the table."""
        query = db.Query("session s", *self.FIELDS).order("s.last_act")
        query.join("usr u", "u.id = s.usr")
        query.where("s.ended IS NULL")
        rows = query.execute(self.cursor).fetchall()
        desc = self.cursor.description
        cols = [Reporter.Column(d[0].replace("_", " ").title()) for d in desc]
        return Reporter.Table(cols, rows)

Control().run()
