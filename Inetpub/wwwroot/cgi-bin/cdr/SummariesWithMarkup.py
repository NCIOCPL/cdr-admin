#!/usr/bin/env python

"""Report on summaries containing specified markup.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Access to the database and report-creation tools."""

    SUBTITLE = "Summaries With Markup"
    LEVELS = "Publish", "Approved", "Proposed", "Rejected"
    INCLUDE_AB_MARKUP = "Include Advisory Board markup"
    INCLUDE_WITHOUT_MARKUP = "Include summaries without markup"
    CSS = (
        "td { width: 60px; text-align: center; vertical-align: middle; }",
        "td.active { width: 80px; }",
        "td.title { text-align: left; vertical-align: top; width: 550px; }",
    )
    SCRIPT = """\
function check_board(val) {
    if (val == "all") {
        jQuery("input[name='board']").prop("checked", false);
        jQuery("#board-all").prop("checked", true);
    }
    else if (jQuery("input[name='board']:checked").length > 0)
        jQuery("#board-all").prop("checked", false);
    else
        jQuery("#board-all").prop("checked", true);
}
"""

    def build_tables(self):
        """Sequence of one table for each board selected."""

        if not self.level:
            self.bail("no revision levels specified")
        if self.board == ["all"]:
            board_ids = list(self.boards)
        else:
            board_ids = self.board
        boards = [Board(self, board_id) for board_id in board_ids]
        return [board.table for board in sorted(boards) if board.summaries]

    def populate_form(self, page):
        """Add the fields to the form.

        Pass:
            page - HTMLPage object where the fields go
        """

        self.add_board_fieldset(page)
        self.add_audience_fieldset(page)
        self.add_language_fieldset(page)
        fieldset = page.fieldset("Markup Levels To Be Included")
        for value in self.LEVELS:
            fieldset.append(page.checkbox("level", value=value, checked=True))
        page.form.append(fieldset)
        fieldset = page.fieldset("Include Advisory Board Markup?")
        name = "advisory"
        fieldset.append(page.radio_button(name, value="yes", checked=True))
        fieldset.append(page.radio_button(name, value="no"))
        page.form.append(fieldset)
        fieldset = page.fieldset("Include Summaries Without Markup?")
        name = "show-all"
        fieldset.append(page.radio_button(name, value="yes"))
        fieldset.append(page.radio_button(name, value="no", checked=True))
        page.form.append(fieldset)
        page.add_script(self.SCRIPT)

    def show_report(self):
        """Override base class version to add custom styling."""

        self.report.page.add_css("\n".join(self.CSS))
        self.report.send()

    @cached_property
    def advisory(self):
        """True if the report should include advisory board markup."""
        return self.fields.getvalue("advisory") == "yes"

    @cached_property
    def audience(self):
        """Audience selected for the report."""

        default = self.AUDIENCES[0]
        audience = self.fields.getvalue("audience", default)
        if audience not in self.AUDIENCES:
            self.bail()
        return audience

    @cached_property
    def board(self):
        """PDQ board(s) selected by the user for the report."""

        board = self.fields.getlist("board") or ["all"]
        if "all" in board:
            return ["all"]
        boards = []
        for id in board:
            if not id.isdigit():
                self.bail()
            id = int(id)
            if id not in self.boards:
                self.bail()
            boards.append(id)
        return boards

    @cached_property
    def boards(self):
        """Dictionary of PDQ boards for the form."""
        return self.get_boards()

    @cached_property
    def columns(self):
        """Sequence of column definitions for the report table(s)."""

        s = "s" if self.language == "Spanish" else ""
        columns = [
            self.Reporter.Column("Doc ID"),
            self.Reporter.Column(f"Summary Title{s}"),
        ]
        for level in self.LEVELS:
            if level in self.level:
                columns.append(self.Reporter.Column(level))
        if self.advisory:
            columns.append(self.Reporter.Column("Advisory"))
        return columns

    @cached_property
    def language(self):
        """Language selected for the report."""

        default = self.LANGUAGES[0]
        language = self.fields.getvalue("language", default)
        if language not in self.LANGUAGES:
            self.bail()
        return language

    @cached_property
    def level(self):
        """Markup level(s) selected for the report."""

        level = self.fields.getlist("level")
        if set(level) - set(self.LEVELS):
            self.bail()
        return level

    @cached_property
    def show_all(self):
        """True if the report should include summaries without markup."""
        return self.fields.getvalue("show-all") == "yes"

    @cached_property
    def subtitle(self):
        """What we display directly under the main banner."""

        if self.request == self.SUBMIT:
            today = self.started.strftime("%Y-%m-%d")
            args = self.language, self.audience, today
            pattern = "{} {} Summaries With Markup - {}"
            return pattern.format(*args)
        return self.SUBTITLE


class Board:
    """PDQ board selected for the report."""

    def __init__(self, control, doc_id):
        """Remember the caller's values.

        Pass:
            control - access to the database and report-creation tools
            doc_id - integer for the CDR document ID for the board
        """

        self.control = control
        self.id = doc_id

    def __lt__(self, other):
        """Order the PDQ boards by name."""
        return self.name < other.name

    @cached_property
    def name(self):
        """String for the board's short name."""
        return self.control.boards[self.id]

    @cached_property
    def summaries(self):
        """Publishable summaries in scope for this report."""

        b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        t_path = "/Summary/TranslationOf/@cdr:ref"
        audience = f"{self.control.audience}s"
        cols = ["d.id"]
        if self.control.language == "Spanish":
            cols.append("t.int_val")
        query = self.control.Query("active_doc d", *cols).unique()
        query.join("query_term_pub a", "a.doc_id = d.id")
        query.where("a.path = '/Summary/SummaryMetaData/SummaryAudience'")
        query.where(query.Condition("a.value", audience))
        query.join("query_term_pub l", "l.doc_id = d.id")
        query.where("l.path = '/Summary/SummaryMetaData/SummaryLanguage'")
        query.where(query.Condition("l.value", self.control.language))
        if self.control.language == "English":
            query.join("query_term_pub b", "b.doc_id = d.id")
        else:
            query.join("query_term_pub t", "t.doc_id = d.id")
            query.where(query.Condition("t.path", t_path))
            query.join("query_term b", "b.doc_id = t.int_val")
        query.where(query.Condition("b.path", b_path))
        query.where(query.Condition("b.int_val", self.id))
        summaries = []
        for row in query.execute(self.control.cursor).fetchall():
            summary = self.Summary(self.control, row)
            if summary.in_scope:
                summaries.append(summary)
        return summaries

    @cached_property
    def table(self):
        """Assemble the report table for the board."""

        rows = [summary.row for summary in sorted(self.summaries)]
        opts = dict(columns=self.control.columns, caption=self.name)
        return self.control.Reporter.Table(rows, **opts)

    class Summary:
        """Summary managed by the current board."""

        QC_REPORT = "QcReport.py"
        QC_REPORT_TYPES = dict(H="rs", P="pat")

        def __init__(self, control, row):
            """Remember the caller's values.

            Pass:
                control - access to the DB and report-creation tools
                row - values from the database query for this summary
            """

            self.control = control
            self.db_row = row

        def __lt__(self, other):
            """Sort by normalized title and document ID."""
            return self.key < other.key

        @cached_property
        def counts(self):
            """Object for keeping track of markup found in the summary."""
            return self.Counts(self.control)

        @cached_property
        def doc(self):
            """CDR API's `Doc` object for the PDQ summary."""
            return Doc(self.control.session, id=self.id)

        @cached_property
        def id(self):
            """Integer for the CDR document ID for this summary."""
            return self.db_row.id

        @cached_property
        def in_scope(self):
            """True if the summary should be included on the report.

            Do a string scan to optimize away parsing of the document
            in the event that there are no Insertion or Deletion
            elements at all in the summary document. Otherwise,
            extract the counts of each type of markup.
            """

            xml = self.doc.xml
            if "<Insertion" in xml or "<Deletion" in xml:
                for node in self.doc.root.iter("Insertion", "Deletion"):
                    self.counts.increment_level(node.get("RevisionLevel"))
                    if node.get("Source") == "advisory-board":
                        self.counts.advisory += 1
            if self.control.show_all or self.counts.included:
                return True
            elif self.control.advisory and self.counts.advisory:
                return True
            return False

        @cached_property
        def is_module(self):
            """True if this summary can only be used as a module."""

            query = self.control.Query("query_term", "value")
            query.where("path = '/Summary/@ModuleOnly'")
            query.where(query.Condition("doc_id", self.id))
            rows = query.execute(self.control.cursor).fetchall()
            return rows[0][0] == "Yes" if rows else False

        @cached_property
        def key(self):
            """Sort by normalized title and document ID."""
            return self.title.lower(), self.id

        @cached_property
        def original_title(self):
            """Title of the summary of which this is a translation."""

            if len(self.db_row) < 2:
                return None
            return self.__summary_title(self.db_row[1])

        @cached_property
        def row(self):
            """Assemble the summary's table row for the report."""

            Cell = self.control.Reporter.Cell
            title = self.title
            if self.original_title is not None:
                title = title, f"({self.original_title})"
            row = [
                Cell(self.id, href=self.url, target="_blank"),
                Cell(title, classes="title"),
            ]
            for level in self.control.LEVELS:
                if level in self.control.level:
                    value = getattr(self.counts, level.lower()) or ""
                    row.append(Cell(value, classes="active"))
            if self.control.advisory:
                row.append(Cell(self.counts.advisory or ""))
            return row

        @cached_property
        def title(self):
            """Official title of the PDQ summary."""

            title = self.__summary_title(self.id)
            if self.is_module:
                title += " (Module)"
            return title

        @cached_property
        def url(self):
            """Address of the QC report for this PDQ summary."""

            parms = dict(
                DocId=self.doc.cdr_id,
                DocType="Summary",
                DocVersion="-1",
                ReportType=self.QC_REPORT_TYPES[self.control.audience[0]],
            )
            return self.control.make_url(self.QC_REPORT, **parms)

        def __summary_title(self, id):
            """Find the official title of a PDQ summary document.

            Pass:
                id - integer for the PDQ summary's CDR document ID

            Return:
                string for the summary document's title
            """

            query = self.control.Query("query_term", "value")
            query.where("path = '/Summary/SummaryTitle'")
            query.where(query.Condition("doc_id", id))
            rows = query.execute(self.control.cursor).fetchall()
            return rows[0].value if rows else "Title not found"

        class Counts:
            """
            Intelligent counting of occurrences of different types of
            markup.

            Properties:
                control   - processing control object
                advisory  - number of elements with Source == "advisory-board"
                included  - True if we have counts for levels which are
                            in scope

                Also, one attribute for each of the possible values of
                the RevisionLevel attribute
            """

            LEVELS = {level.lower() for level in Control.LEVELS}

            def __init__(self, control):
                """Save the control object and initialize the properties.

                Pass:
                    control - access to the report's options
                """

                self.control = control
                self.advisory = 0
                self.included = False
                for level in self.LEVELS:
                    setattr(self, level, 0)

            def increment_level(self, level):
                """
                Bump up the count for one of the revision level attributes.
                Also keep track of how many elements we have seen with
                any of the values the user has asked us to display.
                """
                if level in self.LEVELS:
                    setattr(self, level, getattr(self, level) + 1)
                    if level.capitalize() in self.control.level:
                        self.included = True


if __name__ == "__main__":
    """Protect this from being executed when loaded by lint-like tools."""
    Control().run()
