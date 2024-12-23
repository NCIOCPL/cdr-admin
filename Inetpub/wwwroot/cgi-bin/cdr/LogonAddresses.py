#!/usr/bin/env python

"""Report recent CDR logon sessions.

Utility used to track down events when users get confused about
what they've been doing in the CDR. The report tries to match up
entries in the log for client refresh requests with rows in the
session table, but it's not completely foolproof, as the two events
aren't simultaneous, so in edge cases a session might be matched
with the wrong entry from the client refresh log.
"""

from cdrcgi import Controller, BasicWebPage
import datetime
from functools import cached_property
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

        opts = dict(caption=self.CAPTION, columns=self.COLUMNS)
        table = self.Reporter.Table(self.rows, **opts)
        report = BasicWebPage()
        report.wrapper.append(report.B.H1(self.SUBTITLE))
        report.wrapper.append(table.node)
        report.wrapper.append(self.footer)
        report.send()

    @cached_property
    def end(self):
        """End of the date range for the report."""
        return self.parse_date(self.fields.getvalue("end"))

    @cached_property
    def rows(self):
        """Values for the report table."""

        query = self.Query("session s", *self.FIELDS).order("s.id")
        query.join("usr u", "u.id = s.usr")
        if self.start:
            query.where(query.Condition("s.initiated", self.start, ">="))
        if self.end:
            end = f"{self.end} 23:59:59"
            query.where(query.Condition("s.initiated", self.end, "<="))
        five_seconds = datetime.timedelta(seconds=5)
        thirty_seconds = datetime.timedelta(seconds=30)
        rows = []
        i = 0
        for session in query.execute(self.cursor).fetchall():
            values = list(session)
            close_enough = session.initiated - five_seconds
            too_late_to_match = session.initiated + five_seconds
            too_late_to_log = session.initiated + thirty_seconds
            while i < len(self.requests):
                request = self.requests[i]
                if request.time >= close_enough:
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
            rows.append(values)
        end = self.end or "now"
        self.logger.info("Date range: %s to %s", self.start, end)
        self.logger.info("Found %d logon requests", len(rows))
        self.logger.info("Found %d ticket requests", len(self.requests))
        return rows

    @cached_property
    def requests(self):
        """Ticket requests from the client refresh log."""

        path = f"{self.session.tier.basedir}/Log/ClientRefresh.log"
        lines = []
        with open(path) as fp:
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
        return [Request(*pair) for pair in pairs]

    @cached_property
    def start(self):
        """Beginning of the date range for the report."""

        start = self.fields.getvalue("start")
        if start:
            return self.parse_date(start)
        today = datetime.date.today()
        return today - datetime.timedelta(7)


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
