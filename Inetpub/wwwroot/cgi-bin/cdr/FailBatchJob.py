#!/usr/bin/env python

"""Change the status of a batch or publishing job to a failed state.
"""

from functools import cached_property
from cdrcgi import Controller


class Control(Controller):
    "Logic for the script."

    LOGNAME = "FailBatchJob"
    SUBTITLE = "Mark Stuck Job(s) as Failed"
    INSTRUCTIONS = (
        "This tool marks stalled publishing and batch jobs (usually "
        "caused by a server crash) as failed so that attempts to create "
        "new jobs are not blocked. Check the job(s) which need to "
        "be resolved and press the Submit button."
    )

    def populate_form(self, page):
        """Provide instructions and form fields.

        Pass:
            page - HTMLPage object to be populated
        """

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)
        if self.jobs:
            count = len(self.sorted_jobs)
            s = "" if count == 1 else "s"
            legend = f"{len(self.sorted_jobs)} Stalled or Active Job{s}"
            fieldset = page.fieldset(legend)
            rows = [job.row for job in self.sorted_jobs]
            table = page.B.TABLE(self.headers, *rows)
            table.set("class", "usa-table usa-table--borderless")
            fieldset.append(table)
        else:
            fieldset = page.fieldset("Stalled Jobs")
            para = page.B.P("There are currently no stalled jobs.")
            para.set("class", "center info")
            fieldset.append(para)
        page.form.append(fieldset)
        page.add_css("""\
table.usa-table th { font-weight: bold; }
table.usa-table th:first-child { text-align: center; }
.clickable.usa-checkbox__label { margin-top: -.25rem; margin-left: .75rem; }
""")

    def build_tables(self):
        """Resolve jobs as requested and re-display form."""

        if not self.session.can_do("SET_SYS_VALUE"):
            self.bail("Operation not authorized")
        if self.publishing_jobs:
            placeholders = ",".join(["?"] * len(self.publishing_jobs))
            where = f"WHERE id IN ({placeholders})"
            update = f"UPDATE pub_proc SET status = 'Failure' {where}"
            self.cursor.execute(update, tuple(self.publishing_jobs))
            log_message = "%s marked publishing job %s as 'Failure'"
            for job_id in sorted(self.publishing_jobs):
                args = self.session.user_name, job_id
                self.logger.info(log_message, *args)
                alert = f"Marked publishing job {job_id} as failed."
                self.alerts.append(dict(message=alert, type="success"))
        if self.batch_jobs:
            placeholders = ",".join(["?"] * len(self.batch_jobs))
            where = f"WHERE id IN ({placeholders})"
            update = (
                "UPDATE batch_job"
                "   SET status = 'Aborted',"
                "       status_dt = GETDATE()"
                f" WHERE id IN ({placeholders})"
            )
            self.cursor.execute(update, tuple(self.batch_jobs))
            for job_id in sorted(self.batch_jobs):
                args = self.session.user_name, job_id
                self.logger.info("%s marked batch job %s as 'Aborted'", *args)
                alert = f"Marked batch job {job_id} as aborted."
                self.alerts.append(dict(message=alert, type="success"))
        if self.publishing_jobs or self.batch_jobs:
            self.conn.commit()
        else:
            alert = "No jobs were selected for resolution."
            self.alerts.append(dict(message=alert, type="warning"))
        self.show_form()

    @cached_property
    def batch_jobs(self):
        """Batch jobs marked for resolution by the user."""

        batch_jobs = set()
        for key in self.checked_jobs:
            if key[0] == "B":
                batch_jobs.add(int(key[1:]))
        return batch_jobs

    @cached_property
    def checked_jobs(self):
        """Jobs marked for resolution by the user."""
        return self.fields.getlist("job")

    @cached_property
    def headers(self):
        """Column headers for the form."""

        columns = "\u2713", "Job", "Type", "Started", "Status", "Name"
        headers = [self.HTMLPage.B.TH(column) for column in columns]
        return self.HTMLPage.B.THEAD(self.HTMLPage.B.TR(*headers))

    @cached_property
    def buttons(self):
        """Only show the submit button if there's something to submit."""
        return [self.SUBMIT] if self.jobs else []

    @cached_property
    def jobs(self):
        """Dictionary of stalled jobs (both publihsing and batch)."""

        jobs = {}
        fields = "id", "name", "started", "status"
        query = self.Query("batch_job", *fields)
        query.where("status NOT IN ('Completed', 'Aborted')")
        for row in query.execute(self.cursor).fetchall():
            job = Job(self, "batch", row)
            jobs[job.key] = job
        fields = "id", "pub_subset AS name", "started", "status"
        query = self.Query("pub_proc", *fields)
        query.where("status NOT IN ('Success', 'Failure')")
        for row in query.execute(self.cursor).fetchall():
            job = Job(self, "publishing", row)
            jobs[job.key] = job
        return jobs

    @cached_property
    def publishing_jobs(self):
        """Publishing jobs marked for resolution by the user."""

        publishing_jobs = set()
        for key in self.checked_jobs:
            if key[0] == "P":
                publishing_jobs.add(int(key[1:]))
        return publishing_jobs

    @cached_property
    def same_window(self):
        """Stay on the same browser tab."""
        return self.buttons

    @cached_property
    def sorted_jobs(self):
        """Sorted sequence of the `Job` object for display on the form."""
        return list(reversed(sorted(self.jobs.values())))


class Job:
    """Information about a stalled publishing or batch job."""

    def __init__(self, control, job_type, row):
        """Capture the caller's information."""

        self.__control = control
        self.__type = job_type
        self.__row = row

    def __lt__(self, other):
        """Make the `Job` objects sortable by date."""
        return self.started < other.started

    @property
    def id(self):
        """Integer ID for the job."""
        return self.__row.id

    @cached_property
    def key(self):
        """Combination of "P" or "B" and the job ID."""
        return f"{self.type[0].upper()}{self.id}"

    @property
    def name(self):
        """String for the particular type of job (e.g. 'Export')."""
        return self.__row.name

    @cached_property
    def row(self):
        """HTML table row for display on the form."""

        Page = self.__control.HTMLPage
        checkbox = Page.checkbox("job", value=self.key, label="\u2009")
        self._row = Page.B.TR(
            Page.B.TD(checkbox),
            Page.B.TD(str(self.id)),
            Page.B.TD(self.type),
            Page.B.TD(str(self.started)[:10]),
            Page.B.TD(self.status),
            Page.B.TD(self.name)
        )
        return self._row

    @property
    def started(self):
        """Date and time when the job was created."""
        return self.__row.started

    @property
    def status(self):
        """Current status for the job."""
        return self.__row.status

    @property
    def type(self):
        """String for the job type ('batch' or 'publishing')."""
        return self.__type


if __name__ == "__main__":
    """Don't execute script if loaded as module."""
    Control().run()
