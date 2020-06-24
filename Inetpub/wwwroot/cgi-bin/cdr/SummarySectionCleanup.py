#!/usr/bin/env python

"""Report on anomalous sections found in selected Summaries.

See https://tracker.nci.nih.gov/browse/OCECDR-3804.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Access to the database and report creation tools."""

    SUBTITLE = "Summary Section Cleanup Report"
    LOGNAME = "SectionCleanup"
    B_PATH = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
    T_PATH = "/Summary/TranslationOf/@cdr:ref"
    A_PATH = "/Summary/SummaryMetaData/SummaryAudience"
    L_PATH = "/Summary/SummaryMetaData/SummaryLanguage"

    def populate_form(self, page, titles=None):
        """Fill in the fields for the report request.

        Pass:
            page - HTMLPage object where the fields go
            titles - optional sequence of title fragment object
                     (if present, they will trigger a cascading
                     form to select one of the summary titles)
        """

        self.add_summary_selection_fields(page, titles=titles)
        page.add_output_options(default=self.format)

    def build_tables(self):
        """Assemble the report's single table."""

        opts = dict(columns=self.columns, caption=self.subtitle)
        return self.Reporter.Table(self.rows, **opts)

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
        """PDQ board(s) selected for the report."""

        if not hasattr(self, "_board"):
            boards = self.fields.getlist("board")
            if not boards or "all" in boards:
                self._board = ["all"]
            else:
                self._board = []
                for id in boards:
                    try:
                        board = int(id)
                    except Exception:
                        self.bail()
                    if board not in self.boards:
                        self.bail()
                    self._board.append(int(id))
        return self._board

    @property
    def boards(self):
        """For validation of the board selections."""

        if not hasattr(self, "_boards"):
            self._boards = self.get_boards()
        return self._boards

    @property
    def cdr_id(self):
        """Integer for the summary document selected for the report."""

        if not hasattr(self, "_cdr_id"):
            self._cdr_id = self.fields.getvalue("cdr-id")
            if self._cdr_id:
                try:
                    self._cdr_id = Doc.extract_id(self._cdr_id)
                except Exception:
                    self.bail("Invalid format for CDR ID")
        return self._cdr_id

    @property
    def columns(self):
        """Sequence of column definitions for the report table."""

        return (
            self.Reporter.Column("CDR ID", width="80px"),
            self.Reporter.Column("Title", width="400px"),
            self.Reporter.Column("Summary Sections", width="500px"),
        )

    @property
    def fragment(self):
        """Title fragment provided for matching summaries."""

        if not hasattr(self, "_fragment"):
            self._fragment = self.fields.getvalue("title")
        return self._fragment

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
    def rows(self):
        """One row for each summary which has problem sections."""
        return [summary.row for summary in self.summaries if summary.sections]

    @property
    def summaries(self):
        """Summaries selected by ID, title, or board."""

        if not hasattr(self, "_summaries"):
            if self.selection_method == "title":
                if not self.fragment:
                    self.bail("Title fragment is required.")
                if not self.summary_titles:
                    self.bail("No summaries match that title fragment")
                if len(self.summary_titles) == 1:
                    summary = Summary(self, self.summary_titles[0].id)
                    self._summaries = [summary]
                else:
                    self.populate_form(self.form_page, self.summary_titles)
                    self.form_page.send()
            elif self.selection_method == "id":
                if not self.cdr_id:
                    self.bail("CDR ID is required.")
                self._summaries = [Summary(self, self.cdr_id)]
            else:
                if not self.board:
                    self.bail("At least one board is required.")
                query = self.Query("active_doc d", "d.id")
                query.join("query_term_pub a", "a.doc_id = d.id")
                query.where(f"a.path = '{self.A_PATH}'")
                query.where(query.Condition("a.value", f"{self.audience}s"))
                query.join("query_term_pub l", "l.doc_id = d.id")
                query.where(f"l.path = '{self.L_PATH}'")
                query.where(query.Condition("l.value", self.language))
                if "all" not in self.board:
                    if self.language == "English":
                        query.join("query_term_pub b", "b.doc_id = d.id")
                    else:
                        query.join("query_term_pub t", "t.doc_id = d.id")
                        query.where(query.Condition("t.path", self.T_PATH))
                        query.join("query_term b", "b.doc_id = t.int_val")
                    query.where(query.Condition("b.path", self.B_PATH))
                    query.where(query.Condition("b.int_val", self.board, "IN"))
                query.log(label="SummarySectionCleanup")
                rows = query.unique().execute(self.cursor).fetchall()
                summaries = [Summary(self, row.id) for row in rows]
                self._summaries = sorted(summaries)
                self.logger.info("found %d summaries", len(self._summaries))
        return self._summaries


class Summary:
    """One of the CDR PDQ summaries selected for the report.

    Attributes:
        id       -  CDR ID of summary document
        title    -  title of summary (from title column of all_docs table)
        control  -  object holding request parameters for report
        problems -  sequence of strings identifying sections with problems
    """

    NORMAL_CONTENT = {"Para", "SummarySection", "Table", "QandASet",
                      "ItemizedList", "OrderedList"}

    def __init__(self, control, doc_id):
        """Remember the caller's values.

        Pass:
            control - access to the DB and report options and creation tools
            doc_id - integer for the summary's CDR document ID
        """

        self.__control = control
        self.__doc_id = doc_id

    def __lt__(self, other):
        """Support case-insensitive sorting of the summaries by title."""
        return self.key < other.key

    @property
    def control(self):
        """Access to the DB and report options and creation tools."""
        return self.__control

    @property
    def doc(self):
        """`Doc` object for the CDR Summary document."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.control.session, id=self.id)
        return self._doc

    @property
    def id(self):
        """Integer for the summary's CDR document ID."""
        return self.__doc_id

    @property
    def key(self):
        """Composite values for sorting."""

        if not hasattr(self, "_key"):
            self._key = self.title.lower(), self.id
        return self._key

    @property
    def row(self):
        """Assemble the row for the report table."""
        return self.id, self.title, self.sections

    @property
    def sections(self):
        """Sequence of string identifying anomalous summary sections.

        What we're looking for are sections which don't have any of
        the elements in the class- level `NORMAL_CONTENT` set property.

        Here's the logic:

          FOR EACH SUMMARY SECTION:
            IF THERE ARE NO CHILD ELEMENTS:
              REPORT THIS SECTION AS EMPTY
              SHOW THE NEXT SECTION (OR INDICATE THIS WAS THE LAST SECTION)
            OTHERWISE, IF THE FIRST CHILD IS A TITLE ELEMENT:
              IF THERE ARE NO NORMAL CONTENT CHILDREN:
                IF THERE IS NO INSERTION ANCESTOR OF THIS SECTION ELEMENT:
                  SHOW THE TITLE OF THIS SECTION
                  SHOW THE TAGS OF THE CHILDREN OF THIS SUMMARY SECTION ELEMENT

        """

        if not hasattr(self, "_sections"):
            self._sections = []
            prev_section_empty = False
            for section in self.doc.root.iter("SummarySection"):
                children = [c for c in section if isinstance(c.tag, str)]
                tags = [child.tag for child in children]
                if not children:
                    self._sections.append("*** Empty Section ***")
                    prev_section_empty = True
                elif tags[0] == "Title":
                    title = children[0].text or None
                    if title is None or not title.strip():
                        title = "EMPTY TITLE"
                    if prev_section_empty:
                        self._sections.append("*** %s" % title)
                    if not (set(tags) & Summary.NORMAL_CONTENT):
                        ancestors = [a.tag for a in section.iterancestors()]
                        if "Insertion" not in ancestors:
                            if not prev_section_empty:
                                self._sections.append(title)
                            self._sections.append(tags)
                    prev_section_empty = False
            if prev_section_empty:
                self._sections.append("*** Last Section")
        return self._sections

    @property
    def title(self):
        """String for the title of the summary document."""
        return self.doc.title


if __name__ == "__main__":
    """Protect this from being executed when loaded by lint-like tools."""
    Control().run()
