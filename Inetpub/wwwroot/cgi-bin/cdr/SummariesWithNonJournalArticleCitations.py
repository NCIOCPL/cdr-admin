#!/usr/bin/env python

"""Report on summaries citing publications other than journal articles.
"""

from functools import cached_property
from collections import UserDict
from cdrcgi import Controller, BasicWebPage
from cdrapi.docs import Doc


class Control(Controller):
    """Access to the database and report-creation tools."""

    SUBTITLE = "Summaries With Non-Journal Article Citations Report"
    LANGUAGE_PATH = "/Summary/SummaryMetaData/SummaryLanguage"
    BOARD_PATH = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
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
        page.add_script(self.SCRIPT)

    def show_report(self):
        """Overridden because the table is too wide for the standard layout."""

        report = BasicWebPage()
        report.wrapper.append(report.B.H1(self.subtitle))
        report.wrapper.append(self.table.node)
        report.wrapper.append(self.footer)
        report.page.head.append(report.B.STYLE("table { width: 100%; }"))
        report.send()

    @cached_property
    def board(self):
        """PDQ board ID(s) selected for the report."""

        ids = self.fields.getlist("board")
        if not ids or "all" in ids:
            return ["all"]
        else:
            boards = []
            for id in ids:
                if not id.isdigit():
                    self.bail()
                id = int(id)
                if id not in self.boards:
                    self.bail()
                boards.append(id)
        return boards

    @cached_property
    def boards(self):
        """Dictionary of PDQ board names indexed by integer ID."""
        return self.get_boards()

    @cached_property
    def citations(self):
        """Dictionary of `Citation` objects indexed by CDR ID."""

        class Citations(UserDict):
            def __init__(self, control):
                self.control = control
                UserDict.__init__(self)

            def __getitem__(self, key):
                if key not in self.data:
                    self.data[key] = Citation(self.control, key)
                return self.data[key]
        return Citations(self)

    @cached_property
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

    @cached_property
    def eligible_citations(self):
        """IDs for citations of the type(s) we want, in any summary."""

        query = self.Query("query_term", "doc_id").unique()
        query.where("path = '/Citation/PDQCitation/CitationType'")
        if self.type:
            query.where(query.Condition("value", self.type, "IN"))
        else:
            query.where("value NOT LIKE 'Journal%'")
            query.where("value NOT LIKE 'Proceeding%'")
        rows = query.execute(self.cursor).fetchall()
        eligible = {row.doc_id for row in rows}
        self.logger.info("%d citation docs have the right type", len(eligible))
        return eligible

    @cached_property
    def language(self):
        """Language selected for summaries to be included in the report."""

        language = self.fields.getvalue("language", "English")
        if language not in self.LANGUAGES:
            self.bail()
        return language

    @cached_property
    def rows(self):
        """Sequence of value sets, one for each citation link found."""

        rows = []
        for summary in self.summaries:
            for citation_link in sorted(summary.citation_links):
                rows.append(citation_link.row)
        return rows

    @cached_property
    def summaries(self):
        """PDQ summaries selected for the report."""

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
        if not self.board or "all" in self.board:
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
        summaries = [Summary(self, row.doc_id) for row in rows]
        self.logger.info("found %d summaries", len(summaries))
        return summaries

    @cached_property
    def table(self):
        """Assemble the single table for the report."""
        return self.Reporter.Table(self.rows, columns=self.columns)

    @cached_property
    def type(self):
        """Type(s) of citation selected to be included on the report."""

        type = self.fields.getlist("type")
        if set(type) - set(self.types):
            self.bail()
        return type

    @cached_property
    def types(self):
        """Valid values for the citation type checkboxes."""

        query = self.Query("query_term", "value").order("value")
        query.where("path = '/Citation/PDQCitation/CitationType'")
        query.where("value NOT LIKE 'Proceeding%'")
        query.where("value NOT LIKE 'Journal%'")
        rows = query.unique().execute(self.cursor).fetchall()
        return [row.value for row in rows if row.value]


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

        self.control = control
        self.id = id

    @cached_property
    def details(self):
        """Publication details for the PDQ citation."""

        try:
            result = self.doc.filter(*self.FILTERS)
        except Exception as e:
            self.control.logger.exception("filtering %d", self.doc.id)
            message = f"failure filtering {self.doc.cdr_id}: {e}"
            self.control.bail(message)
        details = None
        for node in result.result_tree.iter("FormattedReference"):
            details = Doc.get_text(node)
        return details

    @cached_property
    def doc(self):
        """`Doc` object for this CDR PDQ Citation document."""
        return Doc(self.control.session, id=self.id)

    @cached_property
    def publication_information(self):
        """Publication details, including link if available (don't cache)."""

        if self.url:
            B = self.control.HTMLPage.B
            link = B.A(self.url, href=self.url, target="_blank")
            return B.SPAN(self.details, B.BR(), link)
        return self.details

    @cached_property
    def title(self):
        """String for the title of the PDQ Citation document."""
        return Doc.get_text(self.doc.root.find(self.TITLE_PATH))

    @cached_property
    def type(self):
        """String for the type of the PDQ Citation document."""
        return Doc.get_text(self.doc.root.find(self.TYPE_PATH))

    @cached_property
    def url(self):
        """String for the citation's web site, if any."""

        url = None
        if "Internet" in self.type:
            for node in self.doc.root.iter("ExternalRef"):
                url = node.get(f"{{{Doc.NS}}}xref")
        return url


class CitationLink:
    """PDQ Citation found in a PDQ summary."""

    def __init__(self, summary, node):
        """Remember the caller's values.

        Pass:
            summary - object for the summary in which this link was found
            node - DOM node for the link
        """

        self.summary = summary
        self.node = node

    def __lt__(self, other):
        """Use the segmented sort key to put the links in order."""
        return self.sort_key < other.sort_key

    @cached_property
    def citation(self):
        """Reference to `Citation` object for document to which this links."""
        return self.control.citations[self.id]

    @cached_property
    def control(self):
        """Access to the report options and report-building tools."""
        return self.summary.control

    @cached_property
    def id(self):
        """Integer for the PDQ Citation document's unique CDR ID."""

        ref = self.node.get(f"{{{Doc.NS}}}ref")
        if ref:
            try:
                return Doc.extract_id(ref)
            except Exception:
                message = "In %s: bad citation reference %r"
                args = self.summary.doc.cdr_id, ref
                self.control.logger.exception(message, *args)
        return None

    @cached_property
    def in_scope(self):
        """True if this citation has a type selected for the report."""
        return self.id in self.control.eligible_citations

    @cached_property
    def key(self):
        """Report links to the same citation from a summary section once."""
        return self.id, self.section_title

    @cached_property
    def row(self):
        """Provide the information for this link to the report's table."""

        return (
            self.summary.id,
            self.summary.title,
            self.section_title,
            self.citation.type,
            self.citation.doc.id,
            self.citation.title,
            self.citation.publication_information,
        )

    @cached_property
    def section_title(self):
        """Title of the summary section in which this link was found."""

        parent = self.node.getparent()
        while parent is not None and parent.tag != "SummarySection":
            parent = parent.getparent()
        if parent is not None:
            return Doc.get_text(parent.find("Title"), "").strip()
        return ""

    @cached_property
    def sort_key(self):
        """Order the citation links by section title, then cite type/id."""
        return self.section_title, self.citation.type, self.citation.doc.id


class Summary:
    """PDQ Summary selected for inclusion on the report."""

    def __init__(self, control, id):
        """Remember the caller's values.

        Pass:
            control - access to the database and the report's options
            id - integer for the summary's unique CDR document ID
        """

        self.control = control
        self.id = id

    @cached_property
    def citation_links(self):
        """Sequence of `CitationLink` objects for links in this summary."""

        links = []
        keys = set()
        for node in self.doc.root.iter("CitationLink"):
            link = CitationLink(self, node)
            if link.in_scope and link.key not in keys:
                links.append(link)
                keys.add(link.key)
        return links

    @cached_property
    def doc(self):
        """`Doc` object for this CDR Summary document."""
        return Doc(self.control.session, id=self.id)

    @cached_property
    def title(self):
        """Official title of the PDQ summary."""
        return Doc.get_text(self.doc.root.find("SummaryTitle"))


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
