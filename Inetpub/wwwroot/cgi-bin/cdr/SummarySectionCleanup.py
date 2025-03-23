#!/usr/bin/env python

"""Report on anomalous sections found in selected Summaries.

See https://tracker.nci.nih.gov/browse/OCECDR-3804.
"""

from functools import cached_property
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
    INSTRUCTIONS = (
        "This report identifies paragraph-level elements which are "
        "found outside of section elements, so that they can be moved "
        "to an appropriate location. The report is intended to be run "
        "on an onoing basis (or at least until all the misplaced elements "
        "have been fixed)."
    )

    def populate_form(self, page, titles=None):
        """Fill in the fields for the report request.

        Pass:
            page - HTMLPage object where the fields go
            titles - optional sequence of title fragment object
                     (if present, they will trigger a cascading
                     form to select one of the summary titles)
        """

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)
        self.add_summary_selection_fields(page, titles=self.summary_titles)
        page.add_output_options(default=self.format)

    def build_tables(self):
        """Assemble the report's single table."""

        opts = dict(columns=self.columns, caption=self.subtitle)
        return self.Reporter.Table(self.rows, **opts)

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
        """PDQ board(s) selected for the report."""

        values = self.fields.getlist("board")
        if not values or "all" in values:
            return ["all"]
        boards = []
        for value in values:
            try:
                board = int(value)
            except Exception:
                self.logger.exception("Internal error: shouldn't happen.")
                self.bail()
            if board not in self.boards:
                self.logger.error("Invalid board %d", board)
                self.bail()
            boards.append(board)
        return boards

    @cached_property
    def boards(self):
        """For validation of the board selections."""
        return self.get_boards()

    @cached_property
    def cdr_id(self):
        """Integer for the summary document selected for the report."""
        return self.fields.getvalue("cdr-id")

    @cached_property
    def columns(self):
        """Sequence of column definitions for the report table."""

        return (
            self.Reporter.Column("CDR ID", width="80px"),
            self.Reporter.Column("Title", width="400px"),
            self.Reporter.Column("Summary Sections", width="500px"),
        )

    @cached_property
    def fragment(self):
        """Title fragment provided for matching summaries."""

        if self.selection_method != "title":
            return None
        return self.fields.getvalue("title")

    @cached_property
    def language(self):
        """English or Spanish."""

        default = self.LANGUAGES[0]
        language = self.fields.getvalue("language", default)
        if language not in self.LANGUAGES:
            self.bail()
        return language

    @cached_property
    def ready(self):
        """True if we have what we need for the report."""

        if not self.request:
            return False
        match self.selection_method:
            case "id":
                if not self.cdr_id:
                    message = "CDR ID is required."
                    self.alerts.append(dict(message=message, type="error"))
                    return False
                try:
                    doc = Doc(self.session, id=self.cdr_id)
                    if doc.doctype.name != "Summary":
                        msg = f"CDR{doc.id} is a {doc.doctype} document."
                        self.alerts.append(dict(message=msg, type="warning"))
                        return False
                    self.cdr_id = doc.id
                except Exception:
                    self.logger.exception(self.cdr_id)
                    message = "Document {self.cdr_id} was not found."
                    self.alerts.append(dict(message=message, type="error"))
                    return False
                return True
            case "title":
                if not self.fragment:
                    message = "Title fragment is required."
                    self.alerts.append(dict(message=message, type="error"))
                    return False
                if not self.summary_titles:
                    message = "No summaries match that title fragment"
                    self.alerts.append(dict(message=message, type="warning"))
                    return False
                return len(self.summary_titles) == 1
            case "board":
                return True
            case _:
                self.bail()

    @cached_property
    def rows(self):
        """One row for each summary which has problem sections."""
        return [summary.row for summary in self.summaries if summary.sections]

    @cached_property
    def summaries(self):
        """Summaries selected by ID, title, or board."""

        match self.selection_method:
            case "id":
                return [Summary(self, self.cdr_id)]
            case "title":
                return [Summary(self, self.summary_titles[0].id)]
            case "board":
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
                self.logger.info("found %d summaries", len(summaries))
                return sorted(summaries)
            case _:
                self.bail()


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

        self.control = control
        self.id = doc_id

    def __lt__(self, other):
        """Support case-insensitive sorting of the summaries by title."""
        return self.key < other.key

    @cached_property
    def doc(self):
        """`Doc` object for the CDR Summary document."""
        return Doc(self.control.session, id=self.id)

    @cached_property
    def key(self):
        """Composite values for sorting."""
        return self.title.lower(), self.id

    @cached_property
    def row(self):
        """Assemble the row for the report table."""
        return self.id, self.title, self.sections

    @cached_property
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

        sections = []
        prev_section_empty = False
        for section in self.doc.root.iter("SummarySection"):
            children = [c for c in section if isinstance(c.tag, str)]
            tags = [child.tag for child in children]
            if not children:
                sections.append("*** Empty Section ***")
                prev_section_empty = True
            elif tags[0] == "Title":
                title = children[0].text or None
                if title is None or not title.strip():
                    title = "EMPTY TITLE"
                if prev_section_empty:
                    sections.append("*** %s" % title)
                if not (set(tags) & Summary.NORMAL_CONTENT):
                    ancestors = [a.tag for a in section.iterancestors()]
                    if "Insertion" not in ancestors:
                        if not prev_section_empty:
                            sections.append(title)
                        sections.append(tags)
                prev_section_empty = False
        if prev_section_empty:
            sections.append("*** Last Section")
        return sections

    @cached_property
    def title(self):
        """String for the title of the summary document."""
        return self.doc.title


if __name__ == "__main__":
    """Protect this from being executed when loaded by lint-like tools."""
    Control().run()
