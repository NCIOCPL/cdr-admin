#!/usr/bin/env python

"""Show version history of document.

Show form for selecting document (and possibly intermediate form
for choosing from multiple matches to title field), then collect
information about the selected document's versions and display it.
"""

from collections import defaultdict
from functools import cached_property
from cdrapi.docs import Doc
from cdrcgi import Controller


class Control(Controller):
    """Access to database and report-generation tools."""

    SUBTITLE = "Document Version History Report"

    def build_tables(self):
        """Pass on the work to the `Document` object."""

        if not self.doc_id:
            self.show_form()
        return self.document.tables

    def populate_form(self, page):
        """Show one of two forms, or jump to report, depending.

        Pass:
            page - HTMLPage object where the form fields go
            titles - sequence of documents to choose from
        """

        if self.doc_id:
            self.show_report()
        elif self.titles:
            titles = self.titles
            legend = "Choose Document"
            if len(titles) > 500:
                legend += " (First 500 Shown)"
                titles = titles[:500]
            fieldset = page.fieldset(legend)
            checked = True
            for doc_id, doc_title, doc_type in titles:
                tooltip = f"CDR{doc_id:d} ({doc_type}) {doc_title}"
                if len(doc_title) > 90:
                    doc_title = doc_title[:90] + " ..."
                opts = dict(
                    label=doc_title,
                    value=doc_id,
                    checked=checked,
                    tooltip=tooltip,
                )
                fieldset.append(page.radio_button(self.DOCID, **opts))
                checked = False
            page.form.append(fieldset)
        else:
            fieldset = page.fieldset("Specify Document ID or Title")
            fieldset.append(page.text_field(self.DOCID, label="Doc ID"))
            fieldset.append(page.text_field("DocTitle", label="Doc Title"))
            page.form.append(fieldset)

    def show_report(self):
        """Override to add some styling to the version table."""

        elapsed = self.report.page.html.get_element_by_id("elapsed", None)
        if elapsed is not None:
            elapsed.text = str(self.elapsed)
        self.report.page.add_css("#version-table td { vertical-align: top; }")
        self.report.send(self.format)

    @cached_property
    def doc_id(self):
        """Integer for CDR ID of selected document."""

        doc_id = self.fields.getvalue(self.DOCID)
        if doc_id:
            try:
                return Doc.extract_id(doc_id)
            except Exception:
                self.bail("Not a valid document ID")
        elif self.titles and len(self.titles) == 1:
            return self.titles[0][0]
        return None

    @cached_property
    def document(self):
        """`Document` object for the subject of the report."""
        return Document(self, self.doc_id)

    @cached_property
    def titles(self):
        """Document titles matching title fragment."""

        if self.fragment:
            fragment = f"{self.fragment}%"
            fields = "d.id", "d.title", "t.name"
            query = self.Query("document d", *fields).order(2)
            query.join("doc_type t", "t.id = d.doc_type")
            query.where(query.Condition("title", fragment, "LIKE"))
            rows = query.execute(self.cursor).fetchall()
            if not rows:
                self.bail("No matching documents found.")
            return rows
        return None

    @cached_property
    def fragment(self):
        """Title fragment for selecting a matching document."""
        return self.fields.getvalue("DocTitle", "").strip()

    @property
    def method(self):
        """Override base class version to use GET requests."""
        return "GET"

    @property
    def same_window(self):
        """Decide when to avoid opening a new browser tab."""
        return [self.SUBMIT] if self.fragment or self.doc_id else []

    @cached_property
    def suppress_sidenav(self):
        """Don't show the left navigation column on followup pages."""
        return True if self.doc_id or self.fragment else False


class Document:
    "CDR document which will be the subject of the requested report"

    def __init__(self, control, doc_id):
        """Remember the caller's values.

        Pass:
            control - access to the database and report-building tools
            doc_id - integer for the CDR document's unique identifier
        """

        self.__control = control
        self.__doc_id = doc_id

    @property
    def blocked(self):
        """True if the CDR document can't be published."""
        return self.doc.active_status != Doc.ACTIVE

    @property
    def columns(self):
        """Headers for the top of the version table columns."""

        if not hasattr(self, "_columns"):
            self._columns = (
                self.__control.Reporter.Column("Ver"),
                self.__control.Reporter.Column("Comment"),
                self.__control.Reporter.Column("Date"),
                self.__control.Reporter.Column("User"),
                self.__control.Reporter.Column("Val"),
                self.__control.Reporter.Column("Pub?"),
                self.__control.Reporter.Column("Publication Date(s)"),
            )
        return self._columns

    @property
    def control(self):
        """Access to the database and report-building tools."""
        return self.__control

    @property
    def created(self):
        """When was this document first created?"""

        if not hasattr(self, "_created"):
            self._created = str(self.doc.creation.when)[:10]
        return self._created

    @property
    def creator(self):
        """Who first created this document?"""

        if not hasattr(self, "_creator"):
            self._creator = "[Conversion]"
            user = self.doc.creation.user
            if user:
                self._creator = user.fullname or user.name or "[Conversion]"
        return self._creator

    @property
    def doc(self):
        """Instance of the `cdrapi.docs.Doc` class."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.control.session, id=self.__doc_id)
        return self._doc

    @property
    def full_load_remove_date(self):
        """First full load after last publication.

        We're looking for an explanation for why the document isn't
        on the web site. One possibility is that a full load took
        place after the last time this document was published.
        Rare but possible.
        """

        if not hasattr(self, "_full_load_remove_date"):
            self._full_load_remove_date = None
            if self.last_push_job:
                query = self.control.Query("pub_proc", "MIN(started)")
                query.where("status = 'Success'")
                query.where("pub_subset = 'Full-Load'")
                query.where(query.Condition("id", self.last_push_job, ">"))
                rows = query.execute(self.control.cursor).fetchall()
                if rows:
                    self._full_load_remove_date = str(rows[0][0])[:10]
        return self._full_load_remove_date

    @property
    def info_table(self):
        """Rotated table for document information independent of any version.

        Headers are lined up vertically in the first column. Values
        are in the second column.
        """

        if not hasattr(self, "_info_table"):
            Cell = self.control.Reporter.Cell
            values = [
                ("Document", f"{self.doc.cdr_id} ({self.doc.doctype})"),
                ("Title", self.doc.title),
            ]
            if self.removal:
                status = f"BLOCKED FOR PUBLICATION ({self.removal})"
                values.append(("Status", Cell(status, classes="blocked")))
            values.append(("Created", f"{self.created} by {self.creator}"))
            if self.updated:
                values.append(("Updated", f"{self.updated} by {self.updater}"))
            rows = []
            for label, value in values:
                rows.append((Cell(label, right=True, bold=True), value))
            self._info_table = self.control.Reporter.Table(rows)
        return self._info_table

    @property
    def last_push_job(self):
        """Job ID of the most recent push to cancer.gov for this document."""

        if not hasattr(self, "_last_push_job"):
            self._last_push_job = None
            for event in self.pub_events:
                if event.type == "C" and not event.removed:
                    self._last_push_job = event.job_id
                    return event.job_id
        return self._last_push_job

    @property
    def pub_events(self):
        """Sequence of publishing events in reverse chronological order."""

        if not hasattr(self, "_pub_events"):
            query = self.control.Query("primary_pub_doc", "*")
            query.where(query.Condition("doc_id", self.doc.id))
            query.order("started DESC", "pub_proc DESC")
            rows = query.execute(self.control.cursor).fetchall()
            self._pub_events = [self.PubEvent(self, row) for row in rows]
        return self._pub_events

    @property
    def pub_events_by_version(self):
        """Dictionary of publishing events indexed by version.

        For this grouping we want oldest events first in each sequence.
        """

        if not hasattr(self, "_pub_events_by_version"):
            self._pub_events_by_version = defaultdict(list)
            for event in reversed(self.pub_events):
                self._pub_events_by_version[event.doc_version].append(event)
        return self._pub_events_by_version

    @property
    def published(self):
        """True if the document is currently on the web site."""

        if not hasattr(self, "_published"):
            query = self.control.Query("pub_proc_cg", "id")
            query.where(query.Condition("id", self.doc.id))
            rows = query.execute(self.control.cursor).fetchall()
            self._published = True if rows else False
        return self._published

    @property
    def removal(self):
        """Information about the last removal from cancer.gov, if applicable.

        If a document has been blocked for publication (doc_status is 'I' --
        for "Inactive") we display an extra row showing the status and the
        date the document was pulled from Cancer.gov (assuming it has been
        pulled).
        """

        if not hasattr(self, "_removal"):
            self._removal = None
            # Only set for currently blocked documents.
            if self.blocked:
                # Make sure we have a removal date.  Normally we will, if the
                # document has ever been published, because when the document
                # is blocked the next publication event sends an instruction
                # to Cancer.gov to withdraw the document, in which case we
                # will have picked up the removal date when we collected the
                # information on publication events.
                if self.removed:
                    self._removal = f"removed {self.removed}"
                elif self.published:
                    # The document is still on cancer.gov, which means it was
                    # blocked since it was last published and will be removed
                    # as part of the next publication job. However, only a
                    # versioned document can be removed, so we check to see
                    # if a version has been created since the last version
                    # which got published.
                    if self.versions:
                        self._removal = "not yet removed"
                    else:
                        self._removal = "needs versioning to be removed"
                # The document isn't on Cancer.gov.  Was it removed by
                # a full load (meaning the sequence of events was
                # publication of the document when it was active,
                # followed by a change of status to inactive, after
                # which the next publication event was a full load)?
                elif self.full_load_remove_date:
                    self._removal = f"removed {self.full_load_remove_date}"
                elif not self.last_push_job:
                    # If that didn't happen, then presumably the document
                    # was never published.
                    self._removal = "never pushed to cancer.gov"
                else:
                    # Otherwise, we have a data corruption problem.
                    self._removal = "CAN'T DETERMINE REMOVAL DATE"
        return self._removal

    @property
    def removed(self):
        """Date the last time this doc was removed from cancer.gov, if ever.

        Only calculated if the document is currently blocked from publication.
        """

        if not hasattr(self, "_removed"):
            self._removed = None
            if self.blocked:
                for event in self.pub_events:
                    if event.removed:
                        self._removed = event.date
                        return event.date
        return self._removed

    @property
    def tables(self):
        """Pull together the two tables used by this report."""
        return self.info_table, self.version_table

    @property
    def updated(self):
        """When was this document last updated?"""

        if not hasattr(self, "_updated"):
            self._updated = None
            if self.doc.modification:
                self._updated = str(self.doc.modification.when)[:10]
        return self._updated

    @property
    def updater(self):
        """Who last modified this document?"""

        if not hasattr(self, "_updater"):
            self._updater = "N/A"
            if self.doc.modification:
                user = self.doc.modification.user
                if user:
                    self._updater = user.fullname or user.name or "N/A"
        return self._updater

    @property
    def version_table(self):
        """Report table with one row for each version."""

        if not hasattr(self, "_version_table"):
            rows = [version.row for version in self.versions]
            opts = dict(columns=self.columns, id="version-table")
            self._version_table = self.control.Reporter.Table(rows, **opts)
        return self._version_table

    @property
    def versions(self):
        """All the versions created for this document.

        Put the most recent versions at the front, because those are the ones
        we're most likely to be interested in.
        """

        if not hasattr(self, "_versions"):
            fields = (
                "v.num",
                "v.comment",
                "u.fullname",
                "u.name",
                "v.dt",
                "v.val_status",
                "v.publishable",
            )
            query = self.control.Query("doc_version v", *fields)
            query.order("v.num DESC")
            query.join("open_usr u", "u.id = v.usr")
            query.where(query.Condition("v.id", self.doc.id))
            rows = query.execute(self.control.cursor).fetchall()
            self._versions = [self.Version(self, row) for row in rows]
        return self._versions

    class PubEvent:
        """Information about a publication of this document"""

        def __init__(self, document, row):
            """Remember the caller's values.

            Pass:
                document - `Document` object for this CDR document
                row - values for this event from the database query
            """

            self.__document = document
            self.__row = row

        def __str__(self):
            """String representation of the event formatted for the report."""

            return f"{self.date}({self.type}-{self.job_id:d})"

        @property
        def date(self):
            """When did this publication occur?"""

            if not hasattr(self, "_date"):
                self._date = str(self.__row.started)[:10]
            return self._date

        @property
        def doc_version(self):
            """Number of the version of the doc published by this event."""
            return self.__row.doc_version

        @property
        def job_id(self):
            """Primary key into the `pub_proc` table."""
            return self.__row.pub_proc

        @property
        def removed(self):
            """'R' if this was a job to remove the document, else ''."""
            return "R" if self.__row.removed == "Y" else ""

        @property
        def type(self):
            """V (vendor) or C (cancer.gov)."""

            if not hasattr(self, "_type"):
                self._type = "V" if self.__row.output_dir else "C"
            return self._type

        @property
        def span(self):
            """Convert this event to its HTML display object."""

            if not hasattr(self, "_span"):
                SPAN = self.__document.control.HTMLPage.B.SPAN
                self._span = SPAN(f"{self}{self.removed}")
                if self.removed:
                    self._span.set("class", "removed")
            return self._span

    class Version:
        """One for each version created for our document."""

        def __init__(self, document, row):
            """Remember the caller's values.

            Pass:
                document - `Document` object for this CDR document
                row - values for this version from the database query
           """

            self.__document = document
            self.__row = row

        @property
        def num(self):
            """Integer for the number of this version."""
            return self.__row.num

        @property
        def publishable(self):
            """True if this version may be published."""

            if not hasattr(self, "_publishable"):
                self._publishable = self.__row.publishable == "Y"
            return self._publishable

        @property
        def publication_events(self):
            """Wrapper containing info on publication of this version."""

            if not hasattr(self, "_publication_events"):
                self._publication_events = ""
                B = self.__document.control.HTMLPage.B
                pieces = []
                events = self.__document.pub_events_by_version[self.num]
                for event in events:
                    if pieces:
                        pieces.append(B.BR())
                    pieces.append(event.span)
                if pieces:
                    self._publication_events = B.SPAN(*pieces)
            return self._publication_events

        @property
        def row(self):
            """Create the line in the report for this version."""

            Cell = self.__document.control.Reporter.Cell
            return [
                Cell(self.num, center=True),
                self.__row.comment or "",
                Cell(str(self.__row.dt)[:16], classes="nowrap"),
                self.__row.fullname or self.__row.name,
                Cell(self.__row.val_status, center=True),
                Cell(self.__row.publishable, center=True),
                Cell(self.publication_events, classes="nowrap"),
            ]


if __name__ == "__main__":
    "Allow documentation or lint tools to load script without side effects"
    Control().run()
