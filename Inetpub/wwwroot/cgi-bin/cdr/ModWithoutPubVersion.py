#!/usr/bin/env python

"""Report on unpublishable changes to documents.

Reports on documents which have been changed since a previously
publishable version without a new publishable version have been
created.
"""

from cdrapi.docs import Doctype
from cdrcgi import Controller
from cdr import FILTERS
import datetime


class Control(Controller):

    SUBTITLE = "Documents Modified Since Last Publishable Version"
    COLUMNS = (
        "Doc ID",
        "Latest Publishable Version Date",
        "Modified By",
        "Modified Date",
        "Latest Non-publishable Version Date",
    )

    def populate_form(self, page):
        """Add the fields to the form.

        Pass:
            page - HTMLPage object where the fields live
        """

        end = datetime.date.today()
        start = end - datetime.timedelta(7)
        fieldset = page.fieldset("Report Options")
        fieldset.append(page.select("user", options=["all"]+self.users))
        fieldset.append(page.select("doctype", options=["all"]+self.doctypes))
        fieldset.append(page.date_field("start", value=start))
        fieldset.append(page.date_field("end", value=end))
        page.form.append(fieldset)

    def build_tables(self):
        """Assemble one table for each doctype with documents to show."""

        fields = (
            "m.id",
            "m.doctype",
            "u.name AS user_name",
            "u.fullname",
            "m.dt AS last_modification_date",
            "p.dt AS last_publishable_version_date",
            "n.dt AS last_unpublishable_version_date",
        )
        self.__make_last_mod_table()
        self.__make_last_pub_table()
        self.__make_last_unp_table()
        query = self.Query(f"{self.last_mod} m", *fields)
        query.order("m.doctype", "m.dt", "m.usr")
        query.join("usr u", "u.name = m.usr")
        query.join("#last_pub p", "p.id = m.id")
        query.outer("#last_unp n", "n.id = m.id")
        query.where("p.dt < m.dt")
        doctype = None
        tables = []
        rows = []
        opts = dict(columns=self.COLUMNS)
        for row in query.execute(self.cursor).fetchall():
            doc = Document(self, row)
            if doc.doctype != doctype:
                if doctype and rows:
                    opts["caption"] = doctype
                    tables.append(self.Reporter.Table(rows, **opts))
                doctype = doc.doctype
                rows = []
            rows.append(doc.row)
        if doctype and rows:
            opts["caption"] = doctype
            tables.append(self.Reporter.Table(rows, **opts))
        return tables

    def __make_last_mod_table(self):
        """Create a temp table for the doc to be included on the report."""

        fields = "d.id", "a.dt", "t.name AS doctype", "u.name AS usr"
        query = self.Query("all_docs d", *fields).into(self.last_mod)
        query.join("doc_type t", "t.id = d.doc_type")
        query.join("doc_last_save s", "s.doc_id = d.id")
        query.join("audit_trail a", "a.document = d.id",
                   "a.dt = s.last_save_date")
        query.join("usr u", "u.id = a.usr")
        if self.user:
            query.where(query.Condition("u.name", self.user))
        if self.doctype:
            query.where(query.Condition("t.name", self.doctype))
        if self.start:
            query.where(query.Condition("s.last_save_date", self.start, ">="))
        if self.end:
            end = f"{self.end} 23:59:59"
            query.where(query.Condition("s.last_save_date", end, "<="))
        query.execute(self.cursor)
        self.conn.commit()

    def __make_last_pub_table(self):
        """Create a temp table showing the last publishable versions."""

        fields = "v.id", "MAX(v.dt) as dt"
        query = self.Query("all_doc_versions v", *fields).into("#last_pub")
        query.join(f"{self.last_mod} m", "m.id = v.id")
        query.where("v.publishable = 'Y'")
        query.group("v.id")
        query.execute(self.cursor)
        self.conn.commit()

    def __make_last_unp_table(self):
        """Create a temp table showing the last unpublishable versions."""

        fields = "v.id", "MAX(v.dt) as dt"
        query = self.Query("all_doc_versions v", *fields).into("#last_unp")
        query.join(f"{self.last_mod} m", "m.id = v.id")
        query.where("v.publishable = 'N'")
        query.group("v.id")
        query.execute(self.cursor)
        self.conn.commit()

    @property
    def doctype(self):
        """Document type selected from the form for the report."""

        if not hasattr(self, "_doctype"):
            self._doctype = self.fields.getvalue("doctype")
            if self._doctype == "all":
                self._doctype = None
        return self._doctype

    @property
    def doctypes(self):
        return sorted(Doctype.list_doc_types(self.session))

    @property
    def end(self):
        """End of report date range selected from the form."""
        return self.fields.getvalue("end")

    @property
    def last_mod(self):
        """Create unique temp table name to work around SQL Server bug.

        Sometimes SQL Server can find its local temporary tables and
        sometimes it can't. This is one of those cases where it can't.
        So we create a global temporary table, and add a timestamp to
        it to minimize the likelihood that two requests will step on
        each other.
        """

        if not hasattr(self, "_last_mod"):
            stamp = f"{self.started.second}_{self.started.microsecond}"
            self._last_mod = f"##last_mod_{stamp}"
            self.logger.info("using global temp table %s", self._last_mod)
        return self._last_mod

    @property
    def start(self):
        """Start of report date range selected from the form."""
        return self.fields.getvalue("start")

    @property
    def subtitle(self):
        """Customize the string displayed below the main banner."""

        if self.request != self.SUBMIT:
            return self.SUBTITLE

        if self.doctype:
            segments = [f"{self.doctype} Documents"]
        else:
            segments = ["Documents"]
        if self.user or self.start or self.end:
            segments.append("Modified")
        if self.user:
            segments.append(f"By {self.user}")
        if self.start and self.end:
            segments.append(f"Between {self.start} And {self.end}")
        elif self.start:
            segments.append(f" On Or After {self.start}")
        elif self.end:
            segments.append(f" On Or Before {self.end}")
        subtitle = " ".join(segments)
        if subtitle == "Documents":
            subtitle = "All Documents"
        return subtitle

    @property
    def user(self):
        """User selected for the report."""

        if not hasattr(self, "_user"):
            self._user = self.fields.getvalue("user")
            if self._user == "all":
                self._user = None
        return self._user

    @property
    def users(self):
        """List of users (for the picklist)."""

        query = self.Query("usr", "name").order("name")
        return [row.name for row in query.execute(self.cursor)]


class Document:
    """Modified document to appear on the report."""

    QCTYPES = set([name.lower().split(":")[0] for name in FILTERS])

    def __init__(self, control, row):
        """Save the caller's values.

        Pass:
            control - access to the current session and to reporting tools
            row - results from the database query
        """

        self.__control = control
        self.__row = row

    @property
    def cdr_id(self):
        """Canonical string format for the document ID."""
        return f"CDR{self.id:010d}"

    @property
    def doctype(self):
        """String for CDR type of the document."""
        return self.__row.doctype

    @property
    def id(self):
        """Integer for the document's unique ID."""
        return self.__row.id

    @property
    def doc_id(self):
        """Link to the document (or just the id if no link can be made."""

        if self.doctype.lower() in self.QCTYPES:
            url = self.__control.make_url("QcReport.py", DocId=self.id)
            opts = dict(href=url, target="_blank")
            return self.__control.Reporter.Cell(self.cdr_id, **opts)
        return self.cdr_id

    @property
    def mod(self):
        """Date/time the document was modified."""
        return self.__row.last_modification_date

    @property
    def pub(self):
        """Date of the last publishable version."""
        return self.__row.last_publishable_version_date

    @property
    def row(self):
        """Values for the report table."""
        return self.doc_id, self.pub, self.user, self.mod, self.unpub

    @property
    def unpub(self):
        """Date of the last unpublishable version."""
        return self.__row.last_unpublishable_version_date

    @property
    def user(self):
        """User who last saved the document."""
        return self.__row.fullname or self.__row.name


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
