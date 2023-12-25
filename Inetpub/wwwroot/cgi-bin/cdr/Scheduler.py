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

from functools import cached_property
from importlib import import_module
from json import loads, dumps
from cdrapi import db
from cdrcgi import Controller
from cdr import ordinal
from sys import path


class Control(Controller):
    """Top-level logic for the administrative interface."""

    LOGNAME = "new-schedule-manager"
    SUBTITLE = "Scheduled Jobs"
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

        # Display the form for editing or creating a job.
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
                fieldset.set("class", "opt-block usa-fieldset")
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
                fieldset.set("class", "opt-block usa-fieldset")
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

        # Show all the jobs.
        else:
            for legend in "Enabled", "Disabled":
                jobs = page.B.TBODY()
                for job in self.jobs:
                    if legend == "Disabled":
                        if job.enabled:
                            continue
                    elif not job.enabled:
                        continue
                    try:
                        schedule = job.formatted_schedule
                    except Exception:
                        schedule = job.schedule
                    url = self.make_url(self.script, id=job.id)
                    segments = [page.B.A(job.name, href=url)]
                    if schedule:
                        segments.append(f" ({schedule})")
                    opts = dict(title=f"Job class is {job.job_class}.")
                    jobs.append(page.B.TR(page.B.TD(*segments, **opts)))
                fieldset = page.fieldset(legend)
                table = page.B.TABLE(jobs)
                table.set("class", "usa-table usa-table--borderless")
                fieldset.append(table)
                page.form.append(fieldset)

            page.add_css(
                f".usa-form a:visited {{ color: {page.LINK_COLOR}; }}\n"
                ".usa-form a { text-decoration: none; }\n"
            )

    def run(self):
        """Override the base class version as this is not a standard report."""

        try:
            if not self.session.can_do("MANAGE SCHEDULER"):
                self.bail("Account not allowed to manage the scheduler")
        except Exception as e:
            self.bail(e)
        try:
            match self.request:
                case self.ADD:
                    return self.show_form()
                case self.SAVE:
                    return self.save_job()
                case self.DELETE:
                    return self.delete_job()
                case self.RUN:
                    return self.run_job()
                case self.JOBS:
                    self.job = None
                    return self.show_form()
                case self.JSON:
                    return self.json()
                case _:
                    Controller.run(self)
        except Exception as e:
            self.bail(e)

    def save_job(self):
        """Save the currently edited job and redraw the form.

        Make sure you don't reference the `job` property before
        putting the new values in the database.
        """

        if not self.name:
            self.alerts.append(dict(
                message="Job name is required.",
                type="error",
            ))
        if not self.job_class:
            self.alerts.append(dict(
                message="Class name for job is required.",
                type="error",
            ))
        if not self.alerts:
            values = [
                self.name,
                self.enabled,
                self.job_class,
                dumps(self.opts),
                self.schedule or None,
            ]
            try:
                if self.id:
                    values.append(self.id)
                    self.cursor.execute(self.UPDATE, values)
                else:
                    self.cursor.execute(self.INSERT, values)
                    self.id = self.cursor.fetchone().id
                self.conn.commit()
                self.logger.info("saved job %s", self.name)
                enabled = "Enabled" if self.job.enabled else "Disabled"
                message = f"{enabled} job {self.name!r} saved."
                if self.job.enabled:
                    if self.job.formatted_schedule:
                        when = self.job.formatted_schedule
                        message = f"{message} Job will run {when}."
                    else:
                        message = (
                            f"Enabled job {self.name!r} will be run but not "
                            "retained since it has no schedule. In order to "
                            "have the job retained for future use, save it "
                            "with a schedule."
                        )
                self.alerts.append(dict(message=message, type="success"))
            except Exception as e:
                self.logger.exception("save failed")
                self.alerts.append(dict(
                    message=f"Unable to save job: {e}",
                    type="error",
                ))
        self.show_form()

    def run_job(self):
        """Queue up the current job to run immediately and redraw the form.

        Note special handling for stopping the scheduler. See OCECDR-5125.
        """

        # Make sure we have the essential information for running the job.
        if not self.name:
            self.alerts.append(dict(
                message="Job name is required.",
                type="error",
            ))
        if not self.job_class:
            self.alerts.append(dict(
                message="Class name for job is required.",
                type="error",
            ))
        dbserver = self.opts.get("dbserver")
        if self.alerts:
            self.show_form()

        # Special handling for the pseudo-job to bounce the scheduler.
        if self.job_class == "stop_scheduler.Stop" and dbserver:
            conn = db.connect(server=dbserver)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO scheduled_job (name, enabled, job_class, opts)"
                " VALUES(?, 'TRUE', 'stop_scheduler.Stop', '{}')", (self.name,)
            )
            conn.commit()
            self.logger.info("queued stop job in %s db", self.opts["dbserver"])
        else:
            values = self.name, True, self.job_class, dumps(self.opts)
            self.cursor.execute(
                "INSERT INTO scheduled_job (name, enabled, job_class, opts)"
                "     VALUES (?, ?, ?, ?)", values)
            self.conn.commit()
        self.alerts.append(dict(
            message=f"Job {self.name!r} queued.",
            type="success",
        ))
        self.show_form()

    def delete_job(self):
        """Remove the current job and return to the job list.

        It's important that the `jobs` property is not referenced until
        the row for this job is removed from the database.
        """

        self.cursor.execute("DELETE FROM scheduled_job WHERE id = ?", self.id)
        self.conn.commit()
        self.logger.info("Job %s deleted", self.id)
        self.alerts.append(dict(
            message=f"Job {self.name} successfully deleted.",
            type="success",
        ))
        self.job = None
        self.show_form()

    def json(self):
        """Send the serialized jobs to the client."""

        rows = self.query.execute(self.cursor)
        json = dumps([tuple(row[1:]) for row in rows], indent=2)
        self.send_page(json, "json")

    @cached_property
    def buttons(self):
        """Customize the set of action buttons displayed."""

        if not self.job:
            return self.ADD, self.JSON
        return self.SAVE, self.DELETE, self.RUN, self.JOBS

    @cached_property
    def enabled(self):
        """True if the current job is allowed to run."""

        if self.request == self.ADD:
            return True
        return "enabled" in self.fields.getlist("opts")

    @cached_property
    def id(self):
        """Primary key for the current job."""
        return self.fields.getvalue("id", "").strip()

    @cached_property
    def job(self):
        """Object for the currently displayed job."""

        if self.request in (self.ADD, self.RUN):
            self.logger.info("returning Job(self)")
            return Job(self)
        if self.id:
            query = self.Query("scheduled_job", "*")
            query.where(query.Condition("id", self.id))
            row = query.execute(self.cursor).fetchone()
            if row:
                self.logger.info("returning Job(self, row)")
                return Job(self, row)
        elif self.request == self.SAVE:
            self.logger.info("returning Job(self) after rejected SAVE")
            return Job(self)
        return None

    @cached_property
    def job_class(self):
        """String for the job's implementing class (module_name.ClassName)."""

        job_class = self.fields.getvalue("job_class", "").strip()
        if job_class:
            if job_class.count(".") != 1:
                self.bail(self.JOB_CLASS_ERROR)
            module, name = job_class.split(".", 1)
            if not module.strip() or not name.strip():
                self.bail(self.JOB_CLASS_ERROR)
        return job_class

    @cached_property
    def jobs(self):
        """Sequence of `Job` objects.

        Skip over the rows which are created for manual job execution.
        """

        rows = self.query.execute(self.cursor).fetchall()
        return [Job(self, row) for row in rows]

    @cached_property
    def name(self):
        """Required string for the job name."""
        return self.fields.getvalue("name", "").strip()

    @cached_property
    def num_opts(self):
        """Integer for the number of job parameters."""

        try:
            return int(self.fields.getvalue("num-opts", "0"))
        except Exception:
            self.bail("Internal error (invalid option count)")

    @cached_property
    def opts(self):
        """Dictionary of named job parameters."""

        opts = {}
        i = 1
        while i <= self.num_opts:
            name = self.fields.getvalue(f"opt-name-{i:d}", "").strip()
            value = self.fields.getvalue(f"opt-value-{i:d}", "").strip()
            if name and value:
                if name in opts:
                    message = f"Duplicate option {name!r}."
                    self.logger.error(message)
                    self.alerts.append(dict(message=message, type="error"))
                elif self.supported_parameters is not None:
                    if name not in self.supported_parameters:
                        message = f"Parameter {name!r} not supported"
                        supported = ", ".join(self.supported_parameters)
                        extra = [f"Supported parameters: {supported}"]
                        self.logger.error(message)
                        self.alerts.append(dict(
                            message=message,
                            extra=extra,
                            type="error",
                        ))
                        continue
                opts[name] = value
            i += 1
        return opts

    @cached_property
    def query(self):
        """How we find the jobs which are not ephemeral."""

        scheduled = "schedule IS NOT NULL AND schedule <> '{}'"
        disabled = "enabled = 0"
        query = self.Query("scheduled_job", "*").order("name")
        query.where(f"{scheduled} OR {disabled}")
        return query

    @cached_property
    def same_window(self):
        """Stay on the same browser tab for all but the JSON command."""
        return self.SAVE, self.DELETE, self.RUN, self.JOBS, self.ADD

    @cached_property
    def schedule(self):
        """Dictionary of values controlling when the job is executed."""

        values = {}
        for name in self.UNITS:
            value = self.fields.getvalue(name, "").strip()
            if value:
                values[name] = value
        return dumps(values)

    @cached_property
    def supported_parameters(self):
        """Set of option names allowed for the job (None if unrestricted)."""

        if "scheduler" not in str(path).lower():
            path.insert(1, "d:/cdr/Scheduler")
        try:
            module_name, class_name = self.job_class.split(".", 1)
            module = import_module(f"jobs.{module_name}")
            job_class = getattr(module, class_name)
            supported = getattr(job_class, "SUPPORTED_PARAMETERS")
            return supported
        except Exception as e:
            args = self.job_class, e
            self.logger.exception("supported_parameters for %s: %s", *args)
            self.bail(f"Unable to load jobs.{self.job_class}: {e}")


class Job:
    """Information about a single scheduled job."""

    def __init__(self, control, row=None):
        """Capture the caller's values.

        Pass:
            control - access to the form values and logging
            row - values from the database for the job
        """

        self.control = control
        self.row = row

    @cached_property
    def id(self):
        """String for the job's primary key."""
        return self.row.id if self.row else self.control.id

    @cached_property
    def name(self):
        """Required string for the job name."""
        return self.row.name if self.row else self.control.name

    @cached_property
    def enabled(self):
        """True if the job is allowed to run."""

        if self.row:
            return True if self.row.enabled else False
        return self.control.enabled

    @cached_property
    def job_class(self):
        """String for the job's implementing class (module_name.ClassName)."""
        return self.row.job_class if self.row else self.control.job_class

    @cached_property
    def opts(self):
        """Dictionary of named job parameters."""

        if not self.row:
            return self.control.opts
        opts = self.row.opts or "{}"
        try:
            return loads(opts)
        except Exception:
            self.logger.exception(opts)
            return dict()

    @cached_property
    def schedule(self):
        """Dictionary of values controlling when the job is executed."""

        if self.row:
            schedule = self.row.schedule or "{}"
        else:
            schedule = self.control.schedule
        try:
            return loads(schedule)
        except Exception:
            self.logger.exception(schedule)
            return {}

    @cached_property
    def formatted_schedule(self):
        """User-friendly display of the job's schedule values."""

        if len(self.schedule) == 1 and "minute" in self.schedule:
            minutes = str(self.schedule["minute"])
            if minutes.startswith("*/"):
                minutes = int(minutes[2:])
                if minutes == 1:
                    return "every minute"
                if minutes == 2:
                    return "every other minute"
                return f"every {ordinal(minutes)} minute"
            minutes = int(minutes)
            if not minutes:
                return "every hour on the hour"
            if minutes == 1:
                return "1 minute after the hour"
            when = f"{minutes} minutes after the hour"
            return f"every hour at {when}"
        if "hour" in self.schedule:
            try:
                minute = int(self.schedule.get("minute", "0"))
                hour = str(self.schedule["hour"])
                if hour.startswith("*/"):
                    hour = int(hour[2:])
                    if not minute:
                        minutes = "on the hour"
                    elif minutes == 1:
                        minutes = "at 1 minute after the hour"
                    else:
                        minutes = f"at {minute} minutes after the hour"
                    if hour == 1:
                        when = f"every hour {minutes}"
                    elif hour == 2:
                        when = f"every other hour {minutes}"
                    else:
                        when = f"every {ordinal(hour)} hour {minutes}"
                else:
                    when = f"{int(hour):02d}:{minute:02d}"
                delta = set(self.schedule) - {"hour", "minute"}
                if not delta:
                    return f"every day at {when}"
                if delta == {"day_of_week"}:
                    dow = self.schedule["day_of_week"]
                    dow = [d.capitalize() for d in dow.split(",")]
                    dow = ", ".join(dow)
                    return f"every {dow} at {when}"
                if delta == {"day"}:
                    day = ordinal(self.schedule["day"])
                    return f"every month on the {day} at {when}"
            except Exception:
                self.logger.exception("funky schedule: %s", self.schedule)
        keys = sorted(self.schedule)
        values = [f"{key}={self.schedule[key]}" for key in keys]
        return " ".join(values)

    @cached_property
    def logger(self):
        """Keep a record of what we do."""
        return self.control.logger


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
