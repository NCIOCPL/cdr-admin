#!/usr/bin/env python

"""Show the status of a publishing job.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi import db
import datetime


class Control(Controller):

    SUBTITLE = "Publishing Status"
    LOGNAME = "PubStatus"
    DETAILS = "Show Document Details"
    JOB_TYPES = (
        "All",
        "Export",
        "Interim-Export",
        "Hotfix-Export",
        "Hotfix-Remove",
        "Republish-Export",
    )
    CSS = "#primary-form .usa-button { margin: 0 .5rem 1rem 0; }"

    def run(self):
        """Override the base class method to customize routing."""

        if self.request == self.SUBMIT and not (self.start and self.end):
            self.show_form()
        elif self.request == self.DETAILS:
            self.show_report()
        elif not self.request and (self.id or self.start and self.end):
            self.show_report()
        else:
            Controller.run(self)

    def populate_form(self, page):
        """Ask the user for report parameters.

        Pass:
            page - HTMLPage object on which we build the form
        """

        fieldset = page.fieldset("Report Parameters")
        end = datetime.date.today()
        start = end - datetime.timedelta(7)
        opts = dict(label="Start Date", value=start)
        fieldset.append(page.date_field("start", **opts))
        opts = dict(label="End Date", value=end)
        fieldset.append(page.date_field("end", **opts))
        opts = dict(label="Job Type", options=self.JOB_TYPES)
        fieldset.append(page.select("type", **opts))
        page.form.append(fieldset)

    @cached_property
    def alert(self):
        return self.fields.getvalue("alert")

    @cached_property
    def caption(self):
        """Caption string displayed above list of jobs."""

        return (
            f"{self.job_type} Publishing Jobs",
            f"From {self.start} to {self.end}",
        )

    @cached_property
    def columns(self):
        """Columns for the list of jobs matching the user's criteria."""

        return (
            self.Reporter.Column("ID", classes="text-center"),
            self.Reporter.Column("Type", classes="text-left"),
            self.Reporter.Column("Status", classes="text-left"),
            self.Reporter.Column("Started", classes="text-center"),
            self.Reporter.Column("Finished", classes="text-center"),
            self.Reporter.Column("Errors", classes="text-right"),
            self.Reporter.Column("Warnings", classes="text-right"),
            self.Reporter.Column("Total", classes="text-right"),
        )

    @cached_property
    def conn(self):
        """We need a connection with a longer timeout."""
        return db.connect(timeout=900)

    @cached_property
    def cursor(self):
        """Patient access to the database."""
        return self.conn.cursor()

    @cached_property
    def end(self):
        """End of the reporting date range."""

        try:
            return self.parse_date(self.fields.getvalue("end"))
        except Exception:
            self.bail("Invalid end date")

    @cached_property
    def id(self):
        """Integer for the ID of the job to report on."""

        id = self.fields.getvalue("id")
        if not id:
            return None
        if not id.isdigit():
            self.bail("Job ID must be an integer")
        return int(id)

    @cached_property
    def job_details(self):
        """Information for a report on a specific publishing job."""
        return JobDetails(self) if self.id else None

    @cached_property
    def jobs(self):
        """Jobs which match the user's criteria."""

        end = f"{self.end} 23:59:59"
        fields = "id", "pub_subset", "started", "completed", "status"
        query = self.Query("pub_proc", *fields).order("id DESC")
        query.where(query.Condition("pub_system", self.pub_system))
        query.where(query.Condition("started", self.start, ">="))
        query.where(query.Condition("started", end, "<="))
        if self.job_type and self.job_type != "All":
            push_type = f"Push_Documents_To_Cancer.Gov_{self.job_type}"
            types = self.job_type, push_type
            query.where(query.Condition("pub_subset", types, "IN"))
        query.log()
        rows = query.execute(self.cursor).fetchall()
        return [Job(self, row) for row in rows]

    @cached_property
    def job_type(self):
        """String for type of job on which to report."""

        job_type = self.fields.getvalue("type")
        if job_type and job_type not in self.JOB_TYPES:
            self.bail("Invalid job type")
        return job_type

    @cached_property
    def loglevel(self):
        """How much logging we should perform (default INFO)."""
        return self.fields.getvalue("level") or "INFO"

    @cached_property
    def pub_system(self):
        """ID for the control document for the Primary publishing system."""

        query = self.Query("active_doc d", "d.id")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'PublishingSystem'")
        query.where("d.title = 'Primary'")
        return query.execute(self.cursor).fetchall()[0].id

    @cached_property
    def report(self):
        """Add buttons and alerts as appropriate."""

        opts = dict(
            control=self,
            footer=self.footer,
            subtitle=self.subtitle,
            page_opts=dict(session=self.session, action=self.script),
        )
        report = self.Reporter(self.title, self.tables, **opts)
        if self.job_details:
            report.page.add_css("""\
.overview td:first-child, .overview th:first-child {
  width: 20rem;
}""")
        if self.alert:
            report.page.add_alert(self.alert, type="success")
        if self.show_summary:
            report.page.form.insert(0, report.page.button(self.DETAILS))
            report.page.add_css(self.CSS)
        report.page.form.append(report.page.hidden_field("id", self.id))
        return report

    @cached_property
    def rows(self):
        """Values for the report table."""
        return [job.row for job in self.jobs]

    @cached_property
    def show_details(self):
        """True if we have a job ID and we are showing per-document details."""
        return self.id and self.job_details.show_details

    @cached_property
    def show_summary(self):
        """True if we have a job but aren't showing per-document details."""
        return self.id and not self.show_details

    @cached_property
    def start(self):
        """Beginning of the reporting date range."""

        try:
            return self.parse_date(self.fields.getvalue("start"))
        except Exception:
            self.bail("Invalid start date")

    @cached_property
    def tables(self):
        """Assemble the tables appropriate for the parameters we are given."""

        if self.job_details:
            return self.job_details.tables
        else:
            opts = dict(columns=self.columns, caption=self.caption)
            return self.Reporter.Table(self.rows, **opts)

    @cached_property
    def wide_css(self):
        """Some versions of the report need more space."""
        return self.Reporter.Table.WIDE_CSS if not self.show_summary else None


class JobDetails:
    """Information for a report on a single job."""

    THRESHOLD = 100
    PUSH_PREFIX = "Push_Documents_To_Cancer.Gov_"

    def __init__(self, control):
        """Remember the caller's value.

        Pass:
            control - access to the database and the report parameters
        """

        self.control = control

    @cached_property
    def doc_titles(self):
        """Dictionary of titles for docs in job (optimization)."""

        query = self.control.Query("document d", "d.id", "d.title")
        query.join("pub_proc_doc p", "p.doc_id = d.id")
        query.where(query.Condition("p.pub_proc", self.id))
        rows = query.execute(self.control.cursor).fetchall()
        return dict([tuple(row) for row in rows])

    @cached_property
    def docs(self):
        """Documents in this job."""

        query = self.control.Query("pub_proc_doc", "*")
        query.where(query.Condition("pub_proc", self.id))
        rows = query.execute(self.control.cursor).fetchall()
        return [self.Doc(self, row) for row in rows]

    @cached_property
    def doctypes(self):
        """Dictionary of doctype strings for docs in job (optimization)."""

        query = self.control.Query("doc_type t", "d.id", "t.name")
        query.join("document d", "d.doc_type = t.id")
        query.join("pub_proc_doc p", "p.doc_id = d.id")
        query.where(query.Condition("p.pub_proc", self.id))
        rows = query.execute(self.control.cursor).fetchall()
        return dict([tuple(row) for row in rows])

    @cached_property
    def document_table(self):
        """Table listing or summarizing the documents for this job."""

        if self.show_details:
            rows = [doc.row for doc in self.docs]
            columns = ["ID", "Version", "Type", "Title", "Failed", "Warnings"]
            columns.append("Action" if self.is_push else "Removed")
            opts = dict(caption="Documents", columns=columns)
            return self.control.Reporter.Table(rows, **opts)
        columns = [
            self.control.Reporter.Column("Type", classes="text-left"),
            self.control.Reporter.Column("Total", classes="text-right"),
        ]
        if self.is_push:
            columns += [
                self.control.Reporter.Column("Added", classes="text-right"),
                self.control.Reporter.Column("Updated", classes="text-right"),
            ]
        columns += [
            self.control.Reporter.Column("Removed", classes="text-right"),
            self.control.Reporter.Column("Failures", classes="text-right"),
            self.control.Reporter.Column("Warnings", classes="text-right"),
        ]
        opts = dict(caption="Documents", columns=columns)
        return self.control.Reporter.Table(self.rows, **opts)

    @cached_property
    def export_job_id(self):
        """Find the job whose documents we are pushing."""

        subset = self.row.pub_subset.replace(self.PUSH_PREFIX, "")
        query = self.control.Query("pub_proc", "MAX(id) AS id")
        query.where(query.Condition("pub_subset", subset))
        query.where(query.Condition("id", self.id, "<"))
        query.where("status = 'Success'")
        return query.execute(self.control.cursor).fetchone().id

    @cached_property
    def id(self):
        """Integer for this job's ID."""
        return self.control.id

    @cached_property
    def failures(self):
        """Table showing failed documents (if any)."""

        rows = []
        for doc in self.docs:
            if doc.failed:
                details = self.parse(doc.messages) or "[NO ERROR MESSAGE]"
                rows.append([
                    self.control.Reporter.Cell(doc.id, right=True),
                    doc.doctype,
                    self.control.Reporter.Cell(details),
                ])
        if rows:
            columns = "ID", "Type", "Details"
            opts = dict(columns=columns, caption="Failures")
            return self.control.Reporter.Table(rows, **opts)
        return None

    @cached_property
    def is_push(self):
        """True if this job pushed documents to the CMS."""
        return "Push" in self.row.pub_subset

    @cached_property
    def last_full_push_job(self):
        """Job ID for the most recent full load push job."""

        query = self.control.Query("pub_proc", "MAX(id) AS id")
        query.where("pub_subset = 'Push_Documents_To_Cancer.Gov_Full-Load'")
        query.where("status = 'Success'")
        return query.execute(self.control.cursor).fetchone().id

    @cached_property
    def next_successful_export_job(self):
        """Integer for the ID of the next successful job of this type."""

        query = self.control.Query("pub_proc", "MIN(id) AS id")
        query.where(query.Condition("id", self.id, ">"))
        query.where(query.Condition("pub_subset", self.row.pub_subset))
        query.where("status = 'Success'")
        query.log()
        row = query.execute(self.control.cursor).fetchone()
        return row.id if row else None

    @cached_property
    def overview(self):
        """Identification values for this job."""

        row = self.row
        values = [
            row.title,
            row.pub_subset,
            row.name,
            row.output_dir,
            str(row.started)[:19],
            str(row.completed)[:19] if row.completed else "[not recorded]",
            row.status,
            row.messages,
            len(self.docs),
        ]
        labels = [
            "Publishing System",
            "System Subset",
            "User Name",
            "Output Location",
            "Started",
            "Completed",
            "Status",
            "Messages",
            "Total Documents",
        ]
        Cell = self.control.Reporter.Cell
        if self.is_push:
            job_id = self.export_job_id
            url = self.control.make_url(self.control.script, id=job_id)
            values.append(Cell(job_id, href=url))
            labels.append("Export Job")
        elif self.row.status == "Success":
            for job in self.push_jobs:
                if job.status == "Success":
                    labels.append("Push Job")
                elif job.status == "Failure":
                    labels.append("Failed Push Job")
                else:
                    labels.append(f"Push Job ({job.status})")
                url = self.control.make_url(self.control.script, id=job.id)
                values.append(Cell(job.id, href=url))
        rows = []
        for i, value in enumerate(values):
            label = labels[i]
            rows.append((Cell(label, bold=True, right=True), value))
        flavor = "Push" if "Push" in self.row.pub_subset else "Publishing"
        opts = dict(caption=f"{flavor} Job {self.id}", classes="overview")
        return self.control.Reporter.Table(rows, **opts)

    @cached_property
    def parameters(self):
        """Settings chosen for this job."""

        fields = "parm_name", "parm_value"
        query = self.control.Query("pub_proc_parm", *fields).order(1)
        query.where(query.Condition("pub_proc", self.id))
        rows = query.execute(self.control.cursor).fetchall()
        rows = [tuple(row) for row in rows]
        columns = "Name", "Value"
        opts = dict(columns=columns, caption="Parameters", classes="overview")
        return self.control.Reporter.Table(rows, **opts)

    @cached_property
    def previous_pushes(self):
        """IDs for docs in this job whose last prev push was not a remove."""

        fields = "d.doc_id", "MAX(p.id) AS id"
        subquery = self.control.Query("pub_proc_doc d", *fields)
        subquery.join("pub_proc p", "p.id = d.pub_proc")
        subquery.join("pub_proc_doc j", "j.doc_id = d.doc_id")
        subquery.where(f"j.pub_proc = {self.id}")
        subquery.where(f"d.pub_proc < {self.id}")
        subquery.where(f"d.pub_proc >= {self.last_full_push_job}")
        subquery.where("d.failure IS NULL")
        subquery.where("p.status = 'Success'")
        subquery.where(f"p.pub_subset LIKE '{self.PUSH_PREFIX}%'")
        subquery.group("d.doc_id")
        subquery.alias("p")
        fields = "d.doc_id", "d.removed"
        query = self.control.Query("pub_proc_doc d", *fields)
        query.join(subquery, "p.id = d.pub_proc", "p.doc_id = d.doc_id")
        previous_pushes = set()
        for row in query.execute(self.control.cursor).fetchall():
            if row.removed != "Y":
                previous_pushes.add(row.doc_id)
        return previous_pushes

    @cached_property
    def push_jobs(self):
        """ID/status pairs of job(s) pushing the docs from this export job."""

        subset = f"{self.PUSH_PREFIX}{self.row.pub_subset}"
        query = self.control.Query("pub_proc", "id", "status").order("id")
        query.where(f"pub_subset = '{subset}'")
        query.where(query.Condition("id", self.id, ">"))
        if self.next_successful_export_job:
            args = "id", self.next_successful_export_job, "<"
            query.where(query.Condition(*args))
        query.log()
        return query.execute(self.control.cursor).fetchall()

    @cached_property
    def row(self):
        """Basic values from the job's pub_proc table row."""

        fields = (
            "d.title",
            "p.pub_subset",
            "u.name",
            "p.output_dir",
            "p.started",
            "p.completed",
            "p.status",
            "p.messages",
        )
        query = self.control.Query("pub_proc p", *fields)
        query.join("document d", "d.id = p.pub_system")
        query.join("usr u", "u.id = p.usr")
        query.where(query.Condition("p.id", self.id))
        return query.execute(self.control.cursor).fetchone()

    @cached_property
    def rows(self):
        """Summary statistics by document type for jobs with lots of docs."""

        doctypes = {}
        for doc in self.docs:
            stats = doctypes.get(doc.doctype)
            if stats is None:
                stats = doctypes[doc.doctype] = dict(
                    total=0,
                    failures=0,
                    warnings=0,
                    removed=0,
                    added=0,
                    updated=0,
                )
            stats["total"] += 1
            if doc.failed:
                stats["failures"] += 1
            elif doc.messages:
                stats["warnings"] += 1
            if doc.removed:
                stats["removed"] += 1
            elif self.is_push:
                if doc.action == "added":
                    stats["added"] += 1
                else:
                    stats["updated"] += 1
        rows = []
        Cell = self.control.Reporter.Cell
        for doctype in sorted(doctypes):
            stats = doctypes[doctype]
            row = [doctype, Cell(stats["total"], right=True)]
            if self.is_push:
                row.append(Cell(stats["added"], right=True))
                row.append(Cell(stats["updated"], right=True))
            row += [
                Cell(stats["removed"], right=True),
                Cell(stats["failures"], right=True),
                Cell(stats["warnings"], right=True),
            ]
            rows.append(row)
        return rows

    @cached_property
    def show_details(self):
        """Whether to show information about each document in the job."""

        if len(self.docs) < self.THRESHOLD:
            return True
        elif self.control.request == Control.DETAILS:
            return True
        return False

    @cached_property
    def tables(self):
        """Sequence of tables for the status report on this job."""

        tables = [
            self.overview,
            self.parameters,
        ]
        if self.docs:
            tables.append(self.document_table)
        if self.failures:
            tables.append(self.failures)
        if self.warnings:
            tables.append(self.warnings)
        return tables

    @cached_property
    def warnings(self):
        """Table showing documents with non-fatal warnings (if any)."""

        rows = []
        for doc in self.docs:
            if doc.messages and not doc.failed:
                rows.append([
                    self.control.Reporter.Cell(doc.id, right=True),
                    doc.doctype,
                    self.control.Reporter.Cell(self.parse(doc.messages)),
                ])
        if rows:
            columns = "ID", "Type", "Details"
            opts = dict(columns=columns, caption="Warnings")
            return self.control.Reporter.Table(rows, **opts)
        return None

    @staticmethod
    def parse(messages):
        """Evaluate a string created with repr() returning a string list.

        Should have used JSON. :-(
        """

        if not messages:
            return ""
        try:
            parsed = eval(messages)
            if isinstance(parsed, (list, tuple)):
                return parsed
        except Exception:
            pass
        return str(messages)

    class Doc:
        """Document from a publishing job."""

        def __init__(self, job, row):
            """Remember the caller's values.

            Pass:
                job - access to information about the job and the database
                row - values from the database query
            """

            self.job = job
            self.db_row = row

        def __lt__(self, other):
            """Support sorting by document ID."""
            return self.id < other.id

        @cached_property
        def action(self):
            """One of added|updated|removed."""

            if self.removed:
                return "removed"
            if self.id in self.job.previous_pushes:
                return "updated"
            return "added"

        @cached_property
        def doctype(self):
            """String for the name of this document's type."""
            return self.job.doctypes[self.id]

        @cached_property
        def failed(self):
            """True if publishing failed for this document."""
            return True if self.db_row.failure == "Y" else False

        @cached_property
        def id(self):
            """Integer for the CDR document ID."""
            return self.db_row.doc_id

        @cached_property
        def messages(self):
            """Warning or error messages for this document."""
            return self.db_row.messages

        @cached_property
        def removed(self):
            """True if the document was being removed by this job."""
            return True if self.db_row.removed == "Y" else False

        @cached_property
        def row(self):
            """Values for the document table."""

            Cell = self.job.control.Reporter.Cell
            row = [
                Cell(self.id),
                Cell(self.version),
                self.doctype,
                self.title,
                Cell("Yes" if self.failed else "No"),
                Cell("Yes" if not self.failed and self.messages else "No"),
            ]
            if self.job.is_push:
                row.append(self.action)
            else:
                row.append(Cell("Yes" if self.removed else "No"))
            return row

        @cached_property
        def version(self):
            """Integer for the version of the document which was published."""
            return self.db_row.doc_version

        @cached_property
        def title(self):
            """Title for the document as of this version."""
            return self.job.doc_titles[self.id]


class Job:
    """Publishing job information for list of jobs."""

    def __init__(self, control, row):
        """Remember the caller's values.

        Pass:
            control  access to the database and the report parameters
            row - values from the database
        """

        self.control = control
        self.db_row = row

    @cached_property
    def counts(self):
        """Counts of documents with warnings/errors."""

        class Counts:
            def __init__(self):
                self.warnings = self.errors = 0
        counts = Counts()
        for doc in self.docs:
            if doc.failure == "Y":
                counts.errors += 1
            elif doc.messages is not None:
                counts.warnings += 1
        return counts

    @cached_property
    def docs(self):
        """Sequence of information on documents in this publishing job."""

        fields = "failure", "messages"
        query = self.control.Query("pub_proc_doc", *fields)
        query.where(query.Condition("pub_proc", self.id))
        return query.execute(self.control.cursor).fetchall()

    @cached_property
    def id(self):
        """Integer for the job's ID."""
        return self.db_row.id

    @cached_property
    def row(self):
        """Values for the table listing matching publishing jobs."""

        Cell = self.control.Reporter.Cell
        url = self.control.make_url(self.control.script, id=self.id)
        started = str(self.db_row.started)[:19]
        completed = str(self.db_row.completed)[:19]
        if completed == "None":
            completed = "[not recorded]"
        return (
            Cell(self.db_row.id, href=url, center=True),
            Cell(self.db_row.pub_subset),
            Cell(self.db_row.status),
            Cell(started, center=True),
            Cell(completed, center=True),
            Cell(self.counts.errors, right=True),
            Cell(self.counts.warnings, right=True),
            Cell(len(self.docs), right=True),
        )


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""

    control = Control()
    try:
        control.run()
    except Exception as e:
        control.logger.exception("Status failure")
        control.bail(e)
