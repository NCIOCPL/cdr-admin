#!/usr/bin/env python

"""Show which glossary name documents have changed recently.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc
import datetime


class Control(Controller):
    """Access to database, session, and report/form building."""

    SUBTITLE = "Glossary Term Name Documents Modified Report"
    NAME_LABELS = {"en": "Term Name", "es": "Translated Term Name" }
    LANGUAGES = (("en", "English"), ("es", "Spanish"))
    STATUS_PATHS = dict(
        en="/GlossaryTermName/TermNameStatus",
        es="/GlossaryTermName/TranslatedName/TranslatedNameStatus",
    )
    AUDIENCE_PATHS = dict(
        en="/GlossaryTermConcept/TermDefinition/Audience",
        es="/GlossaryTermConcept/TranslatedTermDefinition/Audience",
    )
    CONCEPT_PATH = "/GlossaryTermName/GlossaryTermConcept/@cdr:ref"

    def build_tables(self):
        """Assemble the table for the rpoert."""

        opts = dict(columns=self.columns, sheet_name="GlossaryTerm")
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Request the information we need for this report.

        Pass:
            page - HTMLPage object with which the form is built
        """

        end = datetime.date.today()
        start = end - datetime.timedelta(7)
        fieldset = page.fieldset("Date Range")
        fieldset.append(page.date_field("start_date", value=start))
        fieldset.append(page.date_field("end_date", value=end))
        page.form.append(fieldset)
        fieldset = page.fieldset("Language")
        checked=True
        for value, label in self.LANGUAGES:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("language", **opts))
            checked = False
        page.form.append(fieldset)
        fieldset = page.fieldset("Audience")
        for value in self.AUDIENCES:
            opts = dict(value=value, checked=True)
            fieldset.append(page.checkbox("audience", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Term Status(es)")
        for value in self.statuses:
            fieldset.append(page.checkbox("status", value=value, checked=True))
        page.form.append(fieldset)

    @property
    def audience(self):
        """Audience(s) selected for the report."""

        if not hasattr(self, "_audience"):
            self._audience = self.fields.getlist("audience")
            for audience in self._audience:
                if audience not in self.AUDIENCES:
                    self.bail()
        return self._audience

    @property
    def columns(self):
        """Column headers for the report."""

        return (
            self.Reporter.Column("CDR ID", width="70px"),
            self.Reporter.Column(self.name_label, width="350px"),
            self.Reporter.Column("Date Last Modified", width="100px"),
            self.Reporter.Column("Publishable?", width="100px"),
            self.Reporter.Column("Date First Published", width="100px"),
            self.Reporter.Column("Last Comment", width="450px"),
            self.Reporter.Column("Date Last Publishable", width="100px")
        )

    @property
    def docs(self):
        """Term name documents selected for the report."""

        query = self.Query("doc_version v", "v.id", "MAX(v.num) AS num")
        query.join("doc_type t", "t.id = v.doc_type")
        query.join("active_doc d", "d.id = v.id")
        query.where("t.name = 'GlossaryTermName'")
        if self.start:
            query.where(query.Condition("v.dt", self.start, ">="))
        if self.end:
            query.where(query.Condition("v.dt", f"{self.end} 23:59:59", "<="))
        if self.audience:
            query.join("query_term c", "c.doc_id = d.id")
            query.where(f"c.path = '{self.CONCEPT_PATH}'")
            query.join("query_term a", "a.doc_id = c.int_val")
            query.where(f"a.path = '{self.AUDIENCE_PATHS[self.language]}'")
            query.where(query.Condition("a.value", self.audience, "IN"))
            query.unique()
        if self.status:
            query.join("query_term s", "s.doc_id = d.id")
            query.where(f"s.path = '{self.STATUS_PATHS[self.language]}'")
            query.where(query.Condition("s.value", self.status, "IN"))
            query.unique()
        query.group("v.id")
        query.log()
        rows = query.execute(self.cursor).fetchall()
        docs = [GlossaryTermName(self, row) for row in rows]
        return sorted(docs)

    @property
    def end(self):
        """End of the date range for the report."""
        return self.fields.getvalue("end_date")

    @property
    def format(self):
        """Override to get an Excel report."""
        return "excel"

    @property
    def language(self):
        """Language code selected for the report (en or es)."""

        if not hasattr(self, "_language"):
            self._language = self.fields.getvalue("language")
            if self._language not in {"en", "es"}:
                self.bail
        return self._language

    @property
    def name_label(self):
        """Custom column header, depending on the report's language."""
        return self.NAME_LABELS.get(self.language)

    @property
    def rows(self):
        """Values for the report table."""

        rows = []
        for doc in self.docs:
            rows += doc.rows
        return rows

    @property
    def start(self):
        """Beginning of the date range for the report."""
        return self.fields.getvalue("start_date")

    @property
    def status(self):
        """Term status(es) selected by the user for the report."""

        if not hasattr(self, "_status"):
            self._status = []
            for status in self.fields.getlist("status"):
                if status not in self.statuses:
                    self.bail()
                self._status.append(status)
        return self._status

    @property
    def statuses(self):
        """Valid values for term name status checkboxes."""

        if not hasattr(self, "_statuses"):
            paths = tuple(self.STATUS_PATHS.values())
            query = self.Query("query_term", "value").unique()
            query.where(query.Condition("path", paths, "IN"))
            rows = query.execute(self.cursor).fetchall()
            statuses = []
            for row in rows:
                status = (row.value or "").strip()
                if status:
                    statuses.append(status)
            self._statuses = sorted(statuses)
        return self._statuses

class GlossaryTermName:
    """Information needed for a glossary term's report rows."""

    def __init__(self, control, row):
        """Save the caller's values.

        Pass:
            control - access to the session and report-building tools
            row - values from the database query
        """

        self.__control = control
        self.__row = row

    def __lt__(self, other):
        """Make the documents sortable by document title."""
        return self.doc.title < other.doc.title

    @property
    def control(self):
        """Access to the login session and report-building tools."""
        return self.__control

    @property
    def date_first_published(self):
        """Date this document was first published."""

        if not hasattr(self, "_date_first_published"):
            self._date_first_published = ""
            first_pub = self.doc.first_pub
            if first_pub:
                self._date_first_published = str(first_pub)[:10]
        return self._date_first_published

    @property
    def date_last_publishable(self):
        """Date of the most recent publishable version, if any."""

        if not hasattr(self, "_date_last_publishable"):
            self._date_last_publishable = ""
            query = self.control.Query("doc_version", "MAX(dt) AS dt")
            query.where("publishable = 'Y'")
            query.where(query.Condition("id", self.doc.id))
            row = query.execute(self.control.cursor).fetchone()
            if row and row.dt:
                self._date_last_publishable = str(row.dt)[:10]
        return self._date_last_publishable

    @property
    def doc(self):
        """`Doc` object for the glossary term name document."""

        if not hasattr(self, "_doc"):
            opts = dict(id=self.__row.id, version=self.__row.num)
            self._doc = Doc(self.control.session, **opts)
        return self._doc

    @property
    def names(self):
        """Name strings (with comments) pulled from the document."""

        tag = "TermName" if self.control.language == "en" else "TranslatedName"
        names = []
        for node in self.doc.root.findall(tag):
            names.append(self.Name(self, node))
        return names

    @property
    def publishable(self):
        """String 'Y' or 'N' depending on whether the version is publshable."""

        if not hasattr(self, "_publishable"):
            self._publishable = "Y" if self.doc.publishable else "N"
        return self._publishable

    @property
    def rows(self):
        "Create a row for each of the term's name strings"
        return [name.row for name in self.names]


    class Name:
        """A Glossary term can have multiple names, each with a comment."""

        def __init__(self, term, node):
            """Save the caller's values.

            Pass:
                term - object for the CDR document containing the name string
                node - portion of the document for this name string
            """

            self.__term = term
            self.__node = node

        @property
        def comment(self):
            """First comment in the block with this name string."""

            if not hasattr(self, "_comment"):
                self._comment = ""
                node = self.__node.find("Comment")
                if node is not None:
                    self._comment = self.Comment(node)
            return self._comment

        @property
        def date_last_modified(self):
            """Date the name string for this report was last modified."""

            if not hasattr(self, "_date_last_modified"):
                self._date_last_modified = ""
                node = self.__node.find("DateLastModified")
                self._date_last_modified = Doc.get_text(node, "")[:10]
            return self._date_last_modified

        @property
        def row(self):
            """Values for this name string.

            Each name for a term gets its own row in the report, repeating
            the information common to the term in each row for the term.
            """

            Cell = self.__term.control.Reporter.Cell
            return (
                Cell(self.__term.doc.id, center=True),
                self.string,
                Cell(self.date_last_modified, center=True),
                Cell(self.__term.publishable, center=True),
                Cell(self.__term.date_first_published, center=True),
                str(self.comment),
                Cell(self.__term.date_last_publishable, center=True)
            )

        @property
        def string(self):
            """Term name string for this term."""
            return Doc.get_text(self.__node.find("TermNameString"), "")

        class Comment:
            "Subclass holding text and metadata for a definition comment"

            def __init__(self, node):
                """Remember the caller's value.

                Pass:
                    node - element containing the definition comment
                """

                self.__node = node

            def __str__(self):
                """Serialize the comment's values."""

                args = self.date, self.user, self.audience, self.text
                return "[date: {}; user; {}; audience: {}] {}".format(*args)

            @property
            def text(self):
                """String for the comment text."""
                return Doc.get_text(self.__node)

            @property
            def date(self):
                """String for the date the comment was entered."""
                return self.__node.get("date")

            @property
            def audience(self):
                """Is the comment meant for internal or external viewers?"""
                return self.__node.get("audience")

            @property
            def user(self):
                """Account name of the user entering the comment."""
                return self.__node.get("user")


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
