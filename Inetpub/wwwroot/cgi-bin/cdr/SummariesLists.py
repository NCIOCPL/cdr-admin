#!/usr/bin/env python

"""Report on lists of summaries for selected PDQ boards.
"""

from operator import itemgetter
from cdrcgi import Controller


class Control(Controller):

    SUBTITLE = "Summaries Lists"
    INCLUDED = (
        ("a", "Summaries and modules", False),
        ("s", "Summaries only", True),
        ("m", "Modules only", False),
    )
    ID_DISPLAY = (
        ("N", "Without CDR ID", True),
        ("Y", "With CDR ID", False),
    )
    VERSION_DISPLAY = (
        ("N", "Publishable only", True),
        ("Y", "Publishable and non-publishable", False),
    )
    SCRIPT = """\
function check_board(val) {
  if (val == "all")
    jQuery(".some").prop("checked", false);
  else
    jQuery("#board-all").prop("checked", false);
}"""

    def build_tables(self):
        """Assemble the tables from each of the boards."""

        tables = []
        for board in sorted(self.board):
            tables += board.tables
        return tables

    def populate_form(self, page):
        """Put the fields for the report options on the form.

        Pass:
            page - HTMLPage object on which to place the field sets
        """

        self.add_audience_fieldset(page)
        self.add_language_fieldset(page)
        fieldset = page.fieldset("ID Display")
        for value, label, checked in self.ID_DISPLAY:
            opts = dict(label=label, value=value, checked=checked)
            fieldset.append(page.radio_button("show_id", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Version Display")
        for value, label, checked in self.VERSION_DISPLAY:
            opts = dict(label=label, value=value, checked=checked)
            fieldset.append(page.radio_button("show_all", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Extra Blank Columns", id="extra-block")
        opts = dict(label="Extra Cols", value="0")
        fieldset.append(page.text_field("extra", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Select Summary Set(s)")
        fieldset.append(page.checkbox("board", value="all", checked=True))
        for id, name in sorted(self.boards.items(), key=itemgetter(1)):
            opts = dict(value=id, label=name, classes="some")
            fieldset.append(page.checkbox("board", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Included Documents")
        for value, label, checked in self.INCLUDED:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("included", **opts))
        page.form.append(fieldset)
        page.add_script(self.SCRIPT)

    def show_report(self):
        """Override base class version so we can set the table widhts."""

        self.report.page.add_css(".report table { width: 1024px; }")
        self.report.send()

    @property
    def audience(self):
        """Patient or Health Professional."""

        if not hasattr(self, "_audience"):
            default = self.AUDIENCES[0]
            self._audience = self.fields.getvalue("audience", default)
            if self._audience not in self.AUDIENCES:
                self.bail()
        return self._audience

    @property
    def board(self):
        """Board(s) selected for the report."""

        if not hasattr(self, "_board"):
            ids = self.fields.getlist("board")
            if not ids or "all" in ids:
                self._board = [Board(self, id) for id in self.boards]
            else:
                self._board = []
                for id in ids:
                    if not id.isdigit():
                        self.bail()
                    id = int(id)
                    if id not in self.boards:
                        self.bail()
                    self._board.append(Board(self, id))
        return self._board

    @property
    def boards(self):
        """Boards available the report form's piclist."""

        if not hasattr(self, "_boards"):
            self._boards = self.get_boards()
        return self._boards

    @property
    def columns(self):
        """Column header(s) used by each table."""

        if not hasattr(self, "_columns"):
            self._columns = []
            if self.show_id:
                self._columns.append(self.Reporter.Column("CDR ID"))
            self._columns.append(self.Reporter.Column("Title"))
            for _ in range(self.extra):
                self._columns.append(self.Reporter.Column("", width="50px"))
        return self._columns

    @property
    def extra(self):
        """How many extra blank columns should be included?"""

        if not hasattr(self, "_extra"):
            try:
                self._extra = int(self.fields.getvalue("extra", "0"))
            except Exception:
                self._extra = 0
        return self._extra

    @property
    def included(self):
        """Summaries, modules, or both?"""

        if not hasattr(self, "_included"):
            self._included = self.fields.getvalue("included", "s")
            if self._included not in {i[0] for i in self.INCLUDED}:
                self.bail()
        return self._included

    @property
    def language(self):
        """English or Spanish."""

        if not hasattr(self, "_language"):
            default = self.LANGUAGES[0]
            self._language = self.fields.getvalue("language", default)
            if self._language not in self.LANGUAGES:
                self.bail()
        return self._language

    @property
    def show_all(self):
        """True if we should include summaries which are not publishable."""
        return self.fields.getvalue("show_all") == "Y"

    @property
    def show_id(self):
        """True if a column for the CDR document IDs should be included."""
        return self.fields.getvalue("show_id") == "Y"

    @property
    def subtitle(self):
        """What to display underneath the main banner."""

        if not hasattr(self, "_subtitle"):
            if self.request == self.SUBMIT:
                subtitle = f"PDQ {self.language} {self.audience} Summaries"
                if self.show_all:
                    subtitle += " (all)"
                today = self.started.strftime("%Y-%m-%d")
                self._subtitle = f"{subtitle} {today}"
            else:
                self._subtitle = self.SUBTITLE
        return self._subtitle


class Board:
    """PDQ board selected for the report."""

    TABLES = (
        ("sa", "summary", "summaries"),
        ("ma", "module", "modules"),
    )

    def __init__(self, control, doc_id):
        """Remeber the caller's values.

        Pass:
            control - access to the report options and report-building tools
            doc_id - integer for CDR Organization document ID for the board
        """

        self.__control = control
        self.__doc_id = doc_id

    def __lt__(self, other):
        """Sort by board name."""
        return self.name < other.name

    @property
    def control(self):
        """Access to the report options and report-building tools."""
        return self.__control

    @property
    def docs(self):
        """CDR Summary documents for this board."""

        if not hasattr(self, "_docs"):
            control = self.control
            query_term = "query_term"
            if not control.show_all:
                query_term += "_pub"
            cols = ["t.doc_id", "t.value AS title", "m.value AS module_only"]
            if control.language != "English":
                cols.append("o.value AS original_title")
            query = control.Query(f"{query_term} t", *cols).unique()
            query.join(f"{query_term} a", "a.doc_id = t.doc_id")
            query.join(f"{query_term} l", "l.doc_id = t.doc_id")
            query.join("active_doc d", "d.id = t.doc_id")
            query.where("t.path = '/Summary/SummaryTitle'")
            query.where("a.path = '/Summary/SummaryMetaData/SummaryAudience'")
            query.where("l.path = '/Summary/SummaryMetaData/SummaryLanguage'")
            query.where(query.Condition("a.value", f"{control.audience}s"))
            query.where(query.Condition("l.value", control.language))
            if control.language == "English":
                query.join(f"{query_term} b", "b.doc_id = t.doc_id")
            else:
                query.join(f"{query_term} e", "e.doc_id = t.doc_id")
                query.join(f"{query_term} b", "b.doc_id = e.int_val")
                query.join(f"{query_term} o", "o.doc_id = e.int_val")
                query.where("e.path = '/Summary/TranslationOf/@cdr:ref'")
                query.where("o.path = '/Summary/SummaryTitle'")
            b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
            query.where(query.Condition("b.path", b_path))
            query.where(query.Condition("b.int_val", self.id))
            query.outer(f"{query_term} m", "m.doc_id = t.doc_id",
                        "m.path = '/Summary/@ModuleOnly'")
            rows = query.execute(control.cursor).fetchall()
            self._docs = [Summary(row) for row in rows]
        return self._docs

    @property
    def id(self):
        """Integer for CDR Organization document ID for the board."""
        return self.__doc_id

    @property
    def modules(self):
        """Summary documents which can only be used as modules."""

        if not hasattr(self, "_modules"):
            self._modules = [doc for doc in self.docs if doc.module]
        return self._modules

    @property
    def name(self):
        """String for the board's brief name."""

        if not hasattr(self, "_name"):
            self._name = f"{self.control.boards[self.id]} Editorial Board"
        return self._name

    @property
    def summaries(self):
        """Summary documents which can be published independently."""

        if not hasattr(self, "_summaries"):
            self._summaries = [doc for doc in self.docs if not doc.module]
        return self._summaries

    @property
    def tables(self):
        """Create the table(s) showing summaries for this board."""

        if not hasattr(self, "_tables"):
            Cell = self.control.Reporter.Cell
            Table = self.control.Reporter.Table
            columns = self.control.columns
            self._tables = []
            for included, singular, plural in self.TABLES:
                if self.control.included in included:
                    docs = getattr(self, plural)
                    if docs:
                        what = singular if len(docs) == 1 else plural
                        caption = f"{self.name} ({len(docs)} {what})"
                        rows = []
                        for doc in sorted(docs):
                            row = []
                            if self.control.show_id:
                                row = [Cell(doc.doc_id, classes="center")]
                            title = [doc.title]
                            if doc.original_title:
                                title.append(f"({doc.original_title})")
                            row.append(title)
                            while len(row) < len(columns):
                                row.append("")
                            rows.append(row)
                        opts = dict(caption=caption, columns=columns)
                        self._tables.append(Table(rows, **opts))
        return self._tables


class Summary:
    """PDQ summary managed by one of the boards selected for the report."""

    def __init__(self, row):
        """Save the values from the database query for this document."""
        self.__row = row

    def __lt__(self, other):
        """Sort by title, case insensitive."""
        return self.key < other.key

    @property
    def doc_id(self):
        """Integer for the unique CDR document ID for this PDQ summary."""
        return self.__row.doc_id

    @property
    def key(self):
        """Sort by normalized title."""

        if not hasattr(self, "_key"):
            self._key = self.title.lower()
        return self._key

    @property
    def module(self):
        """True if this document can only be used as an included module."""
        return self.__row.module_only == "Yes"

    @property
    def original_title(self):
        """Title of the English document of which this is a translation."""
        try:
            return self.__row.original_title
        except Exception:
            return None

    @property
    def title(self):
        """String for the title of this PDQ summary."""
        return self.__row.title


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
