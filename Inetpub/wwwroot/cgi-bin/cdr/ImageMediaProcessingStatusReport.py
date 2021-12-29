#!/usr/bin/env python

"""Media (Images) Processing Status Report.
"""

from collections import defaultdict
from cdrcgi import Controller, WEBSERVER, BASE
from cdrapi.docs import Doc, Doctype


class Control(Controller):
    """Access to the database and report-building tools."""

    SUBTITLE = "Media (Images) Processing Status Report"

    def build_tables(self):
        """Assemble the table for this report."""

        opts = dict(caption=self.caption, columns=self.columns)
        return [self.Reporter.Table(self.rows, **opts)]

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

    @property
    def caption(self):
        """What we display above the table rows."""

        if not hasattr(self, "_caption"):
            self._caption = [self.subtitle]
            if self.start:
                if self.end:
                    self._caption.append(f"From {self.start} - {self.end}")
                else:
                    self._caption.append(f"On or after {self.start}")
            elif self.end:
                self._caption.append(f"On or before {self.end}")
            self._caption.append(f"Status: {self.status}")
        return self._caption

    @property
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

    @property
    def diagnoses(self):
        """Dictionary of diagnosis names indexed by CDR document ID."""

        if not hasattr(self, "_diagnoses"):
            path = "/Media/MediaContent/Diagnoses/Diagnosis/@cdr:ref"
            query = self.Query("query_term t", "t.doc_id", "t.value")
            query.unique().order(2)
            query.join("query_term m", "m.int_val = t.doc_id")
            query.where("t.path = '/Term/PreferredName'")
            query.where(f"m.path = '{path}'")
            rows = query.execute(self.cursor).fetchall()
            self._diagnoses = dict([tuple(row) for row in rows])
        return self._diagnoses

    @property
    def diagnosis(self):
        """Diagnosis (or diagnoses) selected for the report."""

        if not hasattr(self, "_diagnosis"):
            diagnoses = self.fields.getlist("diagnosis")
            try:
                self._diagnosis = [int(doc_id) for doc_id in diagnoses]
            except Exception:
                self.bail()
            if set(self._diagnosis) - set(self.diagnoses):
                self.bail()
        return self._diagnosis

    @property
    def docs(self):
        """Find the Media documents which are in scope for this report."""

        if not hasattr(self, "_docs"):
            if not self.status:
                self.bail("missing required status value")
            query = self.Query("query_term i", "i.doc_id")
            query.where("i.path = '/Media/PhysicalMedia/ImageData/ImageType'")
            if self.diagnosis:
                query.join("query_term d", "d.doc_id = i.doc_id")
                query.where(query.Condition("d.int_val", self.diagnosis, "IN"))
            self._docs = []
            for row in query.execute(self.cursor).fetchall():
                doc = MediaDoc(self, row.doc_id)
                if doc.in_scope:
                    self._docs.append(doc)
        return self._docs

    @property
    def end(self):
        """Object for the end of the date range for the report."""

        if not hasattr(self, "_end"):
            self._end = self.parse_date(self.fields.getvalue("end"))
        return self._end

    @property
    def end_string(self):
        """Version of the date range end comparable with text from XML docs."""

        if not hasattr(self, "_end_string"):
            self._end_string = str(self.end or "")
        return self._end_string

    @property
    def rows(self):
        """Table rows for the report."""

        if not hasattr(self, "_rows"):
            self._rows = [doc.row for doc in sorted(self.docs)]
        return self._rows

    @property
    def start(self):
        """Object for the start of the date range for the report."""

        if not hasattr(self, "_start"):
            self._start = self.parse_date(self.fields.getvalue("start"))
        return self._start

    @property
    def start_string(self):
        """Date range start comparable with text from XML docs."""

        if not hasattr(self, "_start_string"):
            self._start_string = str(self.start or "")
        return self._start_string

    @property
    def status(self):
        """Status selected for the report."""

        if not hasattr(self, "_status"):
            self._status = self.fields.getvalue("status")
            if self._status and self._status not in self.statuses:
                self.bail()
        return self._status

    @property
    def statuses(self):
        """Valid values for the status picklist."""

        if not hasattr(self, "_statuses"):
            doctype = Doctype(self.session, name="Media")
            statuses = doctype.vv_lists["ProcessingStatusValue"]
            self._statuses = [s for s in statuses if not s.startswith("Audio")]
        return self._statuses


class MediaDoc:
    """Media document to be considered for the report."""

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

    @property
    def control(self):
        """Access to the database and report-generation tools."""
        return self.__control

    @property
    def diagnoses(self):
        """List of diagnosis string link to this Media document."""

        if not hasattr(self, "_diagnoses"):
            self._diagnoses = []
            path = "MediaContent/Diagnoses/Diagnosis"
            for node in self.doc.root.findall(path):
                ref = node.get(f"{{{Doc.NS}}}ref")
                try:
                    id = Doc.extract_id(ref)
                    self._diagnoses.append(self.control.diagnoses[id])
                except Exception:
                    self._diagnoses.append(f"INVALID DIAGNOSIS ID {ref}")
        return self._diagnoses

    @property
    def doc(self):
        """`Doc` object for the CDR media document."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.control.session, id=self.__id)
            if self._doc.root is None:
                raise Exception(f"CDR{self.__id} is malformed")
        return self._doc

    @property
    def glossary_terms(self):
        """Sequence of strings for glossary docs to be used with this media."""
        return self.proposed_uses.get("Glossary", [])

    @property
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

    @property
    def key(self):
        """Make sorting case insensitive."""

        if not hasattr(self, "_key"):
            self._key = (self.title or "").lower()
        return self._key

    @property
    def last_publishable_date(self):
        """When was the most recent publishable version created?"""

        if not hasattr(self, "_last_publishable_date"):
            self._last_publishable_date = ""
            if self.doc.last_publishable_version:
                version = self.doc.last_publishable_version
                query = self.control.Query("doc_version", "dt")
                query.where(query.Condition("id", self.doc.id))
                query.where(query.Condition("num", version))
                row = query.execute(self.control.cursor).fetchone()
                if row and row.dt:
                    self._last_publishable_date = str(row.dt)[:10]
        return self._last_publishable_date

    @property
    def last_ver_pub(self):
        """True if the last version of the doc is marked as publishable."""

        if not hasattr(self, "_last_ver_pub"):
            self._last_ver_pub = False
            if self.doc.last_version:
                if self.doc.last_version == self.doc.last_publishable_version:
                    self._last_ver_pub = True
        return self._last_ver_pub

    @property
    def proposed_uses(self):
        """Dictionary of documents (by type) to use this Media document."""

        if not hasattr(self, "_proposed_uses"):
            self._proposed_uses = defaultdict(list)
            for node in self.doc.root.findall("ProposedUse/*"):
                ref = node.get(f"{{{Doc.NS}}}ref")
                try:
                    title = self.control.doc_titles[Doc.extract_id(ref)]
                    if title:
                        self._proposed_uses[node.tag].append(title)
                except Exception:
                    self.control.logger.exception(ref)
                    bogus = f"UNRESOLVEABLE DOCUMENT ID {ref}"
                    self._proposed_uses[node.tag].append(bogus)
        return self._proposed_uses

    @property
    def row(self):
        """This document's contribution to the report table."""

        if not hasattr(self, "_row"):
            Cell = self.control.Reporter.Cell
            self._row = (
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
        return self._row

    @property
    def status(self):
        """First processing status found in the document (if any)."""

        if not hasattr(self, "_status"):
            self._status = None
            node = self.doc.root.find("ProcessingStatuses/ProcessingStatus")
            if node is not None:
                self._status = self.Status(node)
        return self._status

    @property
    def summaries(self):
        """Sequence of strings for summary docs to be used with this media."""
        return self.proposed_uses.get("Summary", [])

    @property
    def title(self):
        """Title of the Media document."""

        if not hasattr(self, "_title"):
            title = Doc.get_text(self.doc.root.find("MediaTitle", ""))
            self._title = title.strip()
        return self._title

    @property
    def url(self):
        """Web address of the QC report for this document."""

        if not hasattr(self, "_url"):
            self._url = self.URL.format(self.doc.id)
        return self._url

    class Status:
        """Parsed processing status values."""

        def __init__(self, node):
            """Remember the caller's value.

            Pass:
                node - element block containing the values (or None)
            """

            self.__node = node

        @property
        def comments(self):
            """Sequence of comment strings for the status."""

            if not hasattr(self, "_comments"):
                self._comments = []
                for child in self.__node.findall("Comment"):
                    comment = Doc.get_text(child, "").strip()
                    if comment:
                        self._comments.append(comment)
            return self._comments

        @property
        def date(self):
            """String for the date the status was set (if available)."""

            if not hasattr(self, "_date"):
                child = self.__node.find("ProcessingStatusDate")
                self._date = Doc.get_text(child, "").strip()[:10]
            return self._date

        @property
        def value(self):
            """String for the status value (if applicable)."""

            if not hasattr(self, "_value"):
                child = self.__node.find("ProcessingStatusValue")
                self._value = Doc.get_text(child, "").strip()
            return self._value


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
