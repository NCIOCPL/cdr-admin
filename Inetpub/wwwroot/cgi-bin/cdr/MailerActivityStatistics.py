#!/usr/bin/env python

"""Report on mailer counts for a specified date range.
"""

from cdrcgi import Controller
import datetime


class Control(Controller):
    """Report logic."""

    SUBTITLE = "Mailer Activity Statistics"

    def populate_form(self, page):
        """Add date range fields to form.

        Pass:
            page - HTMLPage object on which to place the fields
        """

        fieldset = page.fieldset("Specify Date Range")
        today = datetime.date.today()
        last_week = today - datetime.timedelta(7)
        fieldset.append(page.date_field("start", value=last_week))
        fieldset.append(page.date_field("end", value=today))
        page.form.append(fieldset)

    def build_tables(self):
        """Create the mailer counts table."""

        query = self.Query("query_term t", "t.value", "COUNT(*) AS n")
        query.join("query_term s", "s.doc_id = t.doc_id")
        query.where("t.path = '/Mailer/Type'")
        query.where("s.path = '/Mailer/Sent'")
        query.group("t.value")
        if self.start:
            query.where(query.Condition("s.value", self.start, ">="))
        if self.end:
            end = f"{self.end} 23:59:59"
            query.where(query.Condition("s.value", end, "<="))
        rows = []
        for mailer_type, count in query.execute(self.cursor).fetchall():
            rows.append((mailer_type, self.Reporter.Cell(count, right=True)))
        if not rows:
            return []
        columns = (
            self.Reporter.Column("Type", width="300px"),
            self.Reporter.Column("Count", width="75px"),
        )
        caption = "Mailers Sent"
        if self.start:
            if self.end:
                caption += f" from {self.start} to {self.end}"
            else:
                caption += f" since {self.start}"
        elif self.end:
            caption += f" through {self.end}"
        else:
            caption = "Mailer Counts"
        return self.Reporter.Table(rows, cols=columns, caption=caption)

    @property
    def start(self):
        """String from the form for the start of the date range."""
        return self.fields.getvalue("start")

    @property
    def end(self):
        """String from the form for the end of the date range."""
        return self.fields.getvalue("end")

    @property
    def no_results(self):
        """What to display if there are no mailers to report."""
        return "No mailers were sent during this time period."


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
