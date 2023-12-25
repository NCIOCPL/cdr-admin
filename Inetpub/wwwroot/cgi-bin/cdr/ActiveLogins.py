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

    def populate_form(self, page):
        """Bypass the form.

        Required positional argument:
          page - cdrcgi.HTMLPage instance
        """

        if not self.fields.getvalue("prompt"):
            return self.show_report()
        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(
            "Click Submit to generate an HTML table report showing "
            "the sessions which are still active for this tier. "
            "The table includes columns for:"
            ))
        fieldset.append(
            page.B.UL(
                page.B.LI("The date/time the session was initiated"),
                page.B.LI("The full name of the session's user account"),
                page.B.LI("The machine name for that account"),
                page.B.LI("The user's office (if available)"),
                page.B.LI("The user's email address (if available)"),
                page.B.LI("The user's phone number (if available)"),
                page.B.LI("The date/time of the session's last activity"),
            )
        )
        fieldset.append(page.B.P(
            "The table is ordered by the date/time of the session's "
            "last activity, with the most recently active sessions "
            "at the top of the report."
        ))
        page.form.append(fieldset)

    def build_tables(self):
        """Serve up the table."""
        query = db.Query("session s", *self.FIELDS).order("s.last_act")
        query.join("usr u", "u.id = s.usr")
        query.where("s.ended IS NULL")
        rows = query.execute(self.cursor).fetchall()
        desc = self.cursor.description
        cols = [d[0].replace("_", " ").title() for d in desc]
        return Reporter.Table(rows, columns=cols)


Control().run()
