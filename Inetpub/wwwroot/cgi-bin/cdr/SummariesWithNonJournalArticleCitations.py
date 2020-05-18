#!/usr/bin/env python

"""Report on summaries citing publications other than journal articles.
"""

from collections import UserDict
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Access to the database and report-creation tools."""

    SUBTITLE = "Summaries With Non-Journal Article Citations Report"
    LANGUAGE_PATH = "/Summary/SummaryMetaData/SummaryLanguage"
    BOARD_PATH = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"

    def build_tables(self):
        """Assemble the single table for the report."""
        return self.Reporter.Table(self.rows, columns=self.columns)

    def populate_form(self, page):
        """Add the report request fields to the form.

        Pass:
            page - HTMLPage object where we put the forms
        """

        self.add_board_fieldset(page)
        self.add_language_fieldset(page)
        fieldset = page.fieldset("Select Citation Type (one or more)")
        for value in self.types:
            fieldset.append(page.checkbox("type", value=value, label=value))
        page.form.append(fieldset)

    @property
    def board(self):
        """PDQ board ID(s) selected for the report."""

        if not hasattr(self, "_board"):
            ids = self.fields.getlist("board")
            if not ids or "all" in ids:
                self._board = list(self.boards)
            else:
                self._board = []
                for id in ids:
                    if not id.isdigit():
                        self.bail()
                    id = int(id)
                    if id not in self.boards:
                        self.bail()
                    self._board.append(id)
        return self._board

    @property
    def boards(self):
        """Dictionary of PDQ board names indexed by integer ID."""

        if not hasattr(self, "_boards"):
            self._boards = self.get_boards()
        return self._boards

    @property
    def citations(self):
        """Dictionary of `Citation` objects indexed by CDR ID."""

        if not hasattr(self, "_citations"):
            class Citations(UserDict):
                def __init__(self, control):
                    self.__control = control
                    UserDict.__init__(self)
                def __getitem__(self, key):
                    if key not in self.data:
                        self.data[key] = Citation(self.__control, key)
                    return self.data[key]
            self._citations = Citations(self)
        return self._citations

    @property
    def columns(self):
        """Labels at the top of the report table's columns."""

        return (
            self.Reporter.Column("Summary ID"),
            self.Reporter.Column("Summary Title"),
            self.Reporter.Column("Summary Sec Title"),
            self.Reporter.Column("Citation Type"),
            self.Reporter.Column("Citation ID"),
            self.Reporter.Column("Citation Title"),
            self.Reporter.Column("Publication Details/Other Publication Info"),
        )

    @property
    def eligible_citations(self):
        """IDs for citations of the type(s) we want, in any summary."""

        if not hasattr(self, "_eligible_citations"):
            query = self.Query("query_term", "doc_id").unique()
            query.where("path = '/Citation/PDQCitation/CitationType'")
            if self.type:
                query.where(query.Condition("value", self.type, "IN"))
            else:
                query.where("value NOT LIKE 'Journal%'")
                query.where("value NOT LIKE 'Proceeding%'")
            rows = query.execute(self.cursor).fetchall()
            self._eligible_citations = {row.doc_id for row in rows}
            n = len(self._eligible_citations)
            self.logger.info("%d citation docs have the right type", n)
        return self._eligible_citations

    @property
    def language(self):
        """Language selected for summaries to be included in the report."""

        if not hasattr(self, "_language"):
            self._language = self.fields.getvalue("language", "English")
            if self._language not in self.LANGUAGES:
                self.bail()
        return self._language

    @property
    def rows(self):
        """Sequence of value sets, one for each citation link found."""

        if not hasattr(self, "_rows"):
            self._rows = []
            for summary in self.summaries:
                for citation_link in sorted(summary.citation_links):
                    self._rows.append(citation_link.row)
        return self._rows

    @property
    def summaries(self):
        """PDQ summaries selected for the report."""

        if not hasattr(self, "_summaries"):
            query = self.Query("query_term_pub s", "s.doc_id").unique()
            query.join("active_doc a", "a.id = s.doc_id")
            query.join("query_term c", "c.doc_id = s.int_val")
            query.where("s.path LIKE '/Summary%CitationLink/@cdr:ref'")
            query.where("c.path = '/Citation/PDQCitation/CitationType'")
            if self.type:
                query.where(query.Condition("c.value", self.type, "IN"))
            else:
                query.where("c.value NOT LIKE 'Journal%'")
                query.where("c.value NOT LIKE 'Proceeding%'")
            if not self.board:
                query.join("query_term_pub l", "l.doc_id = s.doc_id")
                query.where(f"l.path = '{self.LANGUAGE_PATH}'")
                query.where(query.Condition("l.value", self.language))
            elif self.language == "English":
                query.join("query_term_pub b", "b.doc_id = s.doc_id")
                query.where(query.Condition("b.int_val", self.board, "IN"))
            else:
                query.join("query_term_pub t", "t.doc_id = s.doc_id")
                query.where("t.path = '/Summary/TranslationOf/@cdr:ref'")
                query.join("query_term b", "b.doc_id = t.int_val")
                query.where(f"b.path = '{self.BOARD_PATH}'")
                query.where(query.Condition("b.int_val", self.board, "IN"))
            rows = query.order("s.doc_id").execute(self.cursor).fetchall()
            self._summaries = [Summary(self, row.doc_id) for row in rows]
            self.logger.info("found %d summaries", len(self._summaries))
        return self._summaries

    @property
    def type(self):
        """Type(s) of citation selected to be included on the report."""

        if not hasattr(self, "_type"):
            self._type = self.fields.getlist("type")
            if set(self._type) - set(self.types):
                self.bail()
        return self._type

    @property
    def types(self):
        """Valid values for the citation type checkboxes."""

        if not hasattr(self, "_types"):
            query = self.Query("query_term", "value").order("value")
            query.where("path = '/Citation/PDQCitation/CitationType'")
            query.where("value NOT LIKE 'Proceeding%'")
            query.where("value NOT LIKE 'Journal%'")
            rows = query.unique().execute(self.cursor).fetchall()
            self._types = [row.value for row in rows if row.value]
        return self._types


class Citation:
    """Information about a CDR PDQ Citation document."""

    TITLE_PATH = "PDQCitation/CitationTitle"
    TYPE_PATH = "PDQCitation/CitationType"
    FILTERS = (
        "set:Denormalization Citation Set",
        "name:Copy XML for Citation QC Report",
    )

    def __init__(self, control, id):
        """Remember the caller's values.

        Pass:
            control - object with access to the database and the report options
            id - integer for the unique CDR ID for this PDQ Citation document
        """

        self.__control = control
        self.__id = id

    @property
    def details(self):
        """Publication details for the PDQ citation."""

        if not hasattr(self, "_details"):
            self._details = None
            try:
                result = self.doc.filter(*self.FILTERS)
            except Exception as e:
                self.__control.logger.exception("filtering %d", self.doc.id)
                message = f"failure filtering {self.doc.cdr_id}: {e}"
                self.__control.bail(message)
            for node in result.result_tree.iter("FormattedReference"):
                self._details = Doc.get_text(node) # XXX WAS node.text ???
        return self._details

    @property
    def doc(self):
        """`Doc` object for this CDR PDQ Citation document."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.__control.session, id=self.__id)
        return self._doc

    @property
    def publication_information(self):
        """Publication details, including link if available (don't cache)."""

        if self.url:
            B = self.__control.HTMLPage.B
            link = B.A(self.url, href=self.url, target="_blank")
            return B.SPAN(self.details, B.BR(), link)
        return self.details

    @property
    def title(self):
        """String for the title of the PDQ Citation document."""

        if not hasattr(self, "_title"):
            self._title = Doc.get_text(self.doc.root.find(self.TITLE_PATH))
        return self._title

    @property
    def type(self):
        """String for the type of the PDQ Citation document."""

        if not hasattr(self, "_type"):
            self._type = Doc.get_text(self.doc.root.find(self.TYPE_PATH))
        return self._type

    @property
    def url(self):
        """String for the citation's web site, if any."""

        if not hasattr(self, "_url"):
            self._url = None
            if "Internet" in self.type:
                for node in self.doc.root.iter("ExternalRef"):
                    self._url = node.get(f"{{{Doc.NS}}}xref")
        return self._url


class CitationLink:
    """PDQ Citation found in a PDQ summary."""

    def __init__(self, summary, node):
        """Remember the caller's values.

        Pass:
            summary - object for the summary in which this link was found
            node - DOM node for the link
        """

        self.__summary = summary
        self.__node = node

    def __lt__(self, other):
        """Use the segmented sort key to put the links in order."""
        return self.sort_key < other.sort_key

    @property
    def citation(self):
        """Reference to `Citation` object for document to which this links."""
        return self.control.citations[self.id]

    @property
    def control(self):
        """Access to the report options and report-building tools."""
        return self.summary.control

    @property
    def id(self):
        """Integer for the PDQ Citation document's unique CDR ID."""

        if not hasattr(self, "_id"):
            self._id = None
            ref = self.__node.get(f"{{{Doc.NS}}}ref")
            if ref:
                try:
                    self._id = Doc.extract_id(ref)
                except Exception:
                    message = "In %s: bad citation reference %r"
                    args = self.summary.doc.cdr_id, ref
                    self.control.logger.exception(message, *args)
        return self._id

    @property
    def in_scope(self):
        """True if this citation has a type selected for the report."""
        return self.id in self.control.eligible_citations

    @property
    def key(self):
        """Report links to the same citation from a summary section once."""

        if not hasattr(self, "_key"):
            self._key = self.id, self.section_title
        return self._key

    @property
    def row(self):
        """Provide the information for this link to the report's table."""

        if not hasattr(self, "_row"):
            self._row = (
                self.summary.id,
                self.summary.title,
                self.section_title,
                self.citation.type,
                self.citation.doc.id,
                self.citation.title,
                self.citation.publication_information,
            )
        return self._row

    @property
    def section_title(self):
        """Title of the summary section in which this link was found."""

        if not hasattr(self, "_section_title"):
            self._section_title = ""
            parent = self.__node.getparent()
            while parent is not None and parent.tag != "SummarySection":
                parent = parent.getparent()
            if parent is not None:
                self._section_title = Doc.get_text(parent.find("Title"))
        return self._section_title

    @property
    def sort_key(self):
        """Order the citation links by section title, then cite type/id."""

        if not hasattr(self, "_sort_key"):
            self._sort_key = (
                self.section_title or "",
                self.citation.type,
                self.citation.doc.id,
            )
        return self._sort_key

    @property
    def summary(self):
        """Object for the summary in which this link was found."""
        return self.__summary


class Summary:
    """PDQ Summary selected for inclusion on the report."""

    def __init__(self, control, id):
        """Remember the caller's values.

        Pass:
            control - access to the database and the report's options
            id - integer for the summary's unique CDR document ID
        """

        self.__control = control
        self.__id = id

    @property
    def citation_links(self):
        """Sequence of `CitationLink` objects for links in this summary."""

        if not hasattr(self, "_citation_links"):
            self._citation_links = []
            keys = set()
            for node in self.doc.root.iter("CitationLink"):
                citation_link = CitationLink(self, node)
                if citation_link.in_scope and citation_link.key not in keys:
                    self._citation_links.append(citation_link)
                    keys.add(citation_link.key)
        return self._citation_links

    @property
    def control(self):
        """Access to the database and the report's options."""
        return self.__control

    @property
    def doc(self):
        """`Doc` object for this CDR Summary document."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.control.session, id=self.id)
        return self._doc

    @property
    def id(self):
        """Integer for the summary's unique CDR document ID."""
        return self.__id

    @property
    def title(self):
        """Official title of the PDQ summary."""

        if not hasattr(self, "_title"):
            self._title = Doc.get_text(self.doc.root.find("SummaryTitle"))
        return self._title


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
