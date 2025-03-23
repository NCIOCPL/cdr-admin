#!/usr/bin/env python

"""Show the CDR XMetaL client logs."""

from datetime import date, timedelta
from functools import cached_property
from io import BytesIO
from sys import stdout
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
from cdrcgi import Controller, BasicWebPage


class Control(Controller):

    MAX_LOGS = 10, 25, 50, 100
    SUBTITLE = "Client Log Viewer"
    LOGNAME = "ClientLogViewer"
    OLDEST_FIRST = "Oldest first"
    LATEST_FIRST = "Most recent first"
    DIR = "cdr-client-logs"
    CSS = """\
.log-block { margin: 2rem 0 3rem; }
th, td { border: none; }
th { text-align: right; color: maroon; padding-left: 1rem; }
th::after { content: ":"; }
td { padding-right: 1rem; }
"""

    def download(self):
        """Hidden option to download the logs as a ZIP file."""

        buf = BytesIO()
        with ZipFile(buf, "w", ZIP_DEFLATED) as zf:
            for log in self.logs:
                stamp = log.log_saved.strftime("%Y%m%d%H%M%S")
                session = log.session_id
                path = f"{self.DIR}/{log.cdr_user}-{stamp}-{session}.log"
                info = ZipInfo(path, log.log_saved.timetuple()[:6])
                info.compress_type = ZIP_DEFLATED
                zf.writestr(info, log.log_data)
        zip_bytes = buf.getvalue()
        stamp = self.started.strftime("%Y%m%d%H%M%S")
        filename = f"{self.DIR}-{stamp}.zip"
        stdout.buffer.write(f"""\
Content-Type: application/zip
Content-Disposition: attachment; filename={filename}
Content-Length: {len(zip_bytes)}
X-Content-Type-Options: nosniff

""".encode("utf-8"))
        stdout.buffer.write(zip_bytes)
        exit()

    def populate_form(self, page):
        """Find out which logs the user wants to see.

        Pass:
            page - HTMLPage object where we communicate with the user.
        """

        fieldset = page.fieldset("Filter Options")
        opts = dict(options=self.users, default="Any")
        fieldset.append(page.select("user", **opts))
        today = date.today()
        yesterday = today - timedelta(1)
        opts = dict(start_date=yesterday, end_date=today)
        fieldset.append(page.date_range("date_range", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Maximum Number Of Logs")
        checked = True
        for value in self.MAX_LOGS:
            opts = dict(value=value, checked=checked)
            checked = False
            fieldset.append(page.radio_button("max-logs", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Sort Order")
        opts = dict(value=self.LATEST_FIRST, checked=True)
        fieldset.append(page.radio_button("sort-order", **opts))
        opts = dict(value=self.OLDEST_FIRST, checked=False)
        fieldset.append(page.radio_button("sort-order", **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Override the default implementation so we can add some CSS."""

        if self.fields.getvalue("download"):
            self.download()
        report = BasicWebPage()
        report.wrapper.append(report.B.H1(self.SUBTITLE))
        for table in self.tables:
            report.wrapper.append(table.node)
            report.wrapper.append(report.B.HR())
        report.wrapper.append(self.footer)
        report.head.append(report.B.STYLE(self.CSS))
        report.send()

    @cached_property
    def end(self):
        """End of date range used to filter the logs."""
        return self.fields.getvalue("date_range-end")

    @cached_property
    def logs(self):
        """Logs to be displayed."""

        query = self.Query("client_trace_log", "*")
        if self.max_logs:
            query.limit(self.max_logs)
        direction = "ASC" if self.sort_order == self.OLDEST_FIRST else "DESC"
        query.order(f"log_saved {direction}")
        if self.user and self.user != "Any":
            query.where(query.Condition("cdr_user", self.user))
        if self.start:
            query.where(query.Condition("log_saved", self.start, ">="))
        if self.end:
            end = self.end
            if len(end) == 10:
                end = f"{end} 23:59:59"
            query.where(query.Condition("log_saved", end, "<="))
        return query.execute(self.cursor).fetchall()

    @cached_property
    def max_logs(self):
        """Cap on the number of logs we display."""
        return int(self.fields.getvalue("max-logs") or 10)

    @cached_property
    def sort_order(self):
        """Does the user want the oldest or the newest logs at the top?"""
        return self.fields.getvalue("sort-order") or self.OLDEST_FIRST

    @cached_property
    def start(self):
        """Start of date range used to filter the logs."""
        return self.fields.getvalue("date_range-start")

    @cached_property
    def tables(self):
        """Create table-like objects with the log data."""

        class TablePlus:
            def __init__(self, div):
                self.node = div
        tables = []
        B = BasicWebPage.B
        for log in self.logs:
            saved = str(log.log_saved)
            if "." in saved and saved.endswith("000"):
                saved = saved[:-3]
            div = B.DIV(
                B.TABLE(
                    B.TR(
                        B.TH("Session"),
                        B.TD(log.session_id),
                    ),
                    B.TR(
                        B.TH("Saved"),
                        B.TD(saved),
                    ),
                    B.TR(
                        B.TH("User"),
                        B.TD(log.cdr_user),
                    ),
                ),
                B.PRE(log.log_data),
                B.CLASS("log-block")
            )
            tables.append(TablePlus(div))
        return tables

    @cached_property
    def user(self):
        """Which user's logs should we show?"""
        return self.fields.getvalue("user") or "Any"

    @cached_property
    def users(self):
        """Values for the picklist on the form."""

        query = self.Query("client_trace_log", "cdr_user").order(1).unique()
        users = [row.cdr_user for row in query.execute(self.cursor)]
        return ["Any"] + users


if __name__ == "__main__":
    """Allow loading without execution."""
    Control().run()
