#!/usr/bin/env python

"""Report to list the Comprehensive Review Dates for PDQ summaries.
"""

from functools import cached_property
from datetime import date
from cdrcgi import Controller, Reporter


class Control(Controller):
    """One master class to rule them all."""

    SUBTITLE = "Summaries Comprehensive Review Dates"
    RADIO_BUTTONS = (
        (
            "audience", "Select Summary Audience",
            (
                (Controller.AUDIENCES[0], Controller.AUDIENCES[0]),
                (Controller.AUDIENCES[1], Controller.AUDIENCES[1]),
            ),
        ),
        (
            "show_all", "Display Review Dates",
            (
                ("N", "Show only last actual review date"),
                ("Y", "Show all review dates"),
            ),
        ),
        (
            "show_id", "ID Display",
            (
                ("N", "Without CDR ID"),
                ("Y", "With CDR ID"),
            ),
        ),
        (
            "show_unpub", "Version Display",
            (
                ("N", "Publishable only"),
                ("Y", "Publishable and non-publishable"),
            ),
        ),
        (
            "lang", "Summary Language",
            (
                (Controller.LANGUAGES[0], Controller.LANGUAGES[0]),
                (Controller.LANGUAGES[1], Controller.LANGUAGES[1]),
            ),
        ),
    )
    INCLUDE = (
        ("a", "Summaries and modules", False),
        ("s", "Summaries only", True),
        ("m", "Modules only", False),
    )

    def build_tables(self):
        """Assemble the tables to be rendered for the report."""

        if not self.board:
            message = "At least one PDQ board must be selected."
            self.alerts.append(dict(message=message, type="error"))
            self.show_form()
        tables = []
        for board in sorted(self.board):
            if self.include in "sa":
                if board.summaries:
                    tables.append(board.to_table(self.columns))
            if self.include in "ma":
                if board.modules:
                    tables.append(board.to_table(self.columns, True))
        return tables

    def populate_form(self, page):
        """Add the fields to the form page.

        Pass:
            page - object on which the form lives
        """

        for name, label, values in self.RADIO_BUTTONS:
            fieldset = page.fieldset(label)
            checked = True
            for value, label in values:
                opts = dict(checked=checked, value=value, label=label)
                fieldset.append(page.radio_button(name, **opts))
                checked = False
            page.form.append(fieldset)
        fieldset = page.fieldset("Select Summary Set(s)")
        fieldset.append(page.checkbox("board", value="all", checked=True))
        opts = dict(classes="some")
        for id in sorted(self.boards, key=lambda k: self.boards[k]):
            name = self.boards[id].replace("Editorial Board", "").strip()
            opts["label"] = self.boards[id]
            opts["value"] = id
            fieldset.append(page.checkbox("board", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Included Documents")
        for value, label, checked in self.INCLUDE:
            opts = dict(checked=checked, value=value, label=label)
            fieldset.append(page.radio_button("include", **opts))
        page.form.append(fieldset)
        page.add_output_options("html")
        page.head.append(page.B.SCRIPT(src="/js/SummaryCRD.js"))

    @cached_property
    def audience(self):
        """User-selected audience for choosing summaries."""

        audience = self.fields.getvalue("audience")
        if audience and audience not in self.AUDIENCES:
            self.bail()
        return audience

    @cached_property
    def board(self):
        """Board(s) selected by the user for the report."""

        ids = []
        for value in self.fields.getlist("board"):
            if value == "all":
                ids = list(self.boards)
                break
            elif not value.isdigit():
                self.bail()
            else:
                id = int(value)
                if id not in self.boards:
                    self.bail()
                ids.append(id)
        return [Board(self, id) for id in ids]

    @cached_property
    def boards(self):
        """Dictionary of editorial board names indexed by Org ID."""
        return self.get_boards()

    @cached_property
    def columns(self):
        """Column headers for the report."""

        columns = []
        if self.show_id:
            columns.append(self.Reporter.Column("CDR ID", width="50px"))
        columns.extend([
            self.Reporter.Column("Summary Title", width="400px"),
            self.Reporter.Column("Date", width="75px"),
            self.Reporter.Column("Status", width="75px"),
            self.Reporter.Column("Comment", width="400px")
        ])
        return columns

    @cached_property
    def include(self):
        """Should we include summaries (s), modules (m), or both (a)?"""

        include = self.fields.getvalue("include", "s")
        if include not in [values[0] for values in self.INCLUDE]:
            self.bail()
        return include

    @cached_property
    def language(self):
        """User-selected language for choosing summaries."""

        language = self.fields.getvalue("lang")
        if language and language not in self.LANGUAGES:
            self.bail()
        return language

    @cached_property
    def report_css(self):
        """Tweak the size of the table captions."""
        return ".usa-table caption { font-size: 1.2em; }"

    @cached_property
    def show_all(self):
        """Show all dates (instead of just the last one)?"""
        return self.fields.getvalue("show_all") == "Y"

    @cached_property
    def show_id(self):
        """True if the report should include a column for the CDR IDs."""
        return self.fields.getvalue("show_id") == "Y"

    @cached_property
    def show_unpub(self):
        """True if the report should include unpublished summaries."""
        return self.fields.getvalue("show_unpub") == "Y"

    @cached_property
    def subtitle(self):
        """What we show under the main banner."""

        if self.request != self.SUBMIT:
            return self.SUBTITLE
        return f"{self.language} {self.audience} Summaries {date.today()}"

    @cached_property
    def title(self):
        """What we show for the main banner."""

        if self.request != self.SUBMIT:
            return self.TITLE
        return "PDQ Summary Comprehensive Review Report"


class Board:
    """Metadata about a single PDQ board and its summaries for this report."""

    def __init__(self, control, doc_id):
        """Remember the caller's values.

        Pass:
            control - access to the fields and the database
            doc_id - CDR ID for the board's Organization document
        """

        self.control = control
        self.doc_id = int(doc_id)

    @cached_property
    def audience(self):
        """For which audience should we select summaries for the report?"""
        return self.control.audience or self.control.AUDIENCES[0]

    @cached_property
    def docs(self):
        """Summary and module documents."""

        suffix = "" if self.control.show_unpub else "_pub"
        query_term = f"query_term{suffix}"
        fields = "t.doc_id", "t.value", "m.value"
        b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        query = self.control.Query("query_term t", *fields)
        query.join(f"{query_term} a", "a.doc_id = t.doc_id")
        query.join(f"{query_term} l", "l.doc_id = t.doc_id")
        if not self.control.show_unpub:
            query.join("active_doc d", "d.id = t.doc_id")
        query.where("t.path = '/Summary/SummaryTitle'")
        query.where("a.path = '/Summary/SummaryMetaData/SummaryAudience'")
        query.where("l.path = '/Summary/SummaryMetaData/SummaryLanguage'")
        query.where(query.Condition("a.value", self.audience + "s"))
        query.where(query.Condition("l.value", self.language))
        if self.language == "English":
            query.join(f"{query_term} b", "b.doc_id = t.doc_id")
        else:
            query.join(f"{query_term} e", "e.doc_id = t.doc_id")
            query.join("query_term b", "b.doc_id = e.int_val")
            query.where("e.path = '/Summary/TranslationOf/@cdr:ref'")
        query.where(query.Condition("b.path", b_path))
        query.where(query.Condition("b.int_val", self.doc_id))
        if self.control.include == "m":
            query.join(f"{query_term} m", "m.doc_id = t.doc_id",
                       "m.path = '/Summary/@ModuleOnly'",
                       "m.value = 'Yes'")
        else:
            query.outer(f"{query_term} m", "m.doc_id = t.doc_id",
                        "m.path = '/Summary/@ModuleOnly'")
            if self.control.include == "s":
                query.where("(m.value IS NULL OR m.value <> 'Yes')")
        rows = query.unique().execute(self.control.cursor).fetchall()
        return [Summary(self.control, *row) for row in rows]

    @cached_property
    def language(self):
        """For which language should we select summaries for the report?"""
        return self.control.language or self.control.LANGUAGES[0]

    @cached_property
    def modules(self):
        """PDQ Summary documents which are modules."""
        return [d for d in self.docs if d.module]

    @cached_property
    def name(self):
        """String for the board's short name."""
        return self.control.boards[self.doc_id]

    @cached_property
    def summaries(self):
        """PDQ Summary documents which are not modules."""
        return [d for d in self.docs if not d.module]

    def to_table(self, columns, modules=False):
        """
        Create a table showing the board's metadata and comprenehsive reviews.

        Pass:
            columns - column headers for the table
            modules - True if we're showing modules

        Return:
            `Reporter.Table` object
        """

        if modules:
            docs = self.modules
            what = "modules"
        else:
            docs = self.summaries
            what = "summaries"
        opts = dict(
            caption="%s Editorial Board (%s)" % (self.name, what),
            sheet_name=self.name,
            columns=columns,
        )
        if "Complementary" in self.name:
            opts["sheet_name"] = "IACT"  # Name is too big.
        elif "Supportive" in self.name:
            opts["sheet_name"] = "Supportive Care"  # Same problem.
        if modules:
            opts["sheet_name"] += " (m)"
        rows = []
        for doc in sorted(docs):
            reviews = []
            have_actual = False
            i = len(doc.reviews)
            while i > 0:
                i -= 1
                review = doc.reviews[i]
                if self.control.show_all:
                    reviews.insert(0, review)
                elif not have_actual and review.state == "Actual":
                    reviews.insert(0, review)
                    have_actual = True
            row = []
            if self.control.show_id:
                row.append(Reporter.Cell(doc.doc_id))
            row.append(Reporter.Cell(doc.title))
            if reviews:
                review = reviews[0]
                row.extend([
                    Reporter.Cell(review.date, classes="text-no-wrap"),
                    Reporter.Cell(review.state, classes="center"),
                    review.comment or ""
                ])
            else:
                row.extend(["", "", ""])
            rows.append(row)
            for review in reviews[1:]:
                row = []
                if self.control.show_id:
                    row.append(Reporter.Cell(doc.doc_id))
                row.append(Reporter.Cell(doc.title))
                row.extend([
                    Reporter.Cell(review.date, classes="text-no-wrap"),
                    Reporter.Cell(review.state, classes="center"),
                    review.comment or ""
                ])
                rows.append(row)
        return Reporter.Table(rows, **opts)

    def __lt__(self, other):
        "Support sorting by board name"
        return self.name < other.name


class Summary:
    """Metadata and comprehensive reviews for a single PDQ summary."""

    NO_TITLE = "[NO TITLE]"

    def __init__(self, control, doc_id, title, module):
        self.control = control
        self.doc_id = doc_id
        self.title = title.strip() or "[NO TITLE]"
        self.module = module == "Yes"
        self.reviews = []
        d_path = "/Summary/ComprehensiveReview/ComprehensiveReviewDate"
        t_path = d_path + "/@DateType"
        query = control.Query("query_term d", "d.value", "t.value", "c.value")
        query.join("query_term t", "t.doc_id = d.doc_id",
                   "LEFT(t.node_loc, 4) = LEFT(d.node_loc, 4)")
        query.outer("query_term c", "c.doc_id = d.doc_id",
                    "LEFT(c.node_loc, 4) = LEFT(d.node_loc, 4)",
                    "c.path = '/Summary/ComprehensiveReview/Comment'")
        query.where(query.Condition("d.doc_id", doc_id))
        query.where(query.Condition("d.path", d_path))
        query.where(query.Condition("t.path", t_path))
        rows = query.execute(control.cursor).fetchall()
        self.reviews = sorted([Review(*row) for row in rows])

    def __lt__(self, other):
        return self.sort_key < other.sort_key

    @cached_property
    def sort_key(self):
        """Force summaries without a title to the top."""
        return "" if self.title == self.NO_TITLE else self.title.upper()


class Review:
    "Information about a single proposed or actual comprehensive review"
    def __init__(self, date, state, comment):
        self.date = date
        self.state = state
        self.comment = comment

    def __lt__(self, other):
        "Support sorting reviews in chronological order"
        return (self.date, self.state) < (other.date, other.state)


if __name__ == "__main__":
    "Allow import (by doc or lint tools, for example) without side effects"
    Control().run()
