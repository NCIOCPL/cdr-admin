#!/usr/bin/env python

"""Report recent CDR logon sessions.

Utility used to track down events when users get confused about
what they've been doing in the CDR.
"""

from cdrcgi import Controller
import datetime
from re import compile


class Control(Controller):

    SUBTITLE = "CDR Ticket Request IP Addresses"
    LOGNAME = "LogonAddresses"
    COLUMNS = (
        "User ID",
        "User Name",
        "Session ID",
        "Logged On",
        "Logged Off",
        "Ticket Request",
        "IP Address",
    )
    FIELDS = (
        "u.name AS account",
        'u.fullname AS "user"',
        "s.name",
        "s.initiated",
        "s.ended",
    )
    CAPTION = "CDR Logons and Ticket Requests"
    DATETIME = r"\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d.\d+"
    PATTERN = compile(fr"({DATETIME}) \[INFO\] Ticket request from (\S+)")

    def build_tables(self):
        """Assemble the table for this report."""

        opts = dict(caption=self.CAPTION, columns=self.COLUMNS)
        return self.Reporter.Table(self.rows, **opts)

    def show_form(self):
        """Skip the form, which isn't used for this report."""
        self.show_report()

    @property
    def end(self):
        """End of the date range for the report."""
        return self.fields.getvalue("end")

    @property
    def rows(self):
        """Values for the report table."""

        if not hasattr(self, "_rows"):
            query = self.Query("session s", *self.FIELDS).order("s.id")
            query.join("usr u", "u.id = s.usr")
            if self.start:
                query.where(query.Condition("s.initiated", self.start, ">="))
            if self.end:
                end = f"{self.end} 23:59:59"
                query.where(query.Condition("s.initiated", self.end, "<="))
            five_seconds = datetime.timedelta(seconds=5)
            thirty_seconds = datetime.timedelta(seconds=30)
            self._rows = []
            i = 0
            for session in query.execute(self.cursor).fetchall():
                values = list(session)
                too_late_to_match = session.initiated + five_seconds
                too_late_to_log = session.initiated + thirty_seconds
                while i < len(self.requests):
                    request = self.requests[i]
                    if request.time >= session.initiated:
                        if request.time < too_late_to_match:
                            values.append(request.time)
                            values.append(request.ip)
                            i += 1
                        elif request.time < too_late_to_log:
                            args = request.time, session.initiated
                            self.logger.warning("skipped %s for %s", *args)
                        break
                    else:
                        i += 1
                while len(values) < len(self.COLUMNS):
                    values.append("")
                self._rows.append(values)
            end = self.end or "now"
            self.logger.info("Date range: %s to %s", self.start, end)
            self.logger.info("Found %d logon requests", len(self._rows))
            self.logger.info("Found %d ticket requests", len(self.requests))
        return self._rows

    @property
    def requests(self):
        """Ticket requests from the client refresh log."""

        if not hasattr(self, "_requests"):
            self._requests = []
            path = f"{self.session.tier.basedir}/Log/ClientRefresh.log"
            with open(path) as fp:
                lines = []
                for line in fp:
                    if "Ticket request from" in line:
                        lines.append(line.strip())
                class Request:
                    strptime = datetime.datetime.strptime
                    PATTERN = "%Y-%m-%d %H:%M:%S.%f"
                    def __init__(self, time, ip):
                        self.time = self.strptime(time, self.PATTERN)
                        self.ip = ip
                pairs = self.PATTERN.findall("\n".join(lines))
                self._requests = [Request(*pair) for pair in pairs]
        return self._requests

    @property
    def start(self):
        """Beginning of the date range for the report."""

        if not hasattr(self, "_start"):
            self._start = self.fields.getvalue("start")
            if not self._start:
                today = datetime.date.today()
                self._start = today - datetime.timedelta(7)
        return self._start


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
