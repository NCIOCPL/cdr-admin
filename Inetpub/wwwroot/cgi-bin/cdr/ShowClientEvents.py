#!/usr/bin/env python

"""Report on the logged events on the client.

Tools used for tracking down what really happened when a user
reports anomalies in stored versions of CDR documents.
"""

import datetime
from cdrcgi import Controller


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

    def build_tables(self):
        """Create the only table this report uses."""

        opts = dict(columns=self.COLUMNS, caption=self.caption)
        return self.Reporter.Table(self.rows, **opts)

    @property
    def caption(self):
        """The string describing the report's range."""
        return f"{len(self.rows)} Events From {self.start} To {self.end}"

    @property
    def end(self):
        """End of the report's date range."""

        if not hasattr(self, "_end"):
            self._end = self.fields.getvalue("end") or str(self.TODAY)
        return self._end

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

    @property
    def start(self):
        """Start of the report's date range."""

        if not hasattr(self, "_start"):
            default = self.TODAY - datetime.timedelta(7)
            self._start = self.fields.getvalue("start") or str(default)
        return self._start

    @property
    def user(self):
        """Optional user for the report."""
        return self.fields.getvalue("user")


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
