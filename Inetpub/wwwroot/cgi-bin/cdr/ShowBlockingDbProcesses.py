#!/usr/bin/env python

"""Show blocking database requests.
"""

from cdrcgi import Controller


class Control(Controller):
    """Access to the database and report-building tools."""

    SUBTITLE = "SQL Server Process Blocks"
    COLUMNS = (
        ("p.spid", "SPID"),
        ("p.blocked", "Blocked By"),
        ("p.waittime", "Wait Time"),
        ("p.lastwaittype", "Last Wait Type"),
        ("p.waitresource", "Wait Resource"),
        ("p.cpu", "CPU Usage"),
        ("p.physical_io", "Physical I/O"),
        ("p.memusage", "Memory Usage"),
        ("d.name", "Database"),
        ("p.uid", "User ID"),
        ("p.loginame", "Login Name"),
        ("p.nt_username", "NT User Name"),
        ("p.nt_domain", "NT Domain"),
        ("p.hostname", "Host Name"),
        ("p.program_name", "Program Name"),
        ("p.hostprocess", "Host Process"),
        ("p.cmd", "Current Command"),
        ("p.net_address", "Net Address"),
        ("p.net_library", "Net Library"),
        ("p.login_time", "Login Time"),
        ("p.last_batch", "Last Request"),
        ("p.ecid", "ECID"),
        ("p.open_tran", "Open Transaction Count"),
        ("p.status", "Status"),
    )
    FIELDS = [column[0] for column in COLUMNS]
    COLUMNS = [column[1] for column in COLUMNS]

    def show_form(self):
        """Bypass the form, go straight to the report."""
        self.show_report()

    def build_tables(self):
        """Assemble the table for this report."""
        return self.Reporter.Table(self.rows, columns=self.COLUMNS)

    @property
    def rows(self):
        """Values for the report table."""

        query = self.Query("master..sysprocesses", "blocked")
        spid_in_blocked = query.Condition("p.spid", query, "IN")
        query = self.Query("master..sysprocesses p", *self.FIELDS)
        query.join("master..sysdatabases d", "d.dbid = p.dbid")
        query.where(query.Or("blocked <> 0", spid_in_blocked))
        return [tuple(row) for row in query.execute(self.cursor).fetchall()]


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
