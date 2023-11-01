#!/usr/bin/env python

"""Update normalized links to selected summary.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc
from datetime import datetime
from functools import cached_property
from lxml import etree
from ModifyDocs import Job


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "Update SummaryRef Titles"
    LOGNAME = "update-summaryref-titles"
    COLS = "Linking ID", "Outcome"
    CAPTION = "Results"
    CSS = "th, td { background-color: #e8e8e8; border-color: #bbb; }"
    CONFIRM = "Confirm"

    def populate_form(self, page):
        """Ask for CDR ID of linked summary.

        If we have the ID, but the user hasn't seen the list of Summary
        documents which will be updated, show them. See OCECDR-5154.
        Pass:
            page - object on which we draw the form
        """

        if not self.id:
            fieldset = page.fieldset("Document ID of Linked Summary")
            opts = dict(label="CDR ID", value=self.id or "")
            fieldset.append(page.text_field("id", **opts))
            page.form.append(fieldset)
        else:
            rows = []
            for id in self.ids:
                summary = self.Summary(self, page, id)
                rows.append(summary.row)
            table = page.B.TABLE(
                page.B.CAPTION(
                    "Summary Documents to be Updated",
                    page.B.BR(),
                    "Unckeck the documents which should not be updated",
                    page.B.BR(),
                    "Press 'Confirm' button to proceed with updates",
                ),
                page.B.THEAD(
                    page.B.TR(
                        page.B.TH("Update?"),
                        page.B.TH("Locked By"),
                        page.B.TH("CDR ID"),
                        page.B.TH("Title"),
                        page.B.TH("Language"),
                        page.B.TH("Audience"),
                    )
                ),
                page.B.TBODY(*rows),
            )
            page.form.append(table)
            page.form.append(page.hidden_field("id", self.id))
            page.add_css(self.CSS)

    def build_tables(self):
        """Show the linking documents we examined.

        Return:
            `Reporter.Table` object
        """

        if not self.selected:
            self.show_form()
        self.logger.info("processing links to %s", self.cdr_id)
        job = Updater(self)
        job.run()
        self.logger.info("assembling table for %d docs", len(self.selected))
        rows = []
        for id in self.selected:
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

    def run(self):
        """Override to handle custom buttons."""

        try:
            if self.request and self.request == self.CONFIRM:
                self.show_report()
        except Exception as e:
            self.logger.exception("Control.run() failure")
            bail(e)
        Controller.run(self)

    @cached_property
    def buttons(self):
        """Override buttons for the confirmation page."""

        if self.selected:
            return self.SUBMENU, self.ADMINMENU, self.LOG_OUT
        elif self.id:
            return self.CONFIRM, self.SUBMENU, self.ADMINMENU, self.LOG_OUT
        return self.SUBMIT, self.SUBMENU, self.ADMINMENU, self.LOGOUT

    @cached_property
    def cdr_id(self):
        """Normalized CDR ID of the linked summary."""
        return Doc.normalize_id(self.id) if self.id else None

    @cached_property
    def id(self):
        """CDR ID of the linked summary."""

        id = self.fields.getvalue("id", "").strip()
        if not id:
            return None
        try:
            return Doc.extract_id(id)
        except Exception:
            return None

    @cached_property
    def ids(self):
        """CDR IDs of the linking summaries."""

        if not self.id:
            return None
        query = self.Query("query_term", "doc_id").unique()
        query.where("path LIKE '/Summary%/SummaryRef/@cdr:href'")
        query.where(query.Condition('int_val', self.id))
        rows = query.execute(self.cursor).fetchall()
        return sorted([row.doc_id for row in rows])

    @cached_property
    def linked_title(self):
        """SummaryTitle for the linked CDR document."""

        if not self.id:
            return None
        query = self.Query("query_term", "value")
        query.where(query.Condition("doc_id", self.id))
        query.where("path = '/Summary/SummaryTitle'")
        rows = query.execute(self.cursor).fetchall()
        return (rows[0].value if rows else "").strip()

    @cached_property
    def selected(self):
        """IDs of the documents the user wants to update."""

        try:
            return [int(id) for id in self.fields.getlist("selected")]
        except Exception:
            self.bail()


    class Summary:

        TITLE = "/Summary/SummaryTitle"
        LANGUAGE = "/Summary/SummaryMetaData/SummaryLanguage"
        AUDIENCE = "/Summary/SummaryMetaData/SummaryAudience"

        def __init__(self, control, page, id):
            """Capture information for linking Summary table row.

            Pass:
                control - access to the database
                page - access to HTML-building tools
                id - CDR ID for the Summary document
            """

            self.id = id
            self.control = control
            opts = dict(value=id, label="", checked=True)
            center = page.B.CLASS("center")
            self.row = page.B.TR(
                page.B.TD(page.checkbox("selected", **opts), center),
                page.B.TD(self.locked_by or ""),
                page.B.TD(str(id)),
                page.B.TD(self.lookup(control, id, self.TITLE)),
                page.B.TD(self.lookup(control, id, self.LANGUAGE)),
                page.B.TD(self.lookup(control, id, self.AUDIENCE)),
            )

        def lookup(self, control, id, path):
            """Find value from the query_term table for this Summary.

            Pass:
                control - access to the database
                id - CDR ID for the Summary document
                path - value for the path column in the query_term table

            Return:
                string for the requested value
            """

            query = control.Query("query_term", "value")
            query.where(query.Condition("doc_id", id))
            query.where(query.Condition("path", path))
            row = query.execute(control.cursor).fetchone()
            return row.value if row else "???"

        @cached_property
        def locked_by(self):
            """None or name of user who has the document checked out."""

            query = self.control.Query("usr u", "u.fullname")
            query.join("checkout c", "c.usr = u.id")
            query.where(query.Condition("c.id", self.id))
            query.where("c.dt_in IS NULL")
            rows = query.execute(self.control.cursor).fetchall()
            return rows[0][0] if rows else None

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
        return sorted(self.__control.selected)

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

    @cached_property
    def comment(self):
        """Custom comment embedding CDR ID of linked summary document."""

        return ("Updating SummaryRef titles (OCECDR-5068) "
                f"for {self.__control.cdr_id} {datetime.now()}")


if __name__ == "__main__":
    """Support loading as a module."""
    Control().run()
