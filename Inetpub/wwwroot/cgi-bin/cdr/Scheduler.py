#!/usr/bin/env python

"""Manage scheduler jobs.

Replacement for the poorly maintained ndscheduler package.

Most of the rows in the scheduled_job table have cron-style
values specifying when the job is to be run by the scheduling
service. If a job's `enabled` flag is turned on, the scheduler
executes the job using the parameter options specified in the
job's table row.

A few jobs are registered without any scheduling information, and
will only be executed on demand. These are stored in the scheduled_job
table with the `enabled` flag turned off and the `schedule` column
set to NULL.

Any job can be launched immediately. When the "Run Job Now" button is
clicked a new row is added to the scheduled_job table, copying the
values from the form displayed for the currently selected job, with
the `enabled` flag turned on and `schedule` column set to NULL. When
the scheduling service performs the requested immediate execution the
temporary row just added to the table is deleted.

In summary, there are four basic types of rows in the scheduled_job table:

 1. Scheduled/enabled (the most common; executed according to schedule)
 2. Scheduled/disabled (scheduled execution suppressed)
 3. Unscheduled/disabled (stores job settings but not executed on a schedule)
 4. Unscheduled/enabled (temporary row for a job execution just requested)

Only jobs for the first three types are displayed in the list of jobs
on the landing page for this script.

"""

from importlib import import_module
from json import loads, dumps
from cdrcgi import Controller, navigateTo
from cdr import ordinal
from sys import path


class Control(Controller):
    """Top-level logic for the administrative interface."""

    LOGNAME = "new-schedule-manager"
    SUBTITLE = "Scheduled Jobs"
    CSS = (
        "fieldset { width: 1200px; }",
        "table { width: 100%; }",
        "th, td { background-color: #e8e8e8; border-color: #ccc; }",
    )
    UNITS = "hour", "minute", "day_of_week", "day"
    JOBS = "Jobs"
    ADD = "Add New Job"
    DELETE = "Delete Job"
    JSON = "JSON"
    RUN = "Run Job Now"
    SAVE = "Save"
    JS = "/js/Scheduler.js"
    JOB_CLASS_ERROR = "Class name must be in the form module.ClassName"
    INSERT = "\n".join([
        "SET NOCOUNT ON;",
        "DECLARE @NEWID TABLE(id UNIQUEIDENTIFIER);",
        "INSERT INTO scheduled_job (name, enabled, job_class, opts, schedule)",
        "OUTPUT INSERTED.id INTO @NEWID(id)",
        "VALUES (?, ?, ?, ?, ?)",
        "SELECT id FROM @NEWID",
    ])
    UPDATE = "\n".join([
        "UPDATE scheduled_job",
        "   SET name = ?,",
        "       enabled = ?,",
        "       job_class = ?,",
        "       opts = ?,",
        "       schedule = ?",
        " WHERE id = ?",
    ])

    def populate_form(self, page):
        """Show jobs or job form, depending on which was requested.

        Pass:
            page - HTMLPage object on which to draw the form
        """

        if self.job:
            fieldset = page.fieldset("Job Settings")
            page.form.append(page.hidden_field("id", self.job.id))
            fieldset.append(page.text_field("name", value=self.job.name))
            opts = dict(label="Job Class", value=self.job.job_class)
            fieldset.append(page.text_field("job_class", **opts))
            page.form.append(fieldset)
            fieldset = page.fieldset("Schedule")
            for unit in self.UNITS:
                value = self.job.schedule.get(unit)
                fieldset.append(page.text_field(unit, value=value))
            page.form.append(fieldset)
            counter = 1
            for name in sorted(self.job.opts):
                fieldset = page.fieldset("Named Job Option")
                fieldset.set("class", "opt-block")
                fieldset.set("id", f"opt-block-{counter}")
                opts = dict(label="Name", value=name, classes="opt-name")
                arg = f"opt-name-{counter}"
                fieldset.append(page.text_field(arg, **opts))
                value = self.job.opts[name]
                opts = dict(label="Value", value=value, classes="opt-value")
                arg = f"opt-value-{counter}"
                fieldset.append(page.text_field(arg, **opts))
                page.form.append(fieldset)
                counter += 1
            if not self.job.opts:
                page.form.append(page.hidden_field("num-opts", 1))
                fieldset = page.fieldset("Named Job Option")
                fieldset.set("class", "opt-block")
                fieldset.set("id", "opt-block-1")
                opts = dict(label="Name", classes="opt-name")
                fieldset.append(page.text_field("opt-name-1", **opts))
                opts = dict(label="Value", classes="opt-value")
                fieldset.append(page.text_field("opt-value-1", **opts))
                page.form.append(fieldset)
            else:
                num_opts = len(self.job.opts)
                page.form.append(page.hidden_field("num-opts", num_opts))
            fieldset = page.fieldset("General Options")
            opts = dict(label="Job enabled", value="enabled")
            if self.job.enabled:
                opts["checked"] = True
            fieldset.append(page.checkbox("opts", **opts))
            fieldset.set("id", "options-block")
            page.form.append(fieldset)
            page.head.append(page.B.SCRIPT(src=self.JS))
            page.add_css(".job-opt-button { padding-left: 10px; }")
        else:
            table = page.B.TABLE(
                page.B.TR(
                    page.B.TH("Name"),
                    page.B.TH("Implemented By"),
                    page.B.TH("Enabled?"),
                    page.B.TH("Schedule")
                )
            )
            for job in self.jobs:
                try:
                    formatted_schedule = job.formatted_schedule
                except Exception:
                    formatted_schedule = job.schedule
                url = self.make_url(self.script, id=job.id)
                row = page.B.TR(
                    page.B.TD(page.B.A(job.name, href=url)),
                    page.B.TD(job.job_class),
                    page.B.TD("Yes" if job.enabled else "No",
                              page.B.CLASS("center")),
                    page.B.TD(formatted_schedule)
                )
                table.append(row)
            fieldset = page.fieldset("Jobs")
            fieldset.append(table)
            page.form.append(fieldset)
            page.add_css("\n".join(self.CSS))

    def run(self):
        """Override the base class version as this is not a standard report."""

        try:
            if not self.session.can_do("MANAGE SCHEDULER"):
                self.bail("Account not allowed to manage the scheduler")
        except Exception as e:
            self.bail(e)
        try:
            if self.request == self.SAVE:
                self.save_job()
            elif self.request == self.DELETE:
                self.delete_job()
            elif self.request == self.RUN:
                self.run_job()
            elif self.request == self.JOBS:
                navigateTo(self.script, self.session.name)
            elif self.request == self.JSON:
                self.json()
            else:
                Controller.run(self)
        except Exception as e:
            self.bail(e)

    def save_job(self):
        """Save the currently edited job and redraw the form."""

        if not self.name:
            self.bail("Job name is required")
        if not self.job_class:
            self.bail("Class name for job is required")
        values = [
            self.name,
            self.enabled,
            self.job_class,
            self.opts,
            self.schedule or None,
        ]
        if self.id:
            values.append(self.id)
            self.cursor.execute(self.UPDATE, values)
        else:
            self.cursor.execute(self.INSERT, values)
            self.id = self.cursor.fetchone().id
        self.conn.commit()
        self.show_form()

    def run_job(self):
        """Queue up the current job to run immediately and redraw the form."""

        if not self.name:
            self.bail("Job name is required")
        if not self.job_class:
            self.bail("Class name for job is required")
        values = [
            self.name,
            True,
            self.job_class,
            self.opts,
        ]
        self.cursor.execute(
            "INSERT INTO scheduled_job (name, enabled, job_class, opts)"
            "     VALUES (?, ?, ?, ?)", values)
        self.conn.commit()
        self.show_form()

    def delete_job(self):
        """Remove the current job and return to the job list."""

        self.cursor.execute("DELETE FROM scheduled_job WHERE id = ?", self.id)
        self.conn.commit()
        navigateTo(self.script, self.session.name)

    def json(self):
        """Send the serialized jobs to the client."""

        rows = self.cursor.execute("SELECT * FROM scheduled_job ORDER BY name")
        json = dumps([tuple(row[1:]) for row in rows], indent=2)
        self.send_page(json, "json")

    @property
    def buttons(self):
        """Customize the set of action buttons displayed."""

        if not self.job:
            return (
                self.ADD,
                self.JSON,
                self.DEVMENU,
                self.ADMINMENU,
                self.LOG_OUT,
            )
        return (
            self.SAVE,
            self.DELETE,
            self.RUN,
            self.JOBS,
            self.DEVMENU,
            self.ADMINMENU,
            self.LOG_OUT,
        )

    @property
    def enabled(self):
        """True if the current job is allowed to run."""

        if not hasattr(self, "_enabled"):
            if self.request == self.ADD:
                self._enabled = True
            else:
                self._enabled = "enabled" in self.fields.getlist("opts")
        return self._enabled

    @property
    def id(self):
        """Primary key for the current job."""

        if not hasattr(self, "_id"):
            self._id = self.fields.getvalue("id", "").strip()
        return self._id

    @id.setter
    def id(self, value):
        """Allow the ID for a newly created job to be set."""
        self._id = value

    @property
    def job(self):
        """Object for the currently displayed job."""

        if not hasattr(self, "_job"):
            self._job = None
            if self.request in (self.ADD, self.RUN):
                self._job = Job(self)
            elif self.id:
                query = self.Query("scheduled_job", "*")
                query.where(query.Condition("id", self.id))
                row = query.execute(self.cursor).fetchone()
                if row:
                    self._job = Job(self, row)
        return self._job

    @property
    def job_class(self):
        """String for the job's implementing class (module_name.ClassName)."""

        if not hasattr(self, "_job_class"):
            self._job_class = self.fields.getvalue("job_class", "").strip()
            if self._job_class:
                if self._job_class.count(".") != 1:
                    self.bail(self.JOB_CLASS_ERROR)
                    module, name = self._job_class.split(".", 1)
                    if not module.strip() or not name.strip():
                        self.bail(self.JOB_CLASS_ERROR)
        return self._job_class

    @property
    def jobs(self):
        """Sequence of `Job` objects.

        Skip over the rows which are created for manual job execution.
        """

        if not hasattr(self, "_jobs"):
            query = self.Query("scheduled_job", "*").order("name")
            query.where("schedule IS NOT NULL OR enabled = 0")
            rows = query.execute(self.cursor).fetchall()
            self._jobs = [Job(self, row) for row in rows]
        return self._jobs

    @property
    def name(self):
        """Required string for the job name."""

        if not hasattr(self, "_name"):
            self._name = self.fields.getvalue("name", "").strip()
        return self._name

    @property
    def num_opts(self):
        """Integer for the number of job parameters."""

        if not hasattr(self, "_num_opts"):
            try:
                self._num_opts = int(self.fields.getvalue("num-opts", "0"))
            except Exception:
                self.bail("Internal error (invalid option count)")
        return self._num_opts

    @property
    def opts(self):
        """Dictionary of named job parameters."""

        if not hasattr(self, "_opts"):
            opts = {}
            i = 1
            while i <= self.num_opts:
                name = self.fields.getvalue(f"opt-name-{i:d}", "").strip()
                value = self.fields.getvalue(f"opt-value-{i:d}", "").strip()
                if name and value:
                    if name in opts:
                        self.bail(f"Duplicate option {name!r}")
                    elif self.supported_parameters is not None:
                        if name not in self.supported_parameters:
                            message = f"Parameter {name!r} not supported"
                            supported = ", ".join(self.supported_parameters)
                            extra = [f"Supported parameters: {supported}"]
                            self.bail(message, extra=extra)
                    opts[name] = value
                i += 1
            self._opts = dumps(opts)
        return self._opts

    @property
    def schedule(self):
        """Dictionary of values controlling when the job is executed."""

        if not hasattr(self, "_schedule"):
            values = {}
            for name in self.UNITS:
                value = self.fields.getvalue(name, "").strip()
                if value:
                    values[name] = value
            self._schedule = dumps(values)
        return self._schedule

    @property
    def subtitle(self):
        """Dynamically determine what to display below the main banner."""

        if not hasattr(self, "_subtitle"):
            if self.request == self.RUN:
                self._subtitle = f"Job {self.name!r} executed"
            elif self.request == self.SAVE:
                self._subtitle = f"Job {self.name!r} saved"
            else:
                self._subtitle = self.SUBTITLE
        return self._subtitle

    @property
    def supported_parameters(self):
        """Set of option names allowed for the job (None if unrestricted)."""

        if not hasattr(self, "_supported_parameters"):
            if "scheduler" not in str(path).lower():
                path.insert(1, "d:/cdr/Scheduler")
            self._supported_parameters = None
            try:
                module_name, class_name = self.job_class.split(".", 1)
                module = import_module(f"jobs.{module_name}")
                job_class = getattr(module, class_name)
                supported = getattr(job_class, "SUPPORTED_PARAMETERS")
                self._supported_parameters = supported
            except Exception as e:
                args = self.job_class, e
                self.logger.exception("supported_parameters for %s: %s", *args)
                self.bail(f"Unable to load jobs.{self.job_class}: {e}")
        return self._supported_parameters


class Job:
    """Information about a single scheduled job."""

    def __init__(self, control, row=None):
        """Capture the caller's values.

        Pass:
            control - access to the form values and logging
            row - values from the database for the job (None for new job)
        """

        self.__control = control
        self.__row = row

    @property
    def id(self):
        """String for the job's primary key."""

        if not hasattr(self, "_id"):
            if self.__row:
                self._id = self.__row.id
            else:
                self._id = self.__control.id
        return self._id

    @property
    def name(self):
        """Required string for the job name."""

        if not hasattr(self, "_name"):
            if self.__row:
                self._name = self.__row.name
            else:
                self._name = self.__control.name
        return self._name

    @property
    def enabled(self):
        """True if the job is allowed to run."""

        if not hasattr(self, "_enabled"):
            if self.__row:
                self._enabled = True if self.__row.enabled else False
            else:
                self._enabled = self.__control.enabled
        return self._enabled

    @property
    def job_class(self):
        """String for the job's implementing class (module_name.ClassName)."""

        if not hasattr(self, "_job_class"):
            if self.__row:
                self._job_class = self.__row.job_class
            else:
                self._job_class = self.__control.job_class
        return self._job_class

    @property
    def opts(self):
        """Dictionary of named job parameters."""

        if not hasattr(self, "_opts"):
            if self.__row:
                opts = self.__row.opts or "{}"
            else:
                opts = self.__control.opts
            try:
                self._opts = loads(opts)
            except Exception:
                self.__control.logger.exception(opts)
                self._opts = {}
        return self._opts

    @property
    def schedule(self):
        """Dictionary of values controlling when the job is executed."""

        if not hasattr(self, "_schedule"):
            if self.__row:
                schedule = self.__row.schedule or "{}"
            else:
                schedule = self.__control.schedule
            try:
                self._schedule = loads(schedule)
            except Exception:
                self.__control.logger.exception(schedule)
                self._schedule = {}
        return self._schedule

    @property
    def formatted_schedule(self):
        """User-friendly display of the job's schedule values."""

        if not hasattr(self, "_formatted_schedule"):
            self._formatted_schedule = ""
            if len(self.schedule) == 1 and "minute" in self.schedule:
                minutes = str(self.schedule["minute"])
                if minutes.startswith("*/"):
                    minutes = int(minutes[2:])
                    if minutes == 1:
                        self._formatted_schedule = "every minute"
                    elif minutes == 2:
                        self._formatted_schedule = "every other minute"
                    else:
                        o = ordinal(minutes)
                        self._formatted_schedule = f"every {o} minute"
                else:
                    minutes = int(minutes)
                    if not minutes:
                        self._formatted_schedule = "every hour on the hour"
                    else:
                        if minutes == 1:
                            when = "1 minute after the hour"
                        else:
                            when = f"{minutes} minutes after the hour"
                        self._formatted_schedule = f"every hour at {when}"
            elif "hour" in self.schedule and "minute" in self.schedule:
                try:
                    hour = int(self.schedule["hour"])
                    minute = int(self.schedule["minute"])
                    when = f"{hour:02d}:{minute:02d}"
                    dow_hour_minute = set(["day_of_week", "hour", "minute"])
                    if set(self.schedule) == dow_hour_minute:
                        dow = self.schedule["day_of_week"]
                        dow = [d.capitalize() for d in dow.split(",")]
                        dow = ", ".join(dow)
                        self._formatted_schedule = f"every {dow} at {when}"
                    elif len(self.schedule) == 2:
                        self._formatted_schedule = f"every day at {when}"
                    elif len(self.schedule) == 3 and "day" in self.schedule:
                        day = f"on the {ordinal(self.schedule['day'])}"
                        fs = f"every month {day} at {when}"
                        self._formatted_schedule = fs
                except Exception:
                    pass
            if not self._formatted_schedule:
                keys = sorted(self.schedule)
                values = [f"{key}={self.schedule[key]}" for key in keys]
                self._formatted_schedule = " ".join(values)
        return self._formatted_schedule


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
