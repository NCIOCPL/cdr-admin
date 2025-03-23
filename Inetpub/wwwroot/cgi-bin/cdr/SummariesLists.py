#!/usr/bin/env python

"""Report on lists of summaries for selected PDQ boards.
"""

from functools import cached_property
from operator import itemgetter
from cdrcgi import Controller, BasicWebPage


class Control(Controller):

    SUBTITLE = "Summaries Lists"
    INCLUDED = (
        ("a", "Summaries and modules", False),
        ("s", "Summaries only", True),
        ("m", "Modules only", False),
        ("p", "SVPC summaries", False),
    )
    ID_DISPLAY = (
        ("N", "Without CDR ID", True),
        ("Y", "With CDR ID", False),
    )
    VERSION_DISPLAY = (
        ("N", "Publishable only", True),
        ("Y", "Publishable and non-publishable", False),
    )

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
        field = page.text_field("extra", **opts)
        field.find("input").set("type", "number")
        fieldset.append(field)
        page.form.append(fieldset)
        fieldset = page.fieldset("Included Documents")
        for value, label, checked in self.INCLUDED:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("included", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Select Summary Set(s)")
        fieldset.set("id", "select-summary-sets-box")
        fieldset.append(page.checkbox("board", value="all", checked=True))
        for id, name in sorted(self.boards.items(), key=itemgetter(1)):
            opts = dict(value=id, label=name, classes="some")
            fieldset.append(page.checkbox("board", **opts))
        page.form.append(fieldset)
        page.head.append(page.B.SCRIPT(src="/js/SummariesLists.js"))

    def show_report(self):
        """Override base class version so we can handle extra columns."""

        if self.extra:
            report = BasicWebPage()
            report.wrapper.append(report.B.H1(self.SUBTITLE))
            for table in self.build_tables():
                report.wrapper.append(table.node)
            report.wrapper.append(self.footer)
            css = "table { margin-bottom: 3rem; width: 100%; }"
            report.page.head.append(report.B.STYLE(css))
            report.send()
        self.report.send()

    @cached_property
    def audience(self):
        """Patient or Health Professional."""

        default = self.AUDIENCES[0]
        audience = self.fields.getvalue("audience", default)
        if audience not in self.AUDIENCES:
            self.bail()
        return audience

    @cached_property
    def board(self):
        """Board(s) selected for the report."""

        # OCECDR-5199: add support for SVPC summaries, which have no board.
        if self.included == "p":
            return [Board(self)]

        # Not SVPC-only: don't narrow by board if none are selected.
        ids = self.fields.getlist("board")
        if not ids or "all" in ids:
            return [Board(self, id) for id in self.boards]

        # We've been asked to restrict the report to specific boards.
        board = []
        for id in ids:
            if not id.isdigit():
                self.bail()
            id = int(id)
            if id not in self.boards:
                self.bail()
            board.append(Board(self, id))
        return board

    @cached_property
    def boards(self):
        """Boards available on the report form's picklist."""
        return self.get_boards()

    @cached_property
    def columns(self):
        """Column header(s) used by each table."""

        columns = []
        if self.show_id:
            columns.append(self.Reporter.Column("CDR ID"))
        columns.append(self.Reporter.Column("Title"))
        for _ in range(self.extra):
            columns.append(self.Reporter.Column("", width="10rem;"))
        return columns

    @cached_property
    def extra(self):
        """How many extra blank columns should be included?"""

        try:
            return int(self.fields.getvalue("extra", "0"))
        except Exception:
            return 0

    @cached_property
    def included(self):
        """Summaries, modules, both, or SVPC?"""

        included = self.fields.getvalue("included", "s")
        if included not in {i[0] for i in self.INCLUDED}:
            self.bail()
        return included

    @cached_property
    def language(self):
        """English or Spanish."""

        default = self.LANGUAGES[0]
        language = self.fields.getvalue("language", default)
        if language not in self.LANGUAGES:
            self.bail()
        return language

    @cached_property
    def show_all(self):
        """True if we should include summaries which are not publishable."""
        return self.fields.getvalue("show_all") == "Y"

    @cached_property
    def show_id(self):
        """True if a column for the CDR document IDs should be included."""
        return self.fields.getvalue("show_id") == "Y"

    @cached_property
    def subtitle(self):
        """What to display underneath the main banner."""

        if self.request != self.SUBMIT:
            return self.SUBTITLE
        subtitle = f"PDQ {self.language} {self.audience} Summaries"
        if self.show_all:
            subtitle += " (all)"
        today = self.started.strftime("%Y-%m-%d")
        return f"{subtitle} {today}"


class Board:
    """PDQ board selected for the report."""

    TABLES = (
        ("sa", "summary", "summaries"),
        ("ma", "module", "modules"),
        ("p", "summary", "summaries"),
    )

    def __init__(self, control, doc_id=None):
        """Remeber the caller's values.

        Pass:
            control - access to the report options and report-building tools
            doc_id - integer for CDR Organization document ID for the board
                     (will be None if the new SVPC flavor of the report was
                     requested, as those summaries have no board, so I'm told)
        """

        self.__control = control
        self.__doc_id = doc_id

    def __lt__(self, other):
        """Sort by board name."""
        return self.name < other.name

    @cached_property
    def control(self):
        """Access to the report options and report-building tools."""
        return self.__control

    @cached_property
    def docs(self):
        """CDR Summary documents for this board."""

        control = self.control
        query_term = "query_term"
        if not control.show_all:
            query_term += "_pub"
        cols = [
            "t.doc_id",
            "t.value AS title",
            "m.value AS module_only",
        ]
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
        if self.control.included == "p":
            query.join(f"{query_term} s", "s.doc_id = t.doc_id",
                       "s.path = '/Summary/@SVPC'")
            query.where("s.value = 'Yes'")
        else:
            b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
            query.where(query.Condition("b.path", b_path))
            query.where(query.Condition("b.int_val", self.id))
            query.outer(f"{query_term} s", "s.doc_id = t.doc_id",
                        "s.path = '/Summary/@SVPC'")
            query.where("s.value IS NULL")
        query.outer(f"{query_term} m", "m.doc_id = t.doc_id",
                    "m.path = '/Summary/@ModuleOnly'")
        rows = query.execute(control.cursor).fetchall()
        return [Summary(row) for row in rows]

    @cached_property
    def id(self):
        """Integer for CDR Organization document ID for the board."""
        return self.__doc_id

    @cached_property
    def modules(self):
        """Summary documents which can only be used as modules."""
        return [doc for doc in self.docs if doc.module]

    @cached_property
    def name(self):
        """String for the board's brief name."""

        if self.id:
            return f"{self.control.boards[self.id]} Editorial Board"
        return ""

    @cached_property
    def summaries(self):
        """Summary documents which can be published independently."""
        return [doc for doc in self.docs if not doc.module]

    @cached_property
    def tables(self):
        """Create the table(s) showing summaries for this board."""

        Cell = self.control.Reporter.Cell
        Table = self.control.Reporter.Table
        columns = self.control.columns
        tables = []
        for included, singular, plural in self.TABLES:
            if self.control.included in included:
                docs = getattr(self, plural)
                if docs:
                    what = singular if len(docs) == 1 else plural
                    if included == "p":
                        caption = f"{len(docs)} SVPC {what}"
                    else:
                        caption = f"{self.name} ({len(docs)} {what})"
                    rows = []
                    for doc in sorted(docs):
                        row = []
                        if self.control.show_id:
                            row = [Cell(doc.doc_id, classes="center")]
                        title = [doc.title or "** NO TITLE **"]
                        if doc.original_title:
                            title.append(f"({doc.original_title})")
                        row.append(title)
                        while len(row) < len(columns):
                            row.append("")
                        rows.append(row)
                    opts = dict(caption=caption, columns=columns)
                    tables.append(Table(rows, **opts))
        return tables


class Summary:
    """PDQ summary managed by one of the boards selected for the report."""

    def __init__(self, row):
        """Save the values from the database query for this document."""
        self.__row = row

    def __lt__(self, other):
        """Sort by title, case insensitive."""
        return self.key < other.key

    @cached_property
    def doc_id(self):
        """Integer for the unique CDR document ID for this PDQ summary."""
        return self.__row.doc_id

    @cached_property
    def key(self):
        """Sort by normalized title."""
        return self.title.lower()

    @cached_property
    def module(self):
        """True if this document can only be used as an included module."""
        return self.__row.module_only == "Yes"

    @cached_property
    def original_title(self):
        """Title of the English document of which this is a translation."""
        try:
            return self.__row.original_title
        except Exception:
            return None

    @cached_property
    def title(self):
        """String for the title of this PDQ summary."""
        return self.__row.title


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
