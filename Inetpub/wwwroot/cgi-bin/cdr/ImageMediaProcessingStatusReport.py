#!/usr/bin/env python

"""Media (Images) Processing Status Report.
"""

from functools import cached_property
from collections import defaultdict
from cdrcgi import Controller, BasicWebPage
from cdrapi.docs import Doc, Doctype


class Control(Controller):
    """Access to the database and report-building tools."""

    SUBTITLE = "Media (Images) Processing Status Report"

    def populate_form(self, page):
        """Put the fields we need on the form.

        Pass:
            page - HTMLPage instance where the fields go
        """

        fieldset = page.fieldset("Report Options (only Status is required)")
        fieldset.append(page.select("status", options=self.statuses))
        fieldset.append(page.date_field("start", label="Start Date"))
        fieldset.append(page.date_field("end", label="End Date"))
        opts = dict(options=self.diagnoses, multiple=True)
        fieldset.append(page.select("diagnosis", **opts))
        page.form.append(fieldset)
        page.add_output_options("html")

    def show_report(self):
        """Customized to accomodate an unusually wide report table."""

        opts = dict(caption=self.caption, columns=self.columns)
        table = self.Reporter.Table(self.rows, **opts)
        report = BasicWebPage()
        report.wrapper.append(report.B.H1(self.SUBTITLE))
        report.wrapper.append(table.node)
        report.wrapper.append(self.footer)
        report.send()

    @cached_property
    def caption(self):
        """What we display above the table rows."""

        caption = [self.subtitle]
        if self.start:
            if self.end:
                caption.append(f"From {self.start} - {self.end}")
            else:
                caption.append(f"On or after {self.start}")
        elif self.end:
            caption.append(f"On or before {self.end}")
        caption.append(f"Status: {self.status}")
        return caption

    @cached_property
    def columns(self):
        return (
            self.Reporter.Column("CDR ID"),
            self.Reporter.Column("Media Title", width="250px"),
            self.Reporter.Column("Diagnosis", width="150px"),
            self.Reporter.Column("Processing Status", width="150px"),
            self.Reporter.Column("Processing Status Date", width="100px"),
            self.Reporter.Column("Proposed Summaries", width="300px"),
            self.Reporter.Column("Proposed Glossary Terms", width="300px"),
            self.Reporter.Column("Comments", width="300px"),
            self.Reporter.Column("Last Version Publishable", width="125px"),
            self.Reporter.Column("Published", width="100px"),
        )

    @cached_property
    def diagnoses(self):
        """Dictionary of diagnosis names indexed by CDR document ID."""

        path = "/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref"
        query = self.Query("query_term t", "t.doc_id", "t.value")
        query.unique().order(2)
        query.join("query_term m", "m.int_val = t.doc_id")
        query.where("t.path = '/Term/PreferredName'")
        query.where(f"m.path = '{path}'")
        rows = query.execute(self.cursor).fetchall()
        return dict([tuple(row) for row in rows])

    @cached_property
    def diagnosis(self):
        """Diagnosis (or diagnoses) selected for the report."""

        diagnoses = self.fields.getlist("diagnosis")
        try:
            diagnoses = [int(doc_id) for doc_id in diagnoses]
        except Exception:
            self.bail()
        if set(diagnoses) - set(self.diagnoses):
            self.bail()
        return diagnoses

    @cached_property
    def docs(self):
        """Find the Media documents which are in scope for this report."""

        if not self.status:
            self.bail("missing required status value")
        query = self.Query("query_term i", "i.doc_id")
        query.where("i.path = '/Media/PhysicalMedia/ImageData/ImageType'")
        if self.diagnosis:
            query.join("query_term d", "d.doc_id = i.doc_id")
            query.where(query.Condition("d.int_val", self.diagnosis, "IN"))
        docs = []
        for row in query.execute(self.cursor).fetchall():
            doc = MediaDoc(self, row.doc_id)
            if doc.in_scope:
                docs.append(doc)
        return docs

    @cached_property
    def end(self):
        """Object for the end of the date range for the report."""
        return self.parse_date(self.fields.getvalue("end"))

    @cached_property
    def end_string(self):
        """Version of the date range end comparable with text from XML docs."""
        return str(self.end or "")

    @cached_property
    def rows(self):
        """Table rows for the report."""
        return [doc.row for doc in sorted(self.docs)]

    @cached_property
    def start(self):
        """Object for the start of the date range for the report."""
        return self.parse_date(self.fields.getvalue("start"))

    @cached_property
    def start_string(self):
        """Date range start comparable with text from XML docs."""
        return str(self.start or "")

    @cached_property
    def status(self):
        """Status selected for the report."""

        status = self.fields.getvalue("status")
        if status and status not in self.statuses:
            self.bail()
        return status

    @cached_property
    def statuses(self):
        """Valid values for the status picklist."""

        doctype = Doctype(self.session, name="Media")
        # pylint: disable-next=unsubscriptable-object
        statuses = doctype.vv_lists["ProcessingStatusValue"]
        return [s for s in statuses if not s.startswith("Audio")]


class MediaDoc:
    """Media document to be considered for the report."""

    WEBSERVER = Control.WEBSERVER
    BASE = Control.BASE
    URL = f"https://{WEBSERVER}{BASE}/QcReport.py?DocVersion=-1&DocId={{}}"

    def __init__(self, control, id):
        """Remember the caller's values.

        Pass:
            control - access to the database and report-creation tools
            id - integer for the unique CDR ID for this Media document
        """

        self.__control = control
        self.__id = id

    def __lt__(self, other):
        """Support sorting of the documents."""
        return self.key < other.key

    @cached_property
    def control(self):
        """Access to the database and report-generation tools."""
        return self.__control

    @cached_property
    def diagnoses(self):
        """List of diagnosis string link to this Media document."""

        diagnoses = []
        path = "MediaContent/Diagnoses/Diagnosis"
        for node in self.doc.root.findall(path):
            ref = node.get(f"{{{Doc.NS}}}ref")
            try:
                id = Doc.extract_id(ref)
                diagnoses.append(self.control.diagnoses[id])
            except Exception:
                diagnoses.append(f"INVALID DIAGNOSIS ID {ref}")
        return diagnoses

    @cached_property
    def doc(self):
        """`Doc` object for the CDR media document."""

        doc = Doc(self.control.session, id=self.__id)
        if doc.root is None:
            raise Exception(f"CDR{self.__id} is malformed")
        return doc

    @cached_property
    def glossary_terms(self):
        """Sequence of strings for glossary docs to be used with this media."""
        return self.proposed_uses.get("Glossary", [])

    @cached_property
    def in_scope(self):
        """Should this Media document be part of the report?"""

        if not self.status:
            return False
        if self.status.value != self.control.status:
            return False
        if self.control.start or self.control.end:
            if not self.status.date:
                return False
            if self.control.start:
                if self.status.date < self.control.start_string:
                    return False
            if self.control.end:
                if self.status.date > self.control.end_string:
                    return False
        return True

    @cached_property
    def key(self):
        """Make sorting case insensitive."""
        return (self.title or "").lower()

    @cached_property
    def last_publishable_date(self):
        """When was the most recent publishable version created?"""

        last_publishable_date = ""
        if self.doc.last_publishable_version:
            version = self.doc.last_publishable_version
            query = self.control.Query("doc_version", "dt")
            query.where(query.Condition("id", self.doc.id))
            query.where(query.Condition("num", version))
            row = query.execute(self.control.cursor).fetchone()
            if row and row.dt:
                last_publishable_date = str(row.dt)[:10]
        return last_publishable_date

    @cached_property
    def last_ver_pub(self):
        """True if the last version of the doc is marked as publishable."""

        if self.doc.last_version:
            if self.doc.last_version == self.doc.last_publishable_version:
                return True
        return False

    @cached_property
    def proposed_uses(self):
        """Dictionary of documents (by type) to use this Media document."""

        proposed_uses = defaultdict(list)
        for node in self.doc.root.findall("ProposedUse/*"):
            ref = node.get(f"{{{Doc.NS}}}ref")
            try:
                title = self.control.doc_titles[Doc.extract_id(ref)]
                if title:
                    proposed_uses[node.tag].append(title)
            except Exception:
                self.control.logger.exception(ref)
                bogus = f"UNRESOLVEABLE DOCUMENT ID {ref}"
                proposed_uses[node.tag].append(bogus)
        return proposed_uses

    @cached_property
    def row(self):
        """This document's contribution to the report table."""

        Cell = self.control.Reporter.Cell
        return (
            Cell(self.doc.id, href=self.url, target="_blank"),
            Cell(self.title),
            Cell("; ".join(self.diagnoses)),
            Cell(self.status.value),
            Cell(self.status.date, classes="nowrap center"),
            Cell("; ".join(self.summaries)),
            Cell("; ".join(self.glossary_terms)),
            Cell(self.status.comments),
            Cell("Yes" if self.last_ver_pub else "No", center=True),
            Cell(self.last_publishable_date, classes="nowrap center"),
        )

    @cached_property
    def status(self):
        """First processing status found in the document (if any)."""

        node = self.doc.root.find("ProcessingStatuses/ProcessingStatus")
        if node is not None:
            return self.Status(node)
        return None

    @cached_property
    def summaries(self):
        """Sequence of strings for summary docs to be used with this media."""
        return self.proposed_uses.get("Summary", [])

    @cached_property
    def title(self):
        """Title of the Media document."""
        return Doc.get_text(self.doc.root.find("MediaTitle", "")).strip()

    @cached_property
    def url(self):
        """Web address of the QC report for this document."""
        return self.URL.format(self.doc.id)

    class Status:
        """Parsed processing status values."""

        def __init__(self, node):
            """Remember the caller's value.

            Pass:
                node - element block containing the values (or None)
            """

            self.__node = node

        @cached_property
        def comments(self):
            """Sequence of comment strings for the status."""

            comments = []
            for child in self.__node.findall("Comment"):
                comment = Doc.get_text(child, "").strip()
                if comment:
                    comments.append(comment)
            return comments

        @cached_property
        def date(self):
            """String for the date the status was set (if available)."""

            child = self.__node.find("ProcessingStatusDate")
            return Doc.get_text(child, "").strip()[:10]

        @cached_property
        def value(self):
            """String for the status value (if applicable)."""

            child = self.__node.find("ProcessingStatusValue")
            return Doc.get_text(child, "").strip()


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""

    control = Control()
    try:
        control.run()
    except Exception as e:
        control.logger.exception("Failure: %s", e)
        control.bail(f"Failure: {e}")
