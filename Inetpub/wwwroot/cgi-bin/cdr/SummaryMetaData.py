#!/usr/bin/env python

"""Report on the metadata for one or more summaries.
"""

from collections import UserDict
from cdrcgi import Controller, Reporter
from cdrapi.docs import Doc


class Control(Controller):
    """Access to the database and report-generation tools."""

    SUBTITLE = "Summary Metadata Report"
    LOGNAME = "SummaryMetadataReport"
    METHODS = (
        ("id", "Single Summary By ID", True),
        ("title", "Single Summary By Title", False),
        ("group", "Multiple Summaries By Group", False),
    )
    A_PATH = "a.path = '/Summary/SummaryMetaData/SummaryAudience'"
    B_PATH = "b.path = '/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref'"
    L_PATH = "l.path = '/Summary/SummaryMetaData/SummaryLanguage'"
    M_PATH = "m.path = '/Summary/@AvailableAsModule'"
    T_PATH = "t.path = '/Summary/TranslationOf/@cdr:ref'"
    ITEMS = (
        ("CDR ID", "id"),
        ("Summary Title", "title"),
        ("Advisory Board", "advisory_board"),
        ("Editorial Board", "editorial_board"),
        ("Audience", "audience"),
        ("Language", "language"),
        ("Description", "description"),
        ("Pretty URL", "pretty_url"),
        ("Topics", "topics"),
        ("Purpose Text", "purpose"),
        ("Section Metadata", None),
        ("Summary Abstract", "abstract"),
        ("Summary Keywords", "keywords"),
        ("PMID", "pmid"),
    )
    LABELS = [item[0] for item in ITEMS]
    DEFAULTS = {
        "CDR ID",
        "Summary Title",
        "Advisory Board",
        "Editorial Board",
        "Topics"
    }
    MODULES = (
        ("both", "Summaries and Modules"),
        ("summaries", "Summaries Only"),
        ("modules", "Modules Only"),
    )
    ORG_NAME_INFO = "/Organization/OrganizationNameInformation"
    ORG_NAME_PATH = f"{ORG_NAME_INFO}/OfficialName/Name"
    SCRIPT = "../../js/SummaryMetaData.js"
    STYLESHEET = "../../stylesheets/SummaryMetaData.css"

    def build_tables(self):
        """Get each summary to assemble its table(s)."""

        if not self.summaries:
            cdrcgi.bail("No summaries found for report")
        tables = []
        for summary in self.summaries:
            tables += summary.tables
        return tables

    def populate_form(self, page):
        """Add the fields to the form.

        Pass:
            page - HTMLPage object containing the form
        """

        if self.titles:
            page.form.append(page.hidden_field("method", "id"))
            fieldset = page.fieldset("Choose Summary")
            opts = dict(label="Summary", options=self.titles)
            fieldset.append(page.select("doc-id", **opts))
            page.form.append(fieldset)
            page.form.append(self.item_fields)
        else:
            fieldset = page.fieldset("Summary Selection Method")
            for value, label, checked in self.METHODS:
                opts = dict(value=value, label=label, checked=checked)
                fieldset.append(page.radio_button("method", **opts))
            page.form.append(fieldset)
            fieldset = page.fieldset("Enter Document ID", id="doc-id-box")
            fieldset.append(page.text_field("doc-id", label="Doc ID"))
            page.form.append(fieldset)
            fieldset = page.fieldset("Enter Document Title", id="doc-title-box")
            fieldset.set("class", "hidden")
            fieldset.append(page.text_field("doc-title", label="Doc Title"))
            page.form.append(fieldset)
            fieldset = page.fieldset("Summary Group", id="group-box")
            fieldset.set("class", "hidden")
            fieldset.append(page.select("board", options=self.boards))
            fieldset.append(page.select("language", options=self.LANGUAGES))
            fieldset.append(page.select("audience", options=self.AUDIENCES))
            fieldset.append(page.select("modules", options=self.MODULES))
            page.form.append(fieldset)
            page.form.append(self.item_fields)
            page.head.append(page.B.SCRIPT(src=self.SCRIPT))

    def show_report(self):
        """Add some custom CSS styling."""

        page = self.report.page
        elapsed = page.html.get_element_by_id("elapsed", None)
        if elapsed is not None:
            elapsed.text = str(self.elapsed)
        page.head.append(page.B.LINK(href=self.STYLESHEET, rel="stylesheet"))
        self.report.send(self.format)

    @property
    def audience(self):
        """Selecting health-professional or patient summaries?"""

        if not hasattr(self, "_audience"):
            self._audience = self.fields.getvalue("audience")
            if self._audience and self._audience not in self.AUDIENCES:
                self.bail()
        return self._audience

    @property
    def board(self):
        """CDR Organization document ID for the selected PDQ board."""

        if not hasattr(self, "_board"):
            self._board = self.fields.getvalue("board")
            if self._board:
                try:
                    self._board = int(self._board)
                    if self._board not in self.boards:
                        self.bail()
                except Exception:
                    self.bail()
        return self._board

    @property
    def board_names(self):
        """Dictionary of all board names (advisory and editorial)."""

        if not hasattr(self, "_board_names"):
            query = self.Query("query_term", "doc_id", "value")
            query.where(query.Condition("path", Control.ORG_NAME_PATH))
            rows = query.execute(self.cursor).fetchall()
            self._board_names = dict([tuple(row) for row in rows])
        return self._board_names

    @property
    def boards(self):
        """Dictionary of ID -> editorial board name (for the picklist)."""

        if not hasattr(self, "_boards"):
            self._boards = self.get_boards()
        return self._boards

    @property
    def diagnoses(self):
        """Cached diagnosis term lookup."""

        if not hasattr(self, "_diagnoses"):
            class Diagnoses(UserDict):
                def __init__(self, control):
                    self.__control = control
                    UserDict.__init__(self)
                def __getitem__(self, key):
                    if key not in self.data:
                        query = self.__control.Query("query_term", "value")
                        query.where("path = '/Term/PreferredName'")
                        query.where(query.Condition("doc_id", key))
                        rows = query.execute(self.__control.cursor).fetchall()
                        self.data[key] = rows[0][0] if rows else ""
                    return self.data[key]
            self._diagnoses = Diagnoses(self)
        return self._diagnoses

    @property
    def doc_id(self):
        """CDR ID (integer) for document on which we are to report."""

        if not hasattr(self, "_doc_id"):
            self._doc_id = self.fields.getvalue("doc-id")
            if self._doc_id:
                try:
                    self._doc_id = Doc.extract_id(self._doc_id)
                except Exception:
                    self.bail("Invalid document ID")
        return self._doc_id

    @property
    def fragment(self):
        """Document title fragment string."""

        if not hasattr(self, "_fragment"):
            self._fragment = self.fields.getvalue("doc-title", "").strip()
        return self._fragment

    @property
    def item_fields(self):
        """Factored out for use on the cascading title selection form."""

        fieldset = self.HTMLPage.fieldset("Include On Report")
        for item in self.LABELS:
            opts = dict(value=item, label=item, checked=item in self.items)
            fieldset.append(self.HTMLPage.checkbox("items", **opts))
        return fieldset

    @property
    def items(self):
        """What fields should be included on the report?"""

        if not hasattr(self, "_items"):
            self._items = set(self.fields.getlist("items"))
            if not self._items:
                self._items = self.DEFAULTS
            if self._items - set(self.LABELS):
                self.bail()
        return self._items

    @property
    def language(self):
        """Selecting English or Spanish summaries?"""

        if not hasattr(self, "_language"):
            self._language = self.fields.getvalue("language")
            if self._language and self._language not in self.LANGUAGES:
                self.bail()
        return self._language

    @property
    def method(self):
        """What method are we using to choose summaries?"""

        if not hasattr(self, "_method"):
            self._method = self.fields.getvalue("method") or "id"
            if self._method not in [m[0] for m in self.METHODS]:
                self.bail()
        return self._method

    @property
    def modules(self):
        """How to handle modules in summary selection."""

        if not hasattr(self, "_modules"):
            self._modules = self.fields.getvalue("modules", "both")
            if self._modules not in [m[0] for m in self.MODULES]:
                self.bail()
        return self._modules

    @property
    def subtitle(self):
        """What should we display underneath the main banner?"""

        if not hasattr(self, "_subtitle"):
            if self.request == self.SUBMIT:
                if self.titles and len(self.titles) > 1:
                    self._subtitle = "Multiple Matching Summaries Found"
                elif self.summaries:
                    if len(self.summaries) == 1:
                        s = self.summaries[0]
                        self._subtitle = f"{s.title} (CDR{s.id:d})"
                    else:
                        board_name = self.boards[self.board]
                        args = self.language, self.audience, board_name
                        self._subtitle = "{} {} Summaries for {}".format(*args)
            else:
                self._subtitle = self.SUBTITLE
        return self._subtitle

    @property
    def summaries(self):
        """Which summaries should be represented on the report?"""

        if not hasattr(self, "_summaries"):
            self._summaries = []
            if self.method == "id":
                if self.doc_id:
                    self._summaries = [Summary(self, self.doc_id)]
            elif self.method == "title":
                if self.titles:
                    if len(self.titles) == 1:
                        id, title = self.titles[0]
                        self._summaries = [Summary(self, id)]
                    else:
                        self.show_form()
            elif self.method == "group":
                if not self.board:
                    self.bail("Board not selected")
                if not self.language:
                    self.bail("Language not selected")
                if not self.audience:
                    self.bail("Audience not selected")
                query = self.Query("active_doc d", "d.id", "d.title").unique()
                query.join("publishable_version v", "v.id = d.id")
                query.join("query_term a", "a.doc_id = d.id")
                query.join("query_term l", "l.doc_id = d.id")
                if self.language == "English":
                    query.join("query_term b", "b.doc_id = d.id")
                else:
                    query.join("query_term t", "t.doc_id = d.id")
                    query.where(self.T_PATH)
                    query.join("query_term b", "b.doc_id = t.int_val")
                query.where(self.A_PATH)
                query.where(self.L_PATH)
                query.where(self.B_PATH)
                query.where(query.Condition("a.value", f"{self.audience}s"))
                query.where(query.Condition("b.int_val", self.board))
                query.where(query.Condition("l.value", self.language))
                if self.modules == "modules":
                    query.join("query_term m", "m.doc_id = d.id")
                    query.where(self.M_PATH)
                elif self.modules == "summaries":
                    query.outer("query_term m", "m.doc_id = d.id", self.M_PATH)
                    query.where("m.doc_id IS NULL")
                query.order("d.title")
                rows = query.execute(self.cursor).fetchall()
                self._summaries = [Summary(self, row.id) for row in rows]
        return self._summaries

    @property
    def titles(self):
        """Find summaries whose titles match the user's title fragment."""

        if not hasattr(self, "_titles"):
            self._titles = None
            if self.method == "title" and self.fragment:
                pattern = f"%{self.fragment}%"
                query = self.Query("active_doc d", "d.id", "d.title")
                query.join("doc_type t", "t.id = d.doc_type")
                query.where(query.Condition("t.name", "Summary"))
                query.where(query.Condition("d.title", pattern, "LIKE"))
                query.order("d.title")
                rows = query.execute(self.cursor).fetchall()
                if rows:
                    self._titles = [tuple(row) for row in rows]
        return self._titles


class Summary:
    """One of these for each PDQ summary on the report."""

    CDR_REF = f"{{{Doc.NS}}}ref"
    COLUMNS = (
        Reporter.Column("Section Title"),
        Reporter.Column("Diagnoses"),
        Reporter.Column("SS\N{NO-BREAK SPACE}No"),
        Reporter.Column("Section Type"),
    )

    def __init__(self, control, doc_id):
        """Remember the caller's values.

        Pass:
            control - access to the login session and table-building tools
            doc_id - integer for the unique CDR document ID for the summary
        """

        self.__control = control
        self.__doc_id = doc_id

    @property
    def abstract(self):
        """Sequence of strings (without markup) for abstract paragraphs."""

        if not hasattr(self, "_abstract"):
            self._abstract = []
            path = "SummaryMetaData/SummaryAbstract/Para"
            for node in self.doc.root.findall(path):
                self._abstract.append(Doc.get_text(node, "").strip())
        return self._abstract

    @property
    def advisory_board(self):
        """String for the name of the advisory board for this PDQ summary."""

        if not hasattr(self, "_advisory_board"):
            self._advisory_board = None
            for name in self.boards:
                if "advisory" in name.lower():
                    self._advisory_board = name
                    break
        return self._advisory_board

    @property
    def audience(self):
        """Patients or Health professionals."""

        if not hasattr(self, "_audience"):
            node = self.doc.root.find("SummaryMetaData/SummaryAudience")
            self._audience = Doc.get_text(node)
        return self._audience

    @property
    def available_as_module(self):
        """Can this summary be used as a module?"""
        return self.doc.root.get("AvailableAsModule") == "Yes"

    @property
    def boards(self):
        """Names of the boards which manage this PDQ summary."""

        if not hasattr(self, "_boards"):
            self._boards = []
            path = "SummaryMetaData/PDQBoard/Board"
            for node in self.doc.root.findall(path):
                ref = node.get(self.CDR_REF)
                try:
                    name = self.control.board_names[Doc.extract_id(ref)]
                    if name:
                        self._boards.append(name)
                except Exception:
                    message = "%s: No board name for %r"
                    args = self.doc.cdr_id, ref
                    self.control.logger.exception(message, *args)
        return self._boards

    @property
    def control(self):
        """Access to the login session and table-building tools."""
        return self.__control

    @property
    def description(self):
        """String for the description of the summary (stripped of markup)."""

        if not hasattr(self, "_description"):
            node = self.doc.root.find("SummaryMetaData/SummaryDescription")
            self._description = Doc.get_text(node)
        return self._description

    @property
    def doc(self):
        """`Doc` object for this PDQ summary document."""
        if not hasattr(self, "_doc"):
            self._doc = Doc(self.control.session, id=self.id)
        return self._doc

    @property
    def editorial_board(self):
        """String for the name of the editorial board for this PDQ summary."""

        if not hasattr(self, "_editorial_board"):
            self._editorial_board = None
            for name in self.boards:
                if "advisory" not in name.lower():
                    self._editorial_board = name
                    break
        return self._editorial_board

    @property
    def general_table(self):
        """Add the top-level metadata for the PDQ summary."""

        if not hasattr(self, "_general_table"):
            rows = []
            for label, name in Control.ITEMS:
                if name and label in self.control.items:
                    rows.append((label, getattr(self, name)))
            self._general_table = Reporter.Table(rows, classes="general")
        return self._general_table

    @property
    def id(self):
        """Integer for the unique CDR document ID for this PDQ summary."""
        return self.__doc_id

    @property
    def keywords(self):
        """Sequence of strings for keywords associated with this summary."""

        if not hasattr(self, "_keywords"):
            self._keywords = []
            path = "SummaryMetaData/SummaryKeyWords/SummaryKeyWord"
            for node in self.doc.root.findall(path):
                self._keywords.append(Doc.get_text(node, "").strip())
        return self._keywords

    @property
    def language(self):
        """English or Spanish."""

        if not hasattr(self, "_language"):
            node = self.doc.root.find("SummaryMetaData/SummaryLanguage")
            self._language = Doc.get_text(node)
        return self._language

    @property
    def link(self):
        """URL and accompanying label for this PDQ summary."""

        if not hasattr(self, "_link"):
            node = self.doc.root.find("SummaryMetaData/SummaryURL")
            self._link = self.Link(node)
        return self._link

    @property
    def pmid(self):
        """PubMed ID for the PDQ summary on NLM's web site."""

        if not hasattr(self, "_pmid"):
            node = self.doc.root.find("SummaryMetaData/PMID")
            self._pmid = Doc.get_text(node)
        return self._pmid

    @property
    def pretty_url(self):
        """Link to this PDQ summary."""
        return self.link.span

    @property
    def purpose(self):
        """String for the purpose of this PDQ summary (stripped of markup)."""

        if not hasattr(self, "_purpose"):
            node = self.doc.root.find("SummaryMetaData/PurposeText")
            self._purpose = Doc.get_text(node)
        return self._purpose

    @property
    def section_metadata_table(self):
        """Table showing information about the sections of this PDQ summary."""

        if not hasattr(self, "_section_metadata_table"):
            if "Section Metadata" not in self.control.items:
                self._section_meta_data = None
                return None
            rows = [section.row for section in self.sections if section.row]
            opts = dict(columns=self.COLUMNS)
            self._section_metadata_table = Reporter.Table(rows, **opts)
        return self._section_metadata_table

    @property
    def sections(self):
        """Find all the sections of the summary recursively."""

        if not hasattr(self, "_sections"):
            self._sections = []
            for node in self.doc.root.iter("SummarySection"):
                self._sections.append(self.Section(self.control, node))
        return self._sections

    @property
    def tables(self):
        """Table(s) for this PDQ summary on the report."""

        if not hasattr(self, "_tables"):
            tables = self.general_table, self.section_metadata_table
            self._tables = [table for table in tables if table]
        return self._tables

    @property
    def title(self):
        """String for the title of the summary (stripped of markup)."""

        if not hasattr(self, "_title"):
            self._title = Doc.get_text(self.doc.root.find("SummaryTitle"))
            if self.available_as_module:
                self._title += " [module]"
        return self._title

    @property
    def topics(self):
        """Sequence of topics strings for this PDQ summary."""

        if not hasattr(self, "_topics"):
            self._topics = []
            for tag in "MainTopics", "SecondaryTopics":
                path = f"SummaryMetaData/{tag}/Term"
                for node in self.doc.root.findall(path):
                    topic = Doc.get_text(node, "").strip()
                    if topic:
                        self._topics.append(f"{topic} ({tag[0]})")
        return self._topics

    @property
    def type(self):
        """String for the type of this summary."""

        if not hasattr(self, "_type"):
            node = self.doc.root.find("SummaryMetaData/SummaryType")
            self._type = Doc.get_text(node)
        return self._type


    class Section:
        """Nested class for all the sections of the summary."""

        CHECK_MARK = "\N{HEAVY CHECK MARK}"

        def __init__(self, control, node):
            """Remember the caller's values.

            Pass:
                control - provides cached diagnosis term name lookup
                node - location of this summary section in the summary doc
            """

            self.__control = control
            self.__node = node

        @property
        def depth(self):
            """How deep is this section in the summary document?"""

            if not hasattr(self, "_depth"):
                self._depth = len(self.path.split("/"))
            return self._depth

        @property
        def diagnoses(self):
            """Sequence of diagnosis term strings applied to this section."""

            if not hasattr(self, "_diagnoses"):
                self._diagnoses = []
                for node in self.__node.findall("SectMetaData/Diagnosis"):
                    ref = node.get(Summary.CDR_REF)
                    try:
                        id = Doc.extract_id(ref)
                        name = self.__control.diagnoses[id]
                        if not name:
                            name = f"diagnosis lookup failure for {ref!r}"
                    except Exception:
                        self.__control.logger.exception("%s lookup", ref)
                        name = f"diagnosis lookup failure for {ref!r}"
                    self._diagnoses.append(name)
            return self._diagnoses

        @property
        def in_scope(self):
            """Does this section have anything to contribute to the report?"""

            if not hasattr(self, "_in_scope"):
                self._in_scope = False
                if self.needs_search_string:
                    self._in_scope = True
                elif self.diagnoses or self.types or self.title:
                    self._in_scope = True
            return self._in_scope

        @property
        def needs_search_string(self):
            """True if the TrialSearchString attribute's value is 'No'."""

            if not hasattr(self, "_needs_search_string"):
                value = self.__node.get("TrialSearchString")
                self._needs_search_string = value == "No"
            return self._needs_search_string

        @property
        def path(self):
            """String for where this section lives in the summary document."""

            if not hasattr(self, "_path"):
                self._path = self.__node.getroottree().getpath(self.__node)
            return self._path

        @property
        def row(self):
            """Optional sequence of values for this section."""

            if not hasattr(self, "_row"):
                self._row = None
                if self.in_scope:
                    check_mark = ""
                    if self.needs_search_string:
                        check_mark = self.CHECK_MARK
                    level = {3: "top", 4: "mid"}.get(self.depth, "low")
                    self._row = (
                        Reporter.Cell(self.title, classes=f"{level}-section"),
                        "; ".join(self.diagnoses),
                        Reporter.Cell(check_mark, center=True),
                        "; ".join(self.types),
                    )
            return self._row

        @property
        def title(self):
            """String for this summary section's title."""

            if not hasattr(self, "_title"):
                self._title = Doc.get_text(self.__node.find("Title"))
            return self._title

        @property
        def types(self):
            """Sequence of strings for the section's types."""

            if not hasattr(self, "_types"):
                self._types = []
                for node in self.__node.findall("SectMetaData/SectionType"):
                    self._types.append(Doc.get_text(node))
            return self._types


    class Link:
        """Holds the label and URL for the summary link."""

        def __init__(self, node):
            """Save the node for this summary's URL.

            Pass:
                node - element from the XML summary document
            """

            self.__node = node

        @property
        def span(self):
            """What to show in the table for this summary's URL."""

            if not hasattr(self, "_span"):
                self._span = None
                if self.__node is not None and self.__node.text:
                    B = Reporter.Cell.B
                    url = self.__node.get(f"{{{Doc.NS}}}xref")
                    link = B.A(url, href=url)
                    self._span = B.SPAN(self.__node.text, B.BR(), link)
            return self._span


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
