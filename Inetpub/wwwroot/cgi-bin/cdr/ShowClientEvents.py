#!/usr/bin/env python

"""Report on the logged events on the client.

Tools used for tracking down what really happened when a user
reports anomalies in stored versions of CDR documents.
"""

from functools import cached_property
import datetime
from cdrcgi import Controller, BasicWebPage


class Control(Controller):

    SUBTITLE = "Client Events"
    COLUMNS = (
        "User ID",
        "User Name",
        "Event Time",
        "Event Description",
        "Session ID",
        "Session Name",
    )
    FIELDS = (
        "u.name",
        "u.fullname",
        "c.event_time",
        "c.event_desc",
        "s.id",
        "s.name",
    )
    TODAY = datetime.date.today()

    def populate_form(self, page):
        """Bypass the from, which isn't used."""
        self.show_report()

    def show_report(self):
        """Override to accommodate the report's wide table."""

        report = BasicWebPage()
        report.wrapper.append(report.B.H1(self.SUBTITLE))
        report.wrapper.append(self.table.node)
        report.wrapper.append(self.footer)
        report.send()

    @property
    def caption(self):
        """The string describing the report's range."""
        return f"{len(self.rows)} Events From {self.start} To {self.end}"

    @cached_property
    def end(self):
        """End of the report's date range."""
        return str(self.parse_date(self.fields.getvalue("end")) or self.TODAY)

    @property
    def rows(self):
        """Table rows for the report."""

        if not hasattr(self, "_rows"):
            end = self.end
            if len(end) == 10:
                end = f"{end} 23:59:59"
            user = self.user
            query = self.Query("usr u", *self.FIELDS).order("c.event_id")
            query.join("session s", "s.usr = u.id")
            query.join("client_log c", "c.session = s.id")
            query.where(query.Condition("c.event_time", self.start, ">="))
            query.where(query.Condition("c.event_time", end, "<="))
            if user:
                query.where(query.Condition("u.name", user))
            self._rows = [tuple(row) for row in query.execute(self.cursor)]
        return self._rows

    @cached_property
    def start(self):
        """Start of the report's date range."""

        default = self.TODAY - datetime.timedelta(7)
        return str(self.parse_date(self.fields.getvalue("start")) or default)

    @cached_property
    def table(self):
        """Create the single table used for this report."""

        opts = dict(columns=self.COLUMNS, caption=self.caption)
        return self.Reporter.Table(self.rows, **opts)

    @property
    def user(self):
        """Optional user for the report."""
        return self.fields.getvalue("user")


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
