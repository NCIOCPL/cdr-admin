#!/usr/bin/env python

"""Track media processing statuses.

"We need a Media Tracking report.  This spreadsheet report will keep
track of the development and processing statuses of the Media
documents."
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):

    SUBTITLE = "Board Meeting Recordings Tracking Report"

    def build_tables(self):
        """Assemble the table for the report."""

        freeze_panes = "A5" if len(self.caption) == 2 else "A4"
        opts = dict(
            columns=self.columns,
            caption=self.caption,
            sheet_name="Board Meeting Recordings",
            freeze_panes=freeze_panes,
        )
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Ask for the report's date range.

        William asked that the default start date be hard-coded as
        March 1, 2010.

        Pass:
            page - HTMLPage object where the fields live
        """

        today = self.started.strftime("%Y-%m-%d")
        fieldset = page.fieldset("Select Date Range")
        fieldset.append(page.date_field("start", value="2010-03-01"))
        fieldset.append(page.date_field("end", value=today))
        page.form.append(fieldset)

    @property
    def caption(self):
        """String(s) displayed above the report table."""

        if not hasattr(self, "_caption"):
            self._caption = ["Board Meeting Recordings Tracking Report"]
            range = self.add_date_range_to_caption("", self.start, self.end)
            if range:
                self._caption.append(range.strip())
        return self._caption

    @property
    def columns(self):
        """Column headers for the report table."""

        return (
            self.Reporter.Column("CDRID", width="75px"),
            self.Reporter.Column("Media Title", width="300px"),
            self.Reporter.Column("Encoding", width="75px"),
            self.Reporter.Column("Date Created", width="75px"),
            self.Reporter.Column("Last Version Publishable", width="75px"),
            self.Reporter.Column("Version Date", width="75px"),
            self.Reporter.Column("Comments", width="300px"),
        )

    @cached_property
    def end(self):
        """Optional conclusion of the report's date range."""
        return self.parse_date(self.fields.getvalue("end"))

    @property
    def format(self):
        """Override so we get an Excel workbook."""
        return "excel"

    @property
    def rows(self):
        """Values for the report table."""

        fields = "d.id", "MAX(v.dt) as dt"
        query = self.Query("document d", *fields).group("d.id")
        query.join("doc_version v", "v.id = d.id")
        query.join("query_term c", "c.doc_id = d.id")
        query.where("c.path = '/Media/MediaContent/Categories/Category'")
        query.where("c.value = 'Meeting Recording'")
        query.group("d.id")
        if self.start:
            query.having(query.Condition("MAX(v.dt)", self.start, ">="))
        if self.end:
            end = f"{self.end} 23:59:59"
            query.having(query.Condition("MAX(v.dt)", end, "<="))
        rows = query.execute(self.cursor).fetchall()
        docs = [MediaDoc(self, row.id) for row in rows]
        return [doc.row for doc in sorted(docs)]

    @cached_property
    def start(self):
        """Optional beginning of the report's date range."""
        return self.parse_date(self.fields.getvalue("start"))


class MediaDoc:
    """A CDR Media document."""

    ENCODING = "PhysicalMedia/SoundData/SoundEncoding"

    def __init__(self, control, id):
        """Save the caller's values.
           (cursor, docId, docTitle, encoding)
        Pass:
            control - access to the current login session
            id - integer for the unique identifer for the CDR document
        """

        self.__control = control
        self.__id = id

    def __lt__(self, other):
        """Support sorting the media documents by title."""
        return self.sortkey < other.sortkey

    @property
    def comment(self):
        """String for the last comment in the Media document."""

        comments = self.doc.root.findall("Comment")
        return Doc.get_text(comments[-1]) if comments else None

    @property
    def created(self):
        """String for the date the media document was created."""
        return str(self.doc.creation.when)[:10]

    @property
    def doc(self):
        """`Doc` object for the CDR Media document."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.__control, id=self.__id)
        return self._doc

    @property
    def encoding(self):
        """The encoding standard used for the recording (typically MP3)."""

        return Doc.get_text(self.doc.root.find(self.ENCODING))

    @property
    def last_version_publishable(self):
        """String ("Y" or "N") for the Boolean flag."""

        if self.doc.last_version == self.doc.last_publishable_version:
            return "Y"
        return "N"

    @property
    def row(self):
        """Values for the report table."""

        Cell = self.__control.Reporter.Cell
        return (
            Cell(self.__id, center=True),
            self.title,
            Cell(self.encoding, center=True),
            Cell(self.created, center=True),
            Cell(self.last_version_publishable, center=True),
            Cell(self.versioned, center=True),
            self.comment,
        )

    @property
    def sortkey(self):
        """Support sorting the document by case-insensitive title."""

        if not hasattr(self, "_sortkey"):
            self._sortkey = self.title.lower()
        return self._sortkey

    @property
    def title(self):
        """String for the title of the media document."""

        if not hasattr(self, "_title"):
            self._title = Doc.get_text(self.doc.root.find("MediaTitle"))
        return self._title

    @property
    def versioned(self):
        """String for the date the last version was created."""
        return str(self.doc.last_version_date)[:10]


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
