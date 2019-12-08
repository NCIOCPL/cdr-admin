#!/usr/bin/env python

"""Show the status of jobs/documents on GateKeeper.

Web interface for requesting status from the Cancer.gov GateKeeper.
and testing if our record in pub_proc_cg confirms that the documents
have been published.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc
import cdr2gk
import re
from operator import attrgetter


class Control(Controller):

    SUBTITLE = "GateKeeper Status"
    INSTRUCTIONS = (
        "This interface is provided for submitting status requests to "
        "Cancer.gov's GateKeeper 2.0 and comparing them to what the "
        "CDR has recorded in the table pub_proc_cg. "
        "Currently the three types of status which can be requested are:",
        (
            (
                "Summary",
                "information about a specific push publishing job,",
            ),
            (
                "Single Document",
                "information about the location of an individual CDR "
                "document in the Cancer.gov system, and",
            ),
            (
                "All Documents",
                "that information for every document in the Cancer.gov "
                "system.",
            ),
        ),
        "Enter a Job ID to request a Summary report for that job. "
        "Enter a CDR ID to request a Single Document report for that "
        "document. If both Job ID and CDR ID are omitted, you will "
        "receive an All Documents report. If the 'Display all' option is "
        "removed only the recorded problems are displayed. "
        "Debug logging can be requested when needed for tracking down "
        "failures and other unexpected behavior.",
        "NOTE: The All Documents report is large; if you invoke it you "
        "should be prepared to wait a while for it to complete; if you "
        "invoke it with debug logging enabled, you will have a large "
        "amount of data added to the debug log.",
    )
    DISPLAY_ALL = "Display all documents, not just those with errors"
    STAGES = "gatekeeper", "preview", "live"

    def build_tables(self):
        """Assemble the table for the report."""

        if self.job_detail_table:
            return self.job_detail_table
        if self.doc_id:
            caption = f"Location Status for Document CDR{self.doc_id}"
            args = "SingleDocument", self.doc_id
        else:
            caption = "Location Status for All Documents"
            args = "DocumentLocation",
        try:
            response = cdr2gk.requestStatus(*args, host=self.host)
        except Exception as e:
            self.logger.exception("Status failure")
            self.bail(f"Status failure: {e}")
        cols = "CDR ID", "GateKeeper", "Preview", "Live", "CDR Record"
        rows = []
        docs = response.details.docs if response.details else []
        checked = missing = 0
        for doc in sorted(docs, key=attrgetter("cdrId")):
            if not self.should_skip(doc):
                checked += 1
                status = "OK" if int(doc.cdrId) in self.published else "Error"
                if status == "Error":
                    missing += 1
                elif not self.full and not self.doc_id:
                    continue
                stages = {}
                for stage in self.STAGES:
                    job_id = getattr(doc, f"{stage}JobId")
                    date_time = getattr(doc, f"{stage}DateTime")
                    stages[stage] = f"Job {job_id} ({date_time})"
                rows.append([
                    doc.cdrId,
                    stages["gatekeeper"],
                    stages["preview"],
                    stages["live"],
                    status,
                ])
        caption = (
            caption,
            f"{checked} Records Checked, {missing} Not In pub_proc_cg",
        )
        return self.Reporter.Table(rows, cols=cols, caption=caption)

    def populate_form(self, page):
        """Show the instructions and the form fields.

        Pass:
            page - HTMLPage object which displays the form
        """

        if self.job:
            self.show_report()
        fieldset = page.fieldset("Instructions")
        for instructions in self.INSTRUCTIONS:
            if isinstance(instructions, str):
                fieldset.append(page.B.P(instructions))
            else:
                ul = page.B.UL()
                for report_type, provided in instructions:
                    description = f", which provides {provided}"
                    ul.append(page.B.LI(page.B.B(report_type), description))
                fieldset.append(ul)
        page.form.append(fieldset)
        fieldset = page.fieldset("Report Parameters")
        opts = dict(value=self.host, label="Host")
        fieldset.append(page.text_field("targetHost", **opts))
        opts = dict(value=self.job_id, label="Job ID")
        fieldset.append(page.text_field("jobId", **opts))
        opts = dict(value=self.doc_id, label="CDR ID")
        fieldset.append(page.text_field("cdrId", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Options")
        opts = dict(label=self.DISPLAY_ALL, checked=self.full, value=1)
        fieldset.append(page.checkbox("flavor", **opts))
        opts = dict(label="Enable debug logging", checked=self.debug, value=1)
        fieldset.append(page.checkbox("debugLogging", **opts))
        page.form.append(fieldset)

    def should_skip(self, doc):
        """True if this document should not be included in the report.

        Pass:
            doc - object returned by GateKeeper for a single CDR document
        """

        if self.doc_id:
            return False
        for stage in self.STAGES:
            if getattr(doc, f"{stage}JobId") == "Not Present":
                return True
        return False

    def show_report(self):
        """Override so we can inject a job summary table."""

        cdr2gk.DEBUGLEVEL = 2 if self.debug else 0
        if self.job_summary_table is not None:
            self.report.page.form.insert(2, self.job_summary_table)
        self.report.send()

    @property
    def debug(self):
        """True if debug logging is requested."""
        return True if self.fields.getvalue("debugLogging") else False

    @property
    def doc_id(self):
        """CDR ID of the document selected for status reporting."""

        if not hasattr(self, "_doc_id"):
            self._doc_id = self.fields.getvalue("cdrId")
            if self._doc_id:
                try:
                    self._doc_id = Doc.extract_id(self._doc_id)
                except:
                    self.logger.exception("Can't parse %s", self._doc_id)
                    self.bail("Invalid CDR ID")
        return self._doc_id

    @property
    def full(self):
        """True if all documents should be shown; otherwise only problems."""

        if not hasattr(self, "_full"):
            if not self.job_id and not self.doc_id and not self.request:
                all = True
            else:
                all = True if self.fields.getvalue("flavor") else False
            self._full = all
        return self._full

    @property
    def host(self):
        """GateKeeper host name."""

        if not hasattr(self, "_host"):
            self._host = self.fields.getvalue("targetHost")
            if self._host:
                if not re.match("^[a-zA-Z0-9._-]+$", self._host):
                    self.bail("Invalid host name")
            else:
                self._host = cdr2gk.HOST
        return self._host

    @property
    def job(self):
        """Details about a specific job, if this is a job report."""

        if not hasattr(self, "_job"):
            self._job = None
            if self.job_id:
                try:
                    args = "Summary", self.job_id
                    self._job = cdr2gk.requestStatus(*args, host=self.host)
                except Exception as e:
                    self.logger.exception("Status failure")
                    self.bail(f"Job {self.job_id} not found: {e}")
        return self._job

    @property
    def job_detail_table(self):
        """Table showing the status for documents in a job."""

        if not self.job:
            return None
        if not hasattr(self, "_job_detail_table"):
            columns = (
                "Packet #",
                "Group",
                "CDR ID",
                "Pub Type",
                "Doc Type",
                "Status",
                "Dependent Status",
                "Location",
            )
            rows = []
            checked = errors = 0
            for doc in self.job.details.docs:
                checked += 1
                if self.full or doc.status == "Error":
                    if doc.status == "Error":
                        errors += 1
                    rows.append([
                        doc.packetNumber,
                        doc.group,
                        doc.cdrId,
                        doc.pubType,
                        doc.docType,
                        doc.status,
                        doc.dependentStatus,
                        doc.location,
                    ])
            caption = f"{checked:d} Documents Checked, {errors:d} Errors"
            opts = dict(caption=caption, columns=columns)
            self._job_detail_table = self.Reporter.Table(rows, **opts)
        return self._job_detail_table

    @property
    def job_id(self):
        """ID of the job for which status reporting has been requested."""

        if not hasattr(self, "_job_id"):
            self._job_id = self.fields.getvalue("jobId")
            if self._job_id:
                try:
                    self._job_id = int(self._job_id)
                except:
                    self.logger.exception("bad job id: %s", self._job_id)
                    self.bail("Invalid job ID")
        return self._job_id

    @property
    def job_summary_table(self):
        """Extra table to show details about the report's job."""

        if not self.job:
            return None
        return self.HTMLPage.B.TABLE(
            self.HTMLPage.B.CAPTION(f"Summary Report for Job {self.job_id}"),
            self.HTMLPage.B.TR(
                self.HTMLPage.B.TH(f"Job ID"),
                self.HTMLPage.B.TD(f"{self.job.details.jobId}")
            ),
            self.HTMLPage.B.TR(
                self.HTMLPage.B.TH(f"Request Type"),
                self.HTMLPage.B.TD(f"{self.job.details.requestType}")
            ),
            self.HTMLPage.B.TR(
                self.HTMLPage.B.TH(f"Description"),
                self.HTMLPage.B.TD(f"{self.job.details.description}")
            ),
            self.HTMLPage.B.TR(
                self.HTMLPage.B.TH(f"Status"),
                self.HTMLPage.B.TD(f"{self.job.details.status}")
            ),
            self.HTMLPage.B.TR(
                self.HTMLPage.B.TH(f"Source"),
                self.HTMLPage.B.TD(f"{self.job.details.source}")
            ),
            self.HTMLPage.B.TR(
                self.HTMLPage.B.TH(f"Initiated"),
                self.HTMLPage.B.TD(f"{self.job.details.initiated}")
            ),
            self.HTMLPage.B.TR(
                self.HTMLPage.B.TH(f"Completion"),
                self.HTMLPage.B.TD(f"{self.job.details.completion}")
            ),
            self.HTMLPage.B.TR(
                self.HTMLPage.B.TH(f"Target"),
                self.HTMLPage.B.TD(f"{self.job.details.target}")
            ),
            self.HTMLPage.B.TR(
                self.HTMLPage.B.TH(f"Expected Count"),
                self.HTMLPage.B.TD(f"{self.job.details.expectedCount}")
            ),
            self.HTMLPage.B.TR(
                self.HTMLPage.B.TH(f"Actual Count"),
                self.HTMLPage.B.TD(f"{self.job.details.actualCount}")
            )
        )

    @property
    def published(self):
        """Dictionary of documents which are (or should be) on the web site."""

        if not hasattr(self, "_published"):
            query = self.Query("pub_proc_cg c", "c.id", "t.name")
            query.join("all_docs d", "d.id = c.id")
            query.join("doc_type t", "t.id = d.doc_type")
            rows = query.execute(self.cursor).fetchall()
            self._published = dict([tuple(row) for row in rows])
        return self._published


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
