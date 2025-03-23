#!/usr/bin/env python

"""Report on newly created documents and their statuses.
"""

import datetime
from cdrcgi import Controller, Reporter
from cdrapi.docs import Doc, Doctype


class Control(Controller):
    """Report logic."""

    SUBTITLE = "New Documents Report"

    def populate_form(self, page):
        """Ask for a document type and a date range.

        Pass:
            page - HTMLPage object to which we attach the fields
        """

        fieldset = page.fieldset("Select Document Type")
        fieldset.append(page.radio_button("type", value="any", checked=True))
        for name in self.typenames:
            fieldset.append(page.radio_button("type", value=name, label=name))
        page.form.append(fieldset)
        fieldset = page.fieldset("Date Range")
        end = datetime.date.today()
        start = end - datetime.timedelta(30)
        fieldset.append(page.date_field("start", value=start))
        fieldset.append(page.date_field("end", value=end))
        page.form.append(fieldset)

    def build_tables(self):
        """Create a table for each selected document type."""
        return [doctype.table for doctype in self.doctypes]

    @property
    def doctypes(self):
        """Sorted sequence of `DoctypeCounts` objects with report counts."""

        if not hasattr(self, "_doctypes"):
            names = self.typenames if self.type == "any" else [self.type]
            self._doctypes = []
            for name in names:
                doctype = DoctypeCounts(self, name)
                if doctype.table:
                    self._doctypes.append(doctype)
        return self._doctypes

    @property
    def end(self):
        """String for the end of the report's date range (optional)."""
        return self.parse_date(self.fields.getvalue("end"))

    @property
    def start(self):
        """String for the start of the report's date range (optional)."""
        return self.parse_date(self.fields.getvalue("start"))

    @property
    def subtitle(self):
        """Customize the string below the main banner."""

        if not hasattr(self, "_subtitle"):
            if self.request == "Submit":
                if self.type == "any":
                    self._subtitle = "New Documents"
                else:
                    self._subtitle = f"New {self.type} Documents"
                start, end = self.start, self.end
                if start:
                    if end:
                        self._subtitle += f" Created Between {start} and {end}"
                    else:
                        self._subtitle += f" Created Since {start}"
                elif self.end:
                    self._subtitle += f" Created Through {end}"
            else:
                self._subtitle = self.SUBTITLE
        return self._subtitle

    @property
    def type(self):
        """Selected document type for the report (or "any")."""
        return self.fields.getvalue("type")

    @property
    def typenames(self):
        """Document type names for the form's picklist."""

        if not hasattr(self, "_typenames"):
            self._typenames = []
            for name in Doctype.list_doc_types(self.session):
                if name:
                    self._typenames.append(name)
        return self._typenames


class DoctypeCounts:
    """Counts by status of new documents of a specific type."""

    COLUMNS = (
        Reporter.Column("Status", width="250px"),
        Reporter.Column("Count", width="75px"),
    )

    def __init__(self, control, name):
        """Save the caller's values.

        Pass:
            control - access to the database
            name - string for this document type's name
        """

        self.__control = control
        self.__name = name

    @property
    def control(self):
        """Access to the database."""
        return self.__control

    @property
    def counts(self):
        """Dictionary of counts per status (None if we have no docs)."""

        if not hasattr(self, "_counts"):
            self._counts = {}
            for doc in self.docs:
                self._counts[doc.status] = self._counts.get(doc.status, 0) + 1
        return self._counts

    @property
    def docs(self):
        """Documents of this type created during the report's date range."""

        if not hasattr(self, "_docs"):
            query = self.control.Query("document d", "d.id")
            query.join("doc_created c", "c.doc_id = d.id")
            query.where(query.Condition("d.doc_type", self.id))
            start, end = self.control.start, self.control.end
            if start:
                query.where(query.Condition("c.created", start, ">="))
            if end:
                end = f"{end} 23:59:59"
                query.where(query.Condition("c.created", end, "<="))
            rows = query.execute(self.control.cursor).fetchall()
            self._docs = [NewDocument(self.control, row.id) for row in rows]
        return self._docs

    @property
    def id(self):
        """Integer unique ID for the document type."""

        if not hasattr(self, "_id"):
            self._id = Doctype(self.control.session, name=self.name).id
        return self._id

    @property
    def name(self):
        """String for this document type's name."""
        return self.__name

    @property
    def rows(self):
        """Sequence of table rows (empty if we have no matching docs)."""

        if not hasattr(self, "_rows"):
            self._rows = []
            if self.counts:
                for name in NewDocument.STATUSES:
                    cell = Reporter.Cell(self.counts.get(name, 0), right=True)
                    self._rows.append((name, cell))
        return self._rows

    @property
    def table(self):
        """Status counts table (or None if we have no matching documents)."""

        if not hasattr(self, "_table"):
            self._table = None
            if self.rows:
                opts = dict(caption=self.name, columns=self.COLUMNS)
                self._table = Reporter.Table(self.rows, **opts)
        return self._table


class NewDocument:

    PUBLISHED = "Published"
    READY_FOR_PUBLICATION = "Ready for Publication"
    READY_FOR_REVIEW = "Ready for Review"
    VALID = "Valid"
    UNVALIDATED = "Unvalidated"
    INVALID = "Invalid"
    MALFORMED = "Malformed"
    STATUSES = (
        PUBLISHED,
        READY_FOR_PUBLICATION,
        READY_FOR_REVIEW,
        VALID,
        UNVALIDATED,
        INVALID,
        MALFORMED,
    )
    VAL_STATUSES = {
        Doc.VALID: VALID,
        Doc.UNVALIDATED: UNVALIDATED,
        Doc.INVALID: INVALID,
        Doc.MALFORMED: MALFORMED,
    }

    def __init__(self, control, id):
        """Remember the caller's values.

        Pass:
            control - access to the database and the current session
            id - integer for the unique CDR ID for this document
        """

        self.__control = control
        self.__id = id

    @property
    def control(self):
        """Access to the database and the current CDR login session."""
        return self.__control

    @property
    def doc(self):
        """The `Doc` object, which provides access to status information."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.control.session, id=self.id)
        return self._doc

    @property
    def id(self):
        """Unique ID for this CDR document."""
        return self.__id

    @property
    def status(self):
        """String for the status of this document (that's why we're here)."""

        if not hasattr(self, "_status"):
            doc = self.doc
            active = Doc.ACTIVE
            query = self.control.Query("pub_proc_cg", "id")
            query.where(query.Condition("id", self.id))
            if query.execute(self.control.cursor).fetchall():
                self._status = self.PUBLISHED
            elif doc.last_publishable_version and doc.active_status == active:
                self._status = self.READY_FOR_PUBLICATION
            elif doc.ready_for_review:
                self._status = self.READY_FOR_REVIEW
            else:
                default = self.UNVALIDATED
                self._status = self.VAL_STATUSES.get(doc.val_status, default)
        return self._status


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
