#!/usr/bin/env python

"""Change the status of a batch or publishing job to a failed state.
"""

from cdrcgi import Controller


class Control(Controller):
    "Logic for the script."

    LOGNAME = "FailBatchJob"
    SUBTITLE = "Mark Stuck Publishing or Batch Job as Failed"
    INSTRUCTIONS = (
        "This tool marks stalled publishing and batch jobs (usually "
        "caused by a server crash) as failed so that attempt to create "
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
            legend = f"{len(self.sorted_jobs)} Stalled and Active Jobs"
            fieldset = page.fieldset(legend)
            rows = [job.row for job in self.sorted_jobs]
            fieldset.append(page.B.TABLE(self.headers, *rows))
        else:
            fieldset = page.fieldset("Stalled Jobs")
            para = page.B.P("There are currently no stalled jobs.")
            para.set("class", "center info")
            fieldset.append(para)
        page.form.append(fieldset)
        page.add_css("""\
fieldset { width: 1000px; }
table * { background: #e8e8e8; }
td, th { border-color: #ccc; }
table { width: 95%; }""")

    def build_tables(self):
        """Resolve jobs as requested and re-display form."""

        subtitle = ""
        if not self.session.can_do("SET_SYS_VALUE"):
            self.bail("Operation not authorized")
        if self.publishing_jobs:
            placeholders = ",".join(["?"] * len(self.publishing_jobs))
            where = f"WHERE id IN ({placeholders})"
            update = f"UPDATE pub_proc SET status = 'Failure' {where}"
            self.cursor.execute(update, tuple(self.publishing_jobs))
            subtitle = f"Resolved {len(self.publishing_jobs)} publishing jobs"
            message = "%s marked publishing job %s as 'Failure'"
            for job_id in sorted(self.publishing_jobs):
                args = self.session.user_name, job_id
                self.logger.info(message, *args)
        if self.batch_jobs:
            placeholders = ",".join(["?"] * len(self.batch_jobs))
            where = f"WHERE id IN ({placeholders})"
            update = f"UPDATE batch_job SET status = 'Aborted' {where}"
            self.cursor.execute(update, tuple(self.batch_jobs))
            if subtitle:
                subtitle += f" and {len(self.batch_jobs)} batch jobs"
            else:
                subtitle = f"Resolved {len(self.batch_jobs)} batch jobs"
            for job_id in sorted(self.batch_jobs):
                args = self.session.user_name, job_id
                self.logger.info("%s marked batch job %s as 'Aborted'", *args)
        if subtitle:
            self.conn.commit()
        else:
            subtitle = "No jobs were selected for resolution"
            self.logger.warning("Request submitted with no jobs")
        self.subtitle = subtitle
        self.show_form()

    @property
    def buttons(self):
        """Decide which buttons to display."""

        if self.jobs:
            return self.SUBMIT, self.DEVMENU, self.ADMINMENU, self.LOG_OUT
        return self.DEVMENU, self.ADMINMENU, self.LOG_OUT

    @property
    def headers(self):
        """Column headers for the form."""

        return self.HTMLPage.B.TR(
            self.HTMLPage.B.TH("\u2713"),
            self.HTMLPage.B.TH("Job", self.HTMLPage.B.STYLE("center")),
            self.HTMLPage.B.TH("Type", self.HTMLPage.B.STYLE("center")),
            self.HTMLPage.B.TH("Started", self.HTMLPage.B.STYLE("center")),
            self.HTMLPage.B.TH("Status", self.HTMLPage.B.STYLE("center")),
            self.HTMLPage.B.TH("Name", self.HTMLPage.B.STYLE("center"))
        )
    @property
    def jobs(self):
        """Dictionary of stalled jobs (both publihsing and batch)."""

        if not hasattr(self, "_jobs"):
            self._jobs = {}
            fields = "id", "name", "started", "status"
            query = self.Query("batch_job", *fields)
            query.where("status NOT IN ('Completed', 'Aborted')")
            for row in query.execute(self.cursor).fetchall():
                job = Job(self, "batch", row)
                self._jobs[job.key] = job
            fields = "id", "pub_subset AS name", "started", "status"
            query = self.Query("pub_proc", *fields)
            query.where("status NOT IN ('Success', 'Failure')")
            for row in query.execute(self.cursor).fetchall():
                job = Job(self, "publishing", row)
                self._jobs[job.key] = job
        return self._jobs

    @property
    def checked_jobs(self):
        """Jobs marked for resolution by the user."""

        if not hasattr(self, "_checked_jobs"):
            self._checked_jobs = self.fields.getlist("job")
        return self._checked_jobs

    @property
    def publishing_jobs(self):
        """Publishing jobs marked for resolution by the user."""

        if not hasattr(self, "_publishing_jobs"):
            self._publishing_jobs = set()
            for key in self.checked_jobs:
                if key[0] == "P":
                    self._publishing_jobs.add(int(key[1:]))
        return self._publishing_jobs

    @property
    def batch_jobs(self):
        """Batch jobs marked for resolution by the user."""

        if not hasattr(self, "_batch_jobs"):
            self._batch_jobs = set()
            for key in self.checked_jobs:
                if key[0] == "B":
                    self._batch_jobs.add(int(key[1:]))
        return self._batch_jobs

    @property
    def sorted_jobs(self):
        """Sorted sequence of the `Job` object for display on the form."""

        if not hasattr(self, "_sorted_jobs"):
            self._sorted_jobs = list(reversed(sorted(self.jobs.values())))
        return self._sorted_jobs

    @property
    def subtitle(self):
        """String to be displayed under the primary banner."""

        if not hasattr(self, "_subtitle"):
            self._subtitle = self.SUBTITLE
        return self._subtitle

    @subtitle.setter
    def subtitle(self, value):
        """Override as necessary."""
        self._subtitle = value


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

    @property
    def key(self):
        """Combination of "P" or "B" and the job ID."""
        return f"{self.type[0].upper()}{self.id}"

    @property
    def name(self):
        """String for the particular type of job (e.g. 'Export')."""
        return self.__row.name

    @property
    def row(self):
        """HTML table row for display on the form."""

        if not hasattr(self, "_row"):
            B = self.__control.HTMLPage.B
            opts = dict(name="job", value=f"{self.key}", type="checkbox")
            self._row = B.TR(
                B.TD(B.INPUT(**opts), B.CLASS("center")),
                B.TD(str(self.id), B.CLASS("center")),
                B.TD(self.type, B.CLASS("center")),
                B.TD(str(self.started)[:10], B.CLASS("center")),
                B.TD(self.status, B.CLASS("center")),
                B.TD(self.name)
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
