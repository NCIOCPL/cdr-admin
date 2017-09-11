#----------------------------------------------------------------------
# Report on the types of changes recorded in selected Summaries.
# JIRA::OCECDR-3703
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

    def __init__(self):
        """
        Collect and validate the form's parameters.
        """

        cdrcgi.Control.__init__(self, "Summary Section Cleanup Report")
        self.boards = self.get_boards()
        self.selection_method = self.fields.getvalue("method", "board")
        self.audience = self.fields.getvalue("audience", "Health Professional")
        self.language = self.fields.getvalue("language", "English")
        self.board = self.fields.getlist("board") or ["all"]
        self.cdr_id = self.fields.getvalue("cdr-id")
        self.fragment = self.fields.getvalue("title")
        self.validate()

    def populate_form(self, form, titles=None):
        """
        Overridden version of the method to fill in the fields for
        the CGI request's form. In addition to being invoked by the
        base class's run() method when the page is first requested,
        this method is invoked by our build_tables() method below,
        when the user has selected the "by summary title" method
        of choosing a summary, with a title fragment which matches
        more than one summary, so that we can put the form up again,
        letting the user pick which of the matching summaries should
        be used for the report.
        """

        self.add_summary_selection_fields(form, titles=titles)
        form.add_output_options(default=self.format)

    def build_tables(self):
        """
        Overrides the base class's version of this method to assemble
        the tables to be displayed for this report. If the user
        chooses the "by summary title" method for selecting which
        summary to use for the report, and the fragment supplied
        matches more than one summary document, display the form
        a second time so the user can pick the summary.
        """

        if self.selection_method == "title":
            if not self.fragment:
                cdrcgi.bail("Title fragment is required.")
            titles = self.summaries_for_title(self.fragment)
            if not titles:
                cdrcgi.bail("No summaries match that title fragment")
            if len(titles) == 1:
                summaries = [Summary(titles[0].id, self)]
            else:
                opts = {
                    "buttons": self.buttons,
                    "action": self.script,
                    "subtitle": self.title,
                    "session": self.session
                }
                form = cdrcgi.Page(self.PAGE_TITLE, **opts)
                self.populate_form(form, titles)
                form.send()
        elif self.selection_method == "id":
            if not self.cdr_id:
                cdrcgi.bail("CDR ID is required.")
            summaries = [Summary(self.cdr_id, self)]
        else:
            if not self.board:
                cdrcgi.bail("At least one board is required.")
            summaries = self.summaries_for_boards()

        # We have the summaries; build the report table.
        cols = self.get_cols()
        rows = [summary.get_row() for summary in summaries if summary.changes]
        return [cdrcgi.Report.Table(cols, rows, caption=self.title)]

    def get_cols(self):
        "Return a sequence of column definitions for the report table."

        return (
            cdrcgi.Report.Column("CDR ID", width="80px"),
            cdrcgi.Report.Column("Title", width="400px"),
            cdrcgi.Report.Column("Summary Sections", width="500px")
        )

    def summaries_for_boards(self):
        """
        The user has asked for a report of multiple summaries for
        one or more of the boards. Find the boards' summaries whose
        language match the request parameters, and return a sorted
        list of Summary objects for them.
        """

        b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        t_path = "/Summary/TranslationOf/@cdr:ref"
        query = cdrdb.Query("active_doc d", "d.id")
        query.join("query_term_pub a", "a.doc_id = d.id")
        query.where("a.path = '/Summary/SummaryMetaData/SummaryAudience'")
        query.where(query.Condition("a.value", self.audience + "s"))
        query.join("query_term_pub l", "l.doc_id = d.id")
        query.where("l.path = '/Summary/SummaryMetaData/SummaryLanguage'")
        query.where(query.Condition("l.value", self.language))
        if "all" not in self.board:
            if self.language == "English":
                query.join("query_term_pub b", "b.doc_id = d.id")
            else:
                query.join("query_term_pub t", "t.doc_id = d.id")
                query.where(query.Condition("t.path", t_path))
                query.join("query_term b", "b.doc_id = t.int_val")
            query.where(query.Condition("b.path", b_path))
            query.where(query.Condition("b.int_val", self.board, "IN"))
        rows = query.unique().execute(self.cursor).fetchall()
        return sorted([Summary(row[0], self) for row in rows])

    def validate(self):
        """
        Separate validation method, to make sure the CGI request's
        parameters haven't been tampered with by an intruder.
        """

        msg = cdrcgi.TAMPERING
        if self.audience not in self.AUDIENCES:
            cdrcgi.bail(msg)
        if self.language not in self.LANGUAGES:
            cdrcgi.bail(msg)
        if self.selection_method not in self.SUMMARY_SELECTION_METHODS:
            cdrcgi.bail(msg)
        if self.format not in self.FORMATS:
            cdrcgi.bail(msg)
        boards = []
        for board in self.board:
            if board == "all":
                boards.append("all")
            else:
                try:
                    board = int(board)
                except:
                    cdrcgi.bail(msg)
                if board not in self.boards:
                    cdrcgi.bail(msg)
                boards.append(board)
        self.board = boards
        if self.cdr_id:
            try:
                self.cdr_id = cdr.exNormalize(self.cdr_id)[1]
            except:
                cdrcgi.bail("Invalid format for CDR ID")

class Summary:
    """
    Represents one CDR Summary document.

    Attributes:
        id       -  CDR ID of summary document
        title    -  title of summary (from title column of all_docs table)
        control  -  object holding request parameters for report
        changes  -  sequence of string descripts of changed sections
    """

    NORMAL_CONTENT = set(["Para", "SummarySection", "Table", "QandASet",
                          "ItemizedList", "OrderedList"])

    def __init__(self, doc_id, control):
        """
        Remember summary identification and recursively walk through
        all of the Summary sections (depth first) looking for information
        to be added to the report.

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

        self.id = doc_id
        self.control = control
        self.changes = []
        query = cdrdb.Query("document", "title", "xml")
        query.where(query.Condition("id", doc_id))
        self.title, xml = query.execute(control.cursor).fetchone()
        root = etree.XML(xml.encode("utf-8"))
        prev_section_empty = False
        for section in root.iter("SummarySection"):

            # Get the element child nodes for the secion (skip PIs, etc.).
            children = [c for c in list(section) if self.is_element(c)]
            # Another possibility:
            #children = [c for c in list(section) if type(c) is etree._Element]

            tags = [child.tag for child in children]
            if not children:
                self.changes.append("*** Empty Section ***")
                prev_section_empty = True
            elif tags[0] == "Title":
                title = children[0].text or None
                if title is None or not title.strip():
                    title = "EMPTY TITLE"
                if prev_section_empty:
                    self.changes.append(u"*** %s" % title)
                if not (set(tags) & Summary.NORMAL_CONTENT):
                    ancestors = [a.tag for a in section.iterancestors()]
                    if "Insertion" not in ancestors:
                        if not prev_section_empty: # title already shown?
                            self.changes.append(title)
                        self.changes.append(tags)
                prev_section_empty = False
        if prev_section_empty:
            self.changes.append("*** Last Section")

    def __cmp__(self, other):
        "Support sorting the summaries by title."
        return cmp((self.title, self.id), (other.title, other.id))

    def get_row(self):
        "Assemble the row for the report table."
        return [self.id, self.title, self.changes]

    @staticmethod
    def is_element(node):
        "We need to skip over processing instructions and comments."
        return isinstance(node.tag, basestring)

if __name__ == "__main__":
    "Protect this from being executed when loaded by lint-like tools."
    Control().run()
