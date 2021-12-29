#!/usr/bin/env python

"""Report on summaries containing specified markup.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Access to the database and report-creation tools."""

    LEVELS = "Publish", "Approved", "Proposed", "Rejected"
    INCLUDE_AB_MARKUP = "Include Advisory Board markup"
    INCLUDE_WITHOUT_MARKUP = "Include summaries without markup"
    CSS = (
        "td { width: 60px; text-align: center; vertical-align: middle; }",
        "td.active { width: 80px; }",
        "td.title { text-align: left; vertical-align: top; width: 550px; }",
    )

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

    def show_report(self):
        """Override base class version to add custom styling."""

        self.report.page.add_css("\n".join(self.CSS))
        self.report.send()

    @property
    def advisory(self):
        """True if the report should include advisory board markup."""
        return self.fields.getvalue("advisory") == "yes"

    @property
    def audience(self):
        """Audience selected for the report."""

        if not hasattr(self, "_audience"):
            default = self.AUDIENCES[0]
            self._audience = self.fields.getvalue("audience", default)
            if self._audience not in self.AUDIENCES:
                self.bail()
        return self._audience

    @property
    def board(self):
        """PDQ board(s) selected by the user for the report."""

        if not hasattr(self, "_board"):
            boards = self.fields.getlist("board") or ["all"]
            if "all" in boards:
                self._board = ["all"]
            else:
                self._board = []
                for id in boards:
                    if not id.isdigit():
                        self.bail()
                    id = int(id)
                    if id not in self.boards:
                        self.bail()
                    self.board.append(id)
        return self._board

    @property
    def boards(self):
        """Dictionary of PDQ boards for the form."""

        if not hasattr(self, "_boards"):
            self._boards = self.get_boards()
        return self._boards

    @property
    def columns(self):
        """Sequence of column definitions for the report table(s)."""

        if not hasattr(self, "_columns"):
            s = "s" if self.language == "Spanish" else ""
            self._columns = [
                self.Reporter.Column("Doc ID"),
                self.Reporter.Column(f"Summary Title{s}"),
            ]
            for level in self.LEVELS:
                if level in self.level:
                    self._columns.append(self.Reporter.Column(level))
            if self.advisory:
                self._columns.append(self.Reporter.Column("Advisory"))
        return self._columns

    @property
    def language(self):
        """Language selected for the report."""

        if not hasattr(self, "_language"):
            default = self.LANGUAGES[0]
            self._language = self.fields.getvalue("language", default)
            if self._language not in self.LANGUAGES:
                self.bail()
        return self._language

    @property
    def level(self):
        """Markup level(s) selected for the report."""

        if not hasattr(self, "_level"):
            self._level = self.fields.getlist("level")
            if set(self._level) - set(self.LEVELS):
                self.bail()
        return self._level

    @property
    def show_all(self):
        """True if the report should include summaries without markup."""
        return self.fields.getvalue("show-all") == "yes"

    @property
    def subtitle(self):
        """What we display directly under the main banner."""

        if not hasattr(self, "_subtitle"):
            if self.request == self.SUBMIT:
                today = self.started.strftime("%Y-%m-%d")
                args = self.language, self.audience, today
                pattern = "{} {} Summaries With Markup - {}"
                self._subtitle = pattern.format(*args)
            else:
                self._subtitle = self.SUBTITLE
        return self._subtitle


class Board:
    """PDQ board selected for the report."""

    def __init__(self, control, doc_id):
        """Remember the caller's values.

        Pass:
            control - access to the database and report-creation tools
            doc_id - integer for the CDR document ID for the board
        """

        self.__control = control
        self.__doc_id = doc_id

    def __lt__(self, other):
        """Order the PDQ boards by name."""
        return self.name < other.name

    @property
    def control(self):
        """Object with access to the database and report-creation tools."""
        return self.__control

    @property
    def id(self):
        """Integer for the board's CDR Organization document ID."""
        return self.__doc_id

    @property
    def name(self):
        """String for the board's short name."""
        return self.control.boards[self.id]

    @property
    def summaries(self):
        """Publishable summaries in scope for this report."""

        if not hasattr(self, "_summaries"):
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
            self._summaries = []
            for row in query.execute(self.control.cursor).fetchall():
                summary = self.Summary(self.control, row)
                if summary.in_scope:
                    self._summaries.append(summary)
        return self._summaries

    @property
    def table(self):
        """Assemble the report table for the board."""

        if not hasattr(self, "_table"):
            rows = [summary.row for summary in sorted(self.summaries)]
            opts = dict(columns=self.control.columns, caption=self.name)
            self._table = self.control.Reporter.Table(rows, **opts)
        return self._table

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

            self.__control = control
            self.__row = row

        def __lt__(self, other):
            """Sort by normalized title and document ID."""
            return self.key < other.key

        @property
        def control(self):
            """Object with access to the DB and report-creation tools."""
            return self.__control

        @property
        def counts(self):
            """Object for keeping track of markup found in the summary."""

            if not hasattr(self, "_counts"):
                self._counts = self.Counts(self.control)
            return self._counts

        @property
        def doc(self):
            """CDR API's `Doc` object for the PDQ summary."""

            if not hasattr(self, "_doc"):
                self._doc = Doc(self.control.session, id=self.id)
            return self._doc

        @property
        def id(self):
            """Integer for the CDR document ID for this summary."""
            return self.__row.id

        @property
        def in_scope(self):
            """True if the summary should be included on the report.

            Do a string scan to optimize away parsing of the document
            in the event that there are no Insertion or Deletion
            elements at all in the summary document. Otherwise,
            extract the counts of each type of markup.
            """

            if not hasattr(self, "_in_scope"):
                self._in_scope = False
                xml = self.doc.xml
                if "<Insertion" in xml or "<Deletion" in xml:
                    for node in self.doc.root.iter("Insertion", "Deletion"):
                        self.counts.increment_level(node.get("RevisionLevel"))
                        if node.get("Source") == "advisory-board":
                            self.counts.advisory += 1
                if self.control.show_all or self.counts.included:
                    self._in_scope = True
                elif self.control.advisory and self.counts.advisory:
                    self._in_scope = True
            return self._in_scope

        @property
        def is_module(self):
            """True if this summary can only be used as a module."""

            if not hasattr(self, "_is_module"):
                query = self.control.Query("query_term", "value")
                query.where("path = '/Summary/@ModuleOnly'")
                query.where(query.Condition("doc_id", self.id))
                rows = query.execute(self.control.cursor).fetchall()
                self._is_module = rows[0][0] == "Yes" if rows else False
            return self._is_module

        @property
        def key(self):
            """Sort by normalized title and document ID."""

            if not hasattr(self, "_key"):
                self._key = self.title.lower(), self.id
            return self._key

        @property
        def original_title(self):
            """Title of the summary of which this is a translation."""

            if not hasattr(self, "_original_title"):
                self._original_title = None
                if len(self.__row) > 1:
                    id = self.__row[1]
                    self._original_title = self.__summary_title(id)
            return self._original_title

        @property
        def row(self):
            """Assemble the summary's table row for the report."""

            if not hasattr(self, "_row"):
                Cell = self.control.Reporter.Cell
                title = self.title
                if self.original_title is not None:
                    title = title, f"({self.original_title})"
                self._row = [
                    Cell(self.id, href=self.url, target="_blank"),
                    Cell(title, classes="title"),
                ]
                for level in self.control.LEVELS:
                    if level in self.control.level:
                        value = getattr(self.counts, level.lower()) or ""
                        self._row.append(Cell(value, classes="active"))
                if self.control.advisory:
                    self._row.append(Cell(self.counts.advisory or ""))
            return self._row

        @property
        def title(self):
            """Official title of the PDQ summary."""

            if not hasattr(self, "_title"):
                self._title = self.__summary_title(self.id)
                if self.is_module:
                    self._title += " (Module)"
            return self._title

        @property
        def url(self):
            """Address of the QC report for this PDQ summary."""

            if not hasattr(self, "_url"):
                parms = dict(
                    DocId=self.doc.cdr_id,
                    DocType="Summary",
                    DocVersion="-1",
                    ReportType=self.QC_REPORT_TYPES[self.control.audience[0]],
                )
                self._url = self.control.make_url(self.QC_REPORT, **parms)
            return self._url

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
