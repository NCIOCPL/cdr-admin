#!/usr/bin/env python3

from cdrcgi import Controller
from cdrapi.docs import Doc
from datetime import datetime
from lxml import etree
from ModifyDocs import Job


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "Update SummaryRef Titles"
    LOGNAME = "update-summaryref-titles"
    COLS = "Linking ID", "Outcome"
    CAPTION = "Results"

    def populate_form(self, page):
        """Ask for CDR ID of linked summary.

        Pass:
            page - object on which we draw the form
        """

        fieldset = page.fieldset("Document ID of Linked Summary")
        opts = dict(label="CDR ID", value=self.id or "")
        fieldset.append(page.text_field("id", **opts))
        page.form.append(fieldset)

    def build_tables(self):
        """Show the linking documents we examined.

        Return:
            `Reporter.Table` object
        """

        if not self.id:
            self.show_form()
        self.logger.info("processing links to %s", self.cdr_id)
        job = Updater(self)
        job.run()
        self.logger.info("assembling table for %d docs", len(self.ids))
        rows = []
        for id in self.ids:
            if id in job.successes:
                outcome = "Processed"
            elif id in job.unavailable:
                outcome = "Checked out to another user"
            elif id in job.failures:
                outcome = job.failures[id]
            else:
                # Don't think this can happen, but just in case ...
                outcome = "Unknown failure"
            cdr_id = Doc.normalize_id(id)
            url = f"QCReport.py?DocId={cdr_id}"
            link = self.Reporter.Cell(cdr_id, href=url, target="_blank")
            rows.append((link, outcome))
            self.logger.info("recording outcome %s for CDR%d", outcome, id)
        self.logger.info("returning table with %d rows", len(rows))
        return self.Reporter.Table(rows, cols=self.COLS, caption=self.CAPTION)

    @property
    def cdr_id(self):
        """Normalized CDR ID of the linked summary."""

        if not hasattr(self, "_cdr_id"):
            self._cdr_id = Doc.normalize_id(self.id) if self.id else None
        return self._cdr_id

    @property
    def id(self):
        """CDR ID of the linked summary."""

        if not hasattr(self, "_id"):
            self._id = self.fields.getvalue("id", "").strip()
            if self._id:
                try:
                    self._id = Doc.extract_id(self._id)
                except Exception:
                    self._id = None
        return self._id

    @property
    def ids(self):
        """CDR IDs of the linking summaries."""

        if not hasattr(self, "_ids"):
            self._ids = None
            if self.id:
                query = self.Query("query_term", "doc_id").unique()
                query.where("path LIKE '/Summary%/SummaryRef/@cdr:href'")
                query.where(query.Condition('int_val', self.id))
                rows = query.execute(self.cursor).fetchall()
                self._ids = sorted([row.doc_id for row in rows])
        return self._ids

    @property
    def linked_title(self):
        """SummaryTitle for the linked CDR document."""

        if not hasattr(self, "_linked_title"):
            self._linked_title = None
            if self.id:
                query = self.Query("query_term", "value")
                query.where(query.Condition("doc_id", self.id))
                query.where("path = '/Summary/SummaryTitle'")
                rows = query.execute(self.cursor).fetchall()
                title = rows[0].value if rows else ""
                self._linked_title = title.strip()
        return self._linked_title


class Updater(Job):
    """Global change job used to update SummaryRef titles."""

    LOGNAME = Control.LOGNAME
    HREF = f"{{{Doc.NS}}}href"

    def __init__(self, control):
        """Capture the caller's values.

        Pass:
            control - access to IDs and linked summary title
        """

        self.__control = control
        opts = dict(session=control.session, mode="live", console=False)
        Job.__init__(self, **opts)

    def select(self):
        """Return sequence of CDR ID integers for documents to transform."""
        return self.__control.ids

    def transform(self, doc):
        """Refresh the SummaryRef elements linked to the target summary.

        Pass:
            doc - reference to `cdr.Doc` object

        Return:
            serialized XML for the modified document
        """

        # Process the links to the target summary.
        root = etree.fromstring(doc.xml)
        for node in root.iter("SummaryRef"):
            if node.get(self.HREF) == self.__control.cdr_id:
                for child in node.getchildren():
                    node.remove(child)
                node.text = self.__control.linked_title

        # Return the results.
        return etree.tostring(root)

    @property
    def comment(self):
        """Custom comment embedding CDR ID of linked summary document."""

        if not hasattr(self, "_comment"):
            self._comment = ("Updating SummaryRef titles (OCECDR-5068) "
                             f"for {self.__control.cdr_id} {datetime.now()}")
        return self._comment


if __name__ == "__main__":
    """Support loading as a module."""
    Control().run()
