#----------------------------------------------------------------------
# Report listing summaries containing specified markup.
#
# BZIssue::4671 - Summaries with Mark-up Report
# BZIssue::4922 - Enhancements to the Summaries with Markup Report
# BZIssue::5094 - Summ. with Markup Report - Add option to show all summaries
# BZIssue::5273 - Identifying Modules in Summary Reports
# JIRA::OCECDR-4062
#----------------------------------------------------------------------
import cdr
import cdrcgi
import cdrdb
import datetime
import lxml.etree as etree

class Control(cdrcgi.Control):
    """
    Override class to generate specific report.
    """

    LEVELS = ("Publish", "Approved", "Proposed", "Rejected")
    "RevisionLevel attribute values of Insertion and Deletion elements"

    INCLUDE_AB_MARKUP = "Include Advisory Board markup"
    INCLUDE_WITHOUT_MARKUP = "Include summaries without markup"
    "Labels for last fieldset on form"

    def __init__(self):
        """
        Collect and validate the form's parameters.
        """

        cdrcgi.Control.__init__(self, "Summaries Markup Report")
        self.boards = self.get_boards()
        self.audience = self.fields.getvalue("audience", "Health Professional")
        self.language = self.fields.getvalue("language", "English")
        self.board = self.fields.getlist("board") or ["all"]
        self.level = self.fields.getlist("level")
        self.advisory = self.fields.getvalue("advisory") == "yes"
        self.show_all = self.fields.getvalue("show-all") == "yes"
        self.validate()

    def populate_form(self, form, titles=None):
        "Ask the user to specify the options for the report."
        self.add_board_fieldset(form)
        self.add_audience_fieldset(form)
        self.add_language_fieldset(form)
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Markup Levels To Be Included"))
        for value in self.LEVELS:
            form.add_checkbox("level", value, value, checked=True)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Include Advisory Board Markup?"))
        form.add_radio("advisory", "Yes", "yes", checked=True)
        form.add_radio("advisory", "No", "no", checked=False)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Include Summaries Without Markup?"))
        form.add_radio("show-all", "Yes", "yes", checked=False)
        form.add_radio("show-all", "No", "no", checked=True)
        form.add("</fieldset>")

    def build_tables(self):
        "Return a sequence of one table for each board selected."
        if "all" in self.board:
            board_ids = sorted(self.boards, key=self.boards.get)
        else:
            board_ids = self.board
        boards = [Board(board_id, self) for board_id in board_ids]
        if self.language == "Spanish":
            Board.COLS[1].set_name("Summary Titles")
        return [board.make_table() for board in boards if board.summaries]

    def set_report_options(self, opts):
        "Add a subtitle and custom style rules to the report page."
        opts["subtitle"] = "%s %s Summaries - %s" % (self.language,
                                                     self.audience,
                                                     datetime.date.today())
        opts["css"] = """\
td { width: 60px; text-align: center; vertical-align: middle; }
td.active, td.inactive { width: 80px; }
td.inactive { background-color: #eee; }
td.title { text-align: left; vertical-aligh: top; width: 550px; }"""
        return opts

    def get_cols(self):
        "Return a sequence of column definitions for the report table."
        return (
            cdrcgi.Report.Column("CDR ID", width="80px"),
            cdrcgi.Report.Column("Title", width="400px"),
            cdrcgi.Report.Column("Summary Sections", width="500px")
        )

    def validate(self):
        """
        Separate validation method, to make sure the CGI request's
        parameters haven't been tampered with by an intruder.
        """

        self.validate_audience()
        self.validate_language()
        self.validate_boards()
        if set(self.level) - set(self.LEVELS):
            cdrcgi.bail(repr((self.level, self.LEVELS)))
            cdrcgi.bail(cdrcgi.TAMPERING)

class Board:
    """
    One of these for each board selected for the report.

    Attributes:
        control   - processing control object
        id        - Organization document ID for the board
        summaries - sorted list of summaries to be display in the table
                    for this board
    """

    NAMES = ["Doc ID", "Summary Title"] + list(Control.LEVELS) + ["Advisory"]
    COLS = [cdrcgi.Report.Column(name) for name in NAMES]
    "Column names for the board's report table."

    def __init__(self, doc_id, control):
        "Find all the board's summaries which are in scope for this report."
        self.id = doc_id
        self.name = control.boards.get(self.id) or cdrcgi.bail(cdrcgi.TAMPERING)
        self.control = control
        self.summaries = self.get_summaries()

    def get_summaries(self):
        """
        Find the board's publishable summaries for the selected
        audience and language.
        """

        b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        t_path = "/Summary/TranslationOf/@cdr:ref"
        cols = ["d.id"]
        if self.control.language == "Spanish":
            cols.append("t.int_val")
        query = cdrdb.Query("active_doc d", *cols)
        query.join("query_term_pub a", "a.doc_id = d.id")
        query.where("a.path = '/Summary/SummaryMetaData/SummaryAudience'")
        query.where(query.Condition("a.value", self.control.audience + "s"))
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
        rows = query.unique().execute(self.control.cursor).fetchall()
        summaries = []
        for row in rows:
            summary = self.Summary(self.control, row)
            if summary.in_scope():
                summaries.append(summary)
        return sorted(summaries)

    def make_table(self):
        "Assemble the report table for the board."
        rows = [s.make_row() for s in self.summaries]
        return cdrcgi.Report.Table(self.COLS, rows, caption=self.name)

    class Summary:
        """
        Summary managed by the current board.

        Attributes:
            control   - processing control object
            id        - CDR document ID for the summary
            title     - summary title drawn from the query_term table
                        (with suffix indicating module only if appropriate)
            counts    - object storing counts of markup types found
        """

        QC_REPORT = "QcReport.py"
        "Script for the QC report link"

        QC_REPORT_TYPES = { "H": "rs", "P": "pat" }
        "Parameter for QC report link, indexed by first letter of audience"

        def __init__(self, control, row):
            """
            Use the query_term table to get the summary title(s).
            Do a string scan to optimize away parsing of the document
            in the event that there are no Insertion or Deletion
            elements at all in the summary document. Otherwise,
            extract the counts of each type of markup.
            """

            self.control = control
            self.id = row[0]
            self.title = self.get_summary_title(self.id)
            if len(row) > 1:
                self.english_title = self.get_summary_title(row[1])
            self.counts = self.Counts(control)
            query = cdrdb.Query("query_term", "value")
            query.where("path = '/Summary/@ModuleOnly'")
            query.where(query.Condition("doc_id", self.id))
            rows = query.execute(control.cursor).fetchall()
            if rows and rows[0][0] == "Yes":
                self.title += " (Module)"
            query = cdrdb.Query("document", "xml")
            query.where(query.Condition("id", self.id))
            xml = query.execute(control.cursor).fetchone()[0]
            if "<Insertion" in xml or "<Deletion" in xml:
                root = etree.XML(xml.encode("utf-8"))
                for node in root.iter("Insertion", "Deletion"):
                    self.counts.increment_level(node.get("RevisionLevel"))
                    if node.get("Source") == "advisory-board":
                        self.counts.advisory += 1

        def __cmp__(self, other):
            "Support sorting the board's summaries by title."
            return cmp((self.title, self.id), (other.title, other.id))

        def get_summary_title(self, doc_id):
            "Pull the summary's title from the query_term table."
            query = cdrdb.Query("query_term", "value")
            query.where("path = '/Summary/SummaryTitle'")
            query.where(query.Condition("doc_id", doc_id))
            rows = query.execute(self.control.cursor).fetchall()
            return rows and rows[0][0] or "Title not found"

        def in_scope(self):
            "Find out whether the summary should be included on the report."
            if self.control.show_all or self.counts.included:
                return True
            return self.control.advisory and self.counts.advisory

        def make_row(self):
            "Assemble the table row for the report."
            title = self.title
            if hasattr(self, "english_title"):
                title = [title, "(%s)" % self.english_title]
            url = self.make_url()
            row = [
                cdrcgi.Report.Cell(self.id, href=url, target="_blank"),
                cdrcgi.Report.Cell(title, classes="title")
            ]
            for level in self.control.LEVELS:
                if level in self.control.level:
                    value = getattr(self.counts, level.lower())
                    row.append(self.make_active_cell(value))
                else:
                    row.append(self.make_inactive_cell())
            if self.control.advisory:
                row.append(self.make_active_cell(self.counts.advisory))
            else:
                row.append(self.make_inactive_cell())
            return row

        def make_active_cell(self, value):
            "Create a cell for a count type which is not suppressed."
            if not value:
                value = ""
            return cdrcgi.Report.Cell(value, classes="active")

        def make_inactive_cell(self):
            "Create a cell for a count type which is suppressed."
            return cdrcgi.Report.Cell("", classes="inactive")

        def make_url(self):
            "Let the user open the QC report for the summary in another tab."
            control = self.control
            parms = {
                "DocId": "CDR%10d" % self.id,
                "DocType": "Summary",
                "ReportType": self.QC_REPORT_TYPES.get(control.audience[0]),
                cdrcgi.SESSION: control.session
            }
            parms = ["%s=%s" % (name, parms[name]) for name in parms]
            return "%s?%s" % (self.QC_REPORT, "&".join(parms))

        class Counts:
            """
            Intelligent counting of occurrences of different types of
            markup.

            Attributes:
                control   - processing control object
                advisory  - number of elements with Source == "advisory-board"

                Also, one attribute for each of the possible values of
                the RevisionLevel attribute
            """

            LEVELS = set([level.lower() for level in Control.LEVELS])
            "All valid values for the RevisionLevel attribute"

            def __init__(self, control):
                """
                Remember the object with the report request settings
                and initialize all the counts to zero.
                """

                self.control = control
                self.advisory = self.included = 0
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
                        self.included += 1

if __name__ == "__main__":
    "Protect this from being executed when loaded by lint-like tools."
    Control().run()
