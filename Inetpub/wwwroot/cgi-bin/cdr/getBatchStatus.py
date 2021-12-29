#!/usr/bin/env python

"""Display status of batch jobs.

Administrator may use this to see past or current batch job
status information.

Program may be invoked with posted variables to display status
to a user.  If no variables are posted, the program displays
a form to get user parameters for the status request, then
processes them.

May post:
  jobId     = ID of job in batch_jobs table.
  jobName   = Name of job.
  jobAge    = Number of days to look backwards for jobs.
  jobStatus = One of the status strings in cdrbatch.py.

As with many other CDR CGI programs, the same program functions
both to display a form and to read its contents.
"""

from cdrbatch import getJobStatus, STATUSES
from cdrcgi import Controller, navigateTo
from lxml import html


class Control(Controller):
    """Access to form/report generation tools."""

    SUBTITLE = "Batch Job Status"
    REFRESH = "Refresh"
    BACK = "New Request"
    COLS = "ID", "Job Name", "Started", "Status", "Last Info", "Last Message"

    def populate_form(self, page):
        """Draw the fields on the form.

        Pass:
            page - HTMLPage object where the fields go
        """

        fieldset = page.fieldset("Report Options")
        fieldset.append(page.text_field("jobId", label="Job ID"))
        fieldset.append(page.text_field("jobName", label="Job Name"))
        opts = dict(label="Job Age", tooltip="Number of days to look back")
        fieldset.append(page.text_field("jobAge", **opts))
        fieldset.append(page.select("jobStatus", options=[""]+STATUSES))
        page.form.append(fieldset)

    def run(self):
        """Add some custom routing."""

        if not self.request:
            if self.id or self.name or self.age or self.status:
                self.request = self.SUBMIT
        elif self.request == self.BACK:
            return navigateTo(self.script, self.session.name)
        elif self.request == self.REFRESH:
            self.request = self.SUBMIT
        Controller.run(self)

    def show_report(self):
        """Override to add hidden fields and a couple of extra buttons."""

        page = self.report.page
        buttons = page.form.find("header/h1/span")
        buttons.insert(0, page.button(self.BACK))
        buttons.insert(0, page.button(self.REFRESH))
        page.form.append(page.hidden_field("jobId", self.id))
        page.form.append(page.hidden_field("jobName", self.name))
        page.form.append(page.hidden_field("jobAge", self.age))
        page.form.append(page.hidden_field("jobStatus", self.status))
        self.report.send()

    def build_tables(self):
        """Assemble the report table."""

        opts = dict(columns=self.COLS, caption="Batch Jobs")
        return self.Reporter.Table(self.rows, **opts)

    @property
    def rows(self):
        """Values for the report table.

        The batch job software violates the principle of applying
        markup to information as far downstream as possible. As a
        result we have to jump through some hoops to extract what
        we need for the Last Message column.
        """

        jobs = getJobStatus(self.id, self.name, self.age, self.status)
        rows = []
        Cell = self.Reporter.Cell
        B = self.HTMLPage.B
        for job in jobs:
            row = list(job)
            row[0] = Cell(row[0], classes="center")
            if row[2]:
                row[2] = Cell(str(row[2])[:19], classes="nowrap")
            if row[4]:
                row[4] = Cell(str(row[4])[:19], classes="nowrap")
            if row[-1]:
                try:
                    node = html.fromstring(row[-1])
                    if node.tag == "errors":
                        errors = [child.text for child in node.findall("err")]
                        errors = "; ".join(errors)
                        row[-1] = Cell(errors, classes="error")
                    else:
                        row[-1] = Cell(node)
                except Exception:
                    row[-1] = Cell(B.SPAN(*html.fragments_fromstring(row[-1])))
            rows.append(row)
        return rows

    @property
    def age(self):

        """Number of days to look back."""
        return self.fields.getvalue("jobAge")

    @property
    def id(self):
        """Job ID on which to report."""
        return self.fields.getvalue("jobId")

    @property
    def name(self):
        """Name of job on which to report."""
        return self.fields.getvalue("jobName")

    @property
    def status(self):
        return self.fields.getvalue("jobStatus")


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
