#!/usr/bin/env python

"""Show the status of a publishing job.
"""

from cdrcgi import Controller
from cdrapi import db
from cdrapi.docs import Doc, Doctype
import datetime


class Control(Controller):

    SUBTITLE = "Publishing Status"
    LOGNAME = "PubStatus"
    DETAILS = "Details"
    JOB_TYPES = (
        "All",
        "Export",
        "Interim-Export",
        "Hotfix-Export",
        "Hotfix-Remove",
        "Republish-Export",
    )

    def run(self):
        """Override the base class method to customize routing."""

        try:
            if self.request == self.DETAILS:
                self.show_report()
            elif not self.request and (self.id or self.start and self.end):
                self.show_report()
            else:
                Controller.run(self)
        except Exception as e:
            self.logger.exception("Status failure")
            self.bail(e)

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

    def build_tables(self):
        """Assemble the tables appropriate for the parameters we are given."""

        if self.job_details:
            return self.job_details.tables
        else:
            opts = dict(columns=self.columns, caption=self.caption)
            return self.Reporter.Table(self.rows, **opts)

    def show_report(self):
        """Override base class version to customize the form."""

        if self.request == self.SUBMIT and not (self.start and self.end):
            self.show_form()
        if self.job_details:
            page = self.report.page
            form = page.form
            form.append(page.hidden_field("id", self.id))
            if not self.job_details.show_details:
                button = page.button(self.DETAILS)
                buttons = form.find("header/h1/span")
                buttons.insert(0, button)
        self.report.send()

    @property
    def caption(self):
        """Caption string displayed above list of jobs."""

        return (
            f"{self.job_type} Publishing Jobs",
            f"From {self.start} to {self.end}",
        )

    @property
    def columns(self):
        """Columns for the list of jobs matching the user's criteria."""

        return (
            "Job ID",
            "Job Type",
            "Job Status",
            "Job Start",
            "Job Finish",
            "Docs With Errors",
            "Docs With Warnings",
            "Total Docs",
        )

    @property
    def conn(self):
        """We need a connection with a longer timeout."""

        if not hasattr(self, "_conn"):
            self._conn = db.connect(timeout=900)
        return self._conn

    @property
    def cursor(self):
        """Patient access to the database."""

        if not hasattr(self, "_cursor"):
            self._cursor = self.conn.cursor()
        return self._cursor

    @property
    def end(self):
        """End of the reporting date range."""

        if not hasattr(self, "_end"):
            try:
                self._end = self.parse_date(self.fields.getvalue("end"))
            except Exception:
                self.bail("Date must use ISO format (YYYY-MM-DD)")
        return self._end

    @property
    def id(self):
        """Integer for the ID of the job to report on."""

        if not hasattr(self, "_id"):
            self._id = self.fields.getvalue("id")
            if self._id:
                if not self._id.isdigit():
                    self.bail("Job ID must be an integer")
                self._id = int(self._id)
        return self._id

    @property
    def job_details(self):
        """Information for a report on a specific publishing job."""

        if not hasattr(self, "_job_details"):
            self._job_details = JobDetails(self) if self.id else None
        return self._job_details

    @property
    def jobs(self):
        """Jobs which match the user's criteria."""

        if not hasattr(self, "_jobs"):
            end = f"{self.end} 23:59:59"
            fields = "id", "pub_subset", "started", "completed", "status"
            query = self.Query("pub_proc", *fields).order("id DESC")
            query.where(query.Condition("pub_system", self.pub_system))
            query.where(query.Condition("started", self.start, ">="))
            query.where(query.Condition("started", end, "<="))
            #query.where("status in ('Success', 'Verifying')")
            if self.job_type and self.job_type != "All":
                push_type = f"Push_Documents_To_Cancer.Gov_{self.job_type}"
                types = self.job_type, push_type
                query.where(query.Condition("pub_subset", types, "IN"))
            rows = query.execute(self.cursor).fetchall()
            self._jobs = [Job(self, row) for row in rows]
        return self._jobs

    @property
    def job_type(self):
        """String for type of job on which to report."""

        if not hasattr(self, "_job_type"):
            self._job_type = self.fields.getvalue("type")
            if self._job_type and self._job_type not in self.JOB_TYPES:
                self.bail("Invalid job type")
        return self._job_type

    @property
    def loglevel(self):
        """How much logging we should perform (default INFO)."""
        return self.fields.getvalue("level") or "INFO"

    @property
    def method(self):
        """Override base class to place the parameters in the URL."""
        return "get"

    @property
    def pub_system(self):
        """ID for the control document for the Primary publishing system."""

        if not hasattr(self, "_pub_system"):
            query = self.Query("active_doc d", "d.id")
            query.join("doc_type t", "t.id = d.doc_type")
            query.where("t.name = 'PublishingSystem'")
            query.where("d.title = 'Primary'")
            self._pub_system = query.execute(self.cursor).fetchall()[0].id
        return self._pub_system

    @property
    def rows(self):
        """Values for the report table."""
        return [job.row for job in self.jobs]

    @property
    def start(self):
        """Beginning of the reporting date range."""

        if not hasattr(self, "_start"):
            try:
                self._start = self.parse_date(self.fields.getvalue("start"))
            except Exception:
                self.bail("Date must use ISO format (YYYY-MM-DD)")
        return self._start


class JobDetails:
    """Information for a report on a single job."""

    THRESHOLD = 100
    PUSH_PREFIX = "Push_Documents_To_Cancer.Gov_"

    def __init__(self, control):
        """Remember the caller's value.

        Pass:
            control - access to the database and the report parameters
        """

        self.__control = control

    @property
    def control(self):
        """Access to the database and the report parameters."""
        return self.__control

    @property
    def doc_titles(self):
        """Dictionary of titles for docs in job (optimization)."""

        if not hasattr(self, "_doc_titles"):
            query = self.control.Query("document d", "d.id", "d.title")
            query.join("pub_proc_doc p", "p.doc_id = d.id")
            query.where(query.Condition("p.pub_proc", self.id))
            rows = query.execute(self.control.cursor).fetchall()
            self._doc_titles = dict([tuple(row) for row in rows])
        return self._doc_titles

    @property
    def doctypes(self):
        """Dictionary of doctype strings for docs in job (optimization)."""

        if not hasattr(self, "_doctypes"):
            query = self.control.Query("doc_type t", "d.id", "t.name")
            query.join("document d", "d.doc_type = t.id")
            query.join("pub_proc_doc p", "p.doc_id = d.id")
            query.where(query.Condition("p.pub_proc", self.id))
            rows = query.execute(self.control.cursor).fetchall()
            self._doctypes = dict([tuple(row) for row in rows])
        return self._doctypes

    @property
    def docs(self):
        """Documents in this job."""

        if not hasattr(self, "_docs"):
            query = self.control.Query("pub_proc_doc", "*")
            query.where(query.Condition("pub_proc", self.id))
            rows = query.execute(self.control.cursor).fetchall()
            self._docs = [self.Doc(self, row) for row in rows]
        return self._docs

    @property
    def document_table(self):
        """Table listing or summarizing the documents for this job."""

        if self.show_details:
            rows = [doc.row for doc in self.docs]
            columns = ["ID", "Version", "Type", "Title", "Failed", "Warnings"]
            columns.append("Action" if self.is_push else "Removed")
            opts = dict(caption="Documents", columns=columns)
            return self.control.Reporter.Table(rows, **opts)
        columns = ["Type", "Total"]
        if self.is_push:
            columns += ["Added", "Updated"]
        columns += ["Removed", "Failures", "Warnings"]
        opts = dict(caption="Documents", columns=columns)
        return self.control.Reporter.Table(self.rows, **opts)

    @property
    def export_job_id(self):
        """Find the job whose documents we are pushing."""

        if not hasattr(self, "_export_job_id"):
            subset = self.row.pub_subset.replace(self.PUSH_PREFIX, "")
            query = self.control.Query("pub_proc", "MAX(id) AS id")
            query.where(query.Condition("pub_subset", subset))
            query.where(query.Condition("id", self.id, "<"))
            query.where("status = 'Success'")
            row = query.execute(self.control.cursor).fetchone()
            self._export_job_id = row.id
        return self._export_job_id

    @property
    def id(self):
        """Integer for this job's ID."""
        return self.control.id

    @property
    def failures(self):
        """Table showing failed documents (if any)."""

        if not hasattr(self, "_failures"):
            self._failures = None
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
                self._failures = self.control.Reporter.Table(rows, **opts)
        return self._failures

    @property
    def is_push(self):
        """True if this job pushed documents to the CMS."""

        if not hasattr(self, "_is_push"):
            self._is_push = "Push" in self.row.pub_subset
        return self._is_push

    @property
    def last_full_push_job(self):
        """Job ID for the most recent full load push job."""

        query = self.control.Query("pub_proc", "MAX(id) AS id")
        query.where("pub_subset = 'Push_Documents_To_Cancer.Gov_Full-Load'")
        query.where("status = 'Success'")
        return query.execute(self.control.cursor).fetchone().id

    @property
    def next_successful_export_job(self):
        """Integer for the ID of the next successful job of this type."""

        if not hasattr(self, "_next_successful_export_job"):
            query = self.control.Query("pub_proc", "MIN(id) AS id")
            query.where(query.Condition("id", self.id, ">"))
            query.where(query.Condition("pub_subset", self.row.pub_subset))
            query.where("status = 'Success'")
            query.log()
            row = query.execute(self.control.cursor).fetchone()
            self._next_successful_export_job = row.id if row else None
        return self._next_successful_export_job

    @property
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
        caption = f"{flavor} Job {self.id}"
        return self.control.Reporter.Table(rows, caption=caption)

    @property
    def parameters(self):
        """Settings chosen for this job."""

        fields = "parm_name", "parm_value"
        query = self.control.Query("pub_proc_parm", *fields).order(1)
        query.where(query.Condition("pub_proc", self.id))
        rows = query.execute(self.control.cursor).fetchall()
        rows = [tuple(row) for row in rows]
        columns = "Name", "Value"
        opts = dict(columns=columns, caption="Parameters")
        return self.control.Reporter.Table(rows, **opts)

    @property
    def previous_pushes(self):
        """IDs for docs in this job whose last prev push was not a remove."""

        if not hasattr(self, "_previous_pushes"):
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
            self._previous_pushes = set()
            for row in query.execute(self.control.cursor).fetchall():
                if row.removed != "Y":
                    self._previous_pushes.add(row.doc_id)
        return self._previous_pushes

    @property
    def push_jobs(self):
        """ID/status pairs of job(s) pushing the docs from this export job."""

        if not hasattr(self, "_push_job_id"):
            subset = f"{self.PUSH_PREFIX}{self.row.pub_subset}"
            query = self.control.Query("pub_proc", "id", "status").order("id")
            query.where(f"pub_subset = '{subset}'")
            query.where(query.Condition("id", self.id, ">"))
            if self.next_successful_export_job:
                args = "id", self.next_successful_export_job, "<"
                query.where(query.Condition(*args))
            query.log()
            self._push_jobs = query.execute(self.control.cursor).fetchall()
        return self._push_jobs

    @property
    def row(self):
        """Basic values from the job's pub_proc table row."""

        if not hasattr(self, "_row"):
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
            self._row = query.execute(self.control.cursor).fetchone()
        return self._row

    @property
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

    @property
    def show_details(self):
        """Whether to show information about each document in the job."""

        if not hasattr(self, "_show_details"):
            self._show_details = False
            if len(self.docs) < self.THRESHOLD:
                self._show_details = True
            elif self.control.request == Control.DETAILS:
                self._show_details = True
        return self._show_details

    @property
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

    @property
    def warnings(self):
        """Table showing documents with non-fatal warnings (if any)."""

        if not hasattr(self, "_warnings"):
            self._warnings = None
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
                self._warnings = self.control.Reporter.Table(rows, **opts)
        return self._warnings

    @staticmethod
    def parse(messages):
        """Evaluate a string created with repr() returning a string list."""

        if not messages:
            return ""
        try:
            parsed = eval(messages)
            if isinstance(parsed, (list, tuple)):
                return parsed
        except:
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

            self.__job = job
            self.__row = row

        def __lt__(self, other):
            """Support sorting by document ID."""
            return self.id < other.id

        @property
        def action(self):
            """One of added|updated|removed."""

            if not hasattr(self, "_action"):
                if self.removed:
                    self._action = "removed"
                elif self.id in self.__job.previous_pushes:
                    self._action = "updated"
                else:
                    self._action = "added"
            return self._action

        @property
        def doctype(self):
            """String for the name of this document's type."""

            if not hasattr(self, "_doctype"):
                self._doctype = self.__job.doctypes[self.id]
            return self._doctype

        @property
        def failed(self):
            """True if publishing failed for this document."""
            return True if self.__row.failure == "Y" else False

        @property
        def id(self):
            """Integer for the CDR document ID."""
            return self.__row.doc_id

        @property
        def messages(self):
            """Warning or error messages for this document."""
            return self.__row.messages

        @property
        def removed(self):
            """True if the document was being removed by this job."""
            return True if self.__row.removed == "Y" else False

        @property
        def row(self):
            """Values for the document table."""

            Cell = self.__job.control.Reporter.Cell
            row = [
                Cell(self.id, right=True),
                Cell(self.version, right=True),
                self.doctype,
                self.title,
                Cell("Yes" if self.failed else "No", center=True),
                Cell("Yes" if not self.failed and self.messages else "No",
                     center=True),
            ]
            if self.__job.is_push:
                row.append(self.action)
            else:
                row.append(Cell("Yes" if self.removed else "No", center=True))
            return row

        @property
        def version(self):
            """Integer for the version of the document which was published."""
            return self.__row.doc_version

        @property
        def title(self):
            """Title for the document as of this version."""

            if not hasattr(self, "_title"):
                self._title = self.__job.doc_titles[self.id]
            return self._title


class Job:
    """Publishing job information for list of jobs."""

    def __init__(self, control, row):
        """Remember the caller's values.

        Pass:
            control  access to the database and the report parameters
            row - values from the database
        """

        self.__control = control
        self.__row = row

    @property
    def docs(self):
        """Sequence of information on documents in this publishing job."""

        if not hasattr(self, "_docs"):
            fields = "failure", "messages"
            query = self.__control.Query("pub_proc_doc", *fields)
            query.where(query.Condition("pub_proc", self.__row.id))
            self._docs = query.execute(self.__control.cursor).fetchall()
        return self._docs

    @property
    def errors(self):
        """Count of documents which failed for this job."""

        if not hasattr(self, "_errors"):
            self._errors = self._warnings = 0
            for doc in self.docs:
                if doc.failure == "Y":
                    self._errors += 1
                elif doc.messages is not None:
                    self._warnings += 1
        return self._errors

    @property
    def id(self):
        """Integer for the job's ID."""

        return self.__row.id

    @property
    def row(self):
        """Values for the table listing matching publishing jobs."""

        Cell = self.__control.Reporter.Cell
        url = self.__control.make_url(self.__control.script, id=self.__row.id)
        started = str(self.__row.started)[:19]
        completed = str(self.__row.completed)[:19]
        if completed == "None":
            completed = "[not recorded]"
        return (
            Cell(self.__row.id, href=url, center=True),
            Cell(self.__row.pub_subset),
            Cell(self.__row.status),
            Cell(started, center=True),
            Cell(completed, center=True),
            Cell(self.errors, right=True),
            Cell(self.warnings, right=True),
            Cell(len(self.docs), right=True),
        )

    @property
    def warnings(self):
        """Count of documents with non-fatal warnings for this job."""

        if not hasattr(self, "_warnings"):
            self._errors = self._warnings = 0
            for doc in self.docs:
                if doc.failure == "Y":
                    self._errors += 1
                elif doc.messages is not None:
                    self._warnings += 1
        return self._warnings


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
