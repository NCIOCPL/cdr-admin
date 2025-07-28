#!/usr/bin/env python

"""Report on the metadata for one or more summaries.
"""

from collections import UserDict
from functools import cached_property
from cdrcgi import Controller, Reporter, BasicWebPage
from cdrapi.docs import Doc


class Control(Controller):
    """Access to the database and report-generation tools."""

    SUBTITLE = "Summary Metadata Report"
    LOGNAME = "SummaryMetadataReport"
    METHODS = (
        ("id", "Single Summary By ID"),
        ("title", "Single Summary By Title"),
        ("group", "Multiple Summaries By Group"),
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
    CSS = "../../stylesheets/SummaryMetaData.css"

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
            for value, label in self.METHODS:
                checked = value == self.selection_method
                opts = dict(value=value, label=label, checked=checked)
                fieldset.append(page.radio_button("method", **opts))
            page.form.append(fieldset)
            fieldset = page.fieldset("Enter Document ID", id="doc-id-box")
            opts = dict(label="Doc ID", value=self.doc_id)
            fieldset.append(page.text_field("doc-id", **opts))
            page.form.append(fieldset)
            opts = dict(id="doc-title-box")
            fieldset = page.fieldset("Enter Document Title", **opts)
            fieldset.set("class", "hidden usa-fieldset")
            opts = dict(value=self.fragment, label="Doc Title")
            fieldset.append(page.text_field("doc-title", **opts))
            page.form.append(fieldset)
            fieldset = page.fieldset("Summary Group", id="group-box")
            fieldset.set("class", "hidden usa-fieldset")
            opts = dict(options=self.boards, default=self.board)
            fieldset.append(page.select("board", **opts))
            opts = dict(options=self.LANGUAGES, default=self.language)
            fieldset.append(page.select("language", **opts))
            opts = dict(options=self.AUDIENCES, default=self.audience)
            fieldset.append(page.select("audience", **opts))
            opts = dict(options=self.MODULES, default=self.modules)
            fieldset.append(page.select("modules", **opts))
            page.form.append(fieldset)
            page.form.append(self.item_fields)
            page.head.append(page.B.SCRIPT(src=self.SCRIPT))

    def show_report(self):
        """Overridden because the table is too wide for the standard layout."""

        if not self.ready:
            self.show_form()
        report = BasicWebPage()
        report.wrapper.append(report.B.H1(self.subtitle))
        for table in self.tables:
            report.wrapper.append(table.node)
        report.wrapper.append(self.footer)
        report.page.head.append(report.B.LINK(href=self.CSS, rel="stylesheet"))
        report.send()

    @cached_property
    def audience(self):
        """Selecting health-professional or patient summaries?"""

        audience = self.fields.getvalue("audience")
        if audience and audience not in self.AUDIENCES:
            self.bail()
        return audience

    @cached_property
    def board(self):
        """CDR Organization document ID for the selected PDQ board."""

        board = self.fields.getvalue("board")
        if board:
            try:
                board = int(board)
                if board not in self.boards:
                    self.bail()
            except Exception:
                self.bail()
        return board

    @cached_property
    def board_names(self):
        """Dictionary of all board names (advisory and editorial)."""

        query = self.Query("query_term", "doc_id", "value")
        query.where(query.Condition("path", Control.ORG_NAME_PATH))
        rows = query.execute(self.cursor).fetchall()
        return dict([tuple(row) for row in rows])

    @cached_property
    def boards(self):
        """Dictionary of ID -> editorial board name (for the picklist)."""
        return self.get_boards()

    @cached_property
    def diagnoses(self):
        """Cached diagnosis term lookup."""

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
        return Diagnoses(self)

    @cached_property
    def doc_id(self):
        """CDR ID (integer) for document on which we are to report."""

        doc_id = self.fields.getvalue("doc-id")
        if doc_id:
            try:
                doc_id = Doc.extract_id(doc_id)
            except Exception:
                self.bail("Invalid document ID")
        return doc_id

    @cached_property
    def fragment(self):
        """Document title fragment string."""
        return self.fields.getvalue("doc-title", "").strip()

    @cached_property
    def item_fields(self):
        """Factored out for use on the cascading title selection form."""

        fieldset = self.HTMLPage.fieldset("Include On Report")
        for item in self.LABELS:
            opts = dict(value=item, label=item, checked=item in self.items)
            fieldset.append(self.HTMLPage.checkbox("items", **opts))
        return fieldset

    @cached_property
    def items(self):
        """What fields should be included on the report?"""

        items = set(self.fields.getlist("items"))
        if not items:
            items = self.DEFAULTS
        if items - set(self.LABELS):
            self.bail()
        return items

    @cached_property
    def language(self):
        """Selecting English or Spanish summaries?"""

        language = self.fields.getvalue("language")
        if language and language not in self.LANGUAGES:
            self.bail()
        return language

    @cached_property
    def modules(self):
        """How to handle modules in summary selection."""

        modules = self.fields.getvalue("modules", "both")
        if modules not in [m[0] for m in self.MODULES]:
            self.bail()
        return modules

    @cached_property
    def ready(self):
        """True if we have everything we need for the report."""

        if not self.request:
            return False
        match self.selection_method:
            case "id":
                if not self.doc_id:
                    message = "Document ID is required."
                    self.alerts.append(dict(message=message, type="error"))
                    return False
                try:
                    doc = Doc(self.session, id=self.doc_id)
                    if doc.doctype.name != "Summary":
                        message = f"CDR{doc.id} is a {doc.doctype} document."
                        alert = dict(message=message, type="warning")
                        self.alerts.append(alert)
                        return False
                except Exception:
                    message = f"Unable to find document {self.doc_id}."
                    self.logger.exception(message)
                    self.alerts.append(dict(message=message, type="error"))
                    return False
                return True
            case "title":
                if not self.fragment:
                    message = "Title fragment is required."
                    self.alerts.append(dict(message=message, type="error"))
                    return False
                if not self.titles:
                    message = f"No summaries match {self.fragment!r}."
                    self.alerts.append(dict(message=message, type="warning"))
                return len(self.titles) == 1
            case "group":
                missing = []
                for field in "Board", "Language", "Audience":
                    if not getattr(self, field.lower()):
                        missing.append(field)
                        message = f"{field} not selected."
                        self.alerts.append(dict(message=message, type="error"))
                if missing:
                    return False
                if self.summaries:
                    return True
                message = "No summaries match the filtering criteria."
                self.alerts.append(dict(message=message, type="warning"))
                return False
            case _:
                self.bail()

    @cached_property
    def same_window(self):
        """Control when a new browser tab is opened."""
        return [self.SUBMIT] if self.request else []

    @cached_property
    def selection_method(self):
        """What method are we using to choose summaries?"""

        method = self.fields.getvalue("method") or "id"
        if method not in [m[0] for m in self.METHODS]:
            self.bail()
        return method

    @cached_property
    def subtitle(self):
        """What should we display underneath the main banner?"""

        if self.request == self.SUBMIT:
            if self.titles and len(self.titles) > 1:
                return "Multiple Matching Summaries Found"
            elif self.summaries:
                if len(self.summaries) == 1:
                    s = self.summaries[0]
                    return f"{s.title} (CDR{s.id:d})"
                else:
                    board_name = self.boards[self.board]
                    args = self.language, self.audience, board_name
                    return "{} {} Summaries for {}".format(*args)
        return self.SUBTITLE

    @cached_property
    def summaries(self):
        """Which summaries should be represented on the report?"""

        if self.selection_method == "id":
            return [Summary(self, self.doc_id)] if self.doc_id else []
        if self.selection_method == "title":
            if self.titles and len(self.titles) == 1:
                id, title = self.titles[0]
                return [Summary(self, id)]
            return []
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
        return [Summary(self, row.id) for row in rows]

    @cached_property
    def tables(self):
        """Get each summary to assemble its table(s)."""

        if not self.summaries:
            self.bail("No summaries found for report")
        tables = []
        for summary in self.summaries:
            tables += summary.tables
        return tables

    @cached_property
    def titles(self):
        """Find summaries whose titles match the user's title fragment."""

        if self.selection_method == "title" and self.fragment:
            pattern = f"%{self.fragment}%"
            query = self.Query("active_doc d", "d.id", "d.title")
            query.join("doc_type t", "t.id = d.doc_type")
            query.where(query.Condition("t.name", "Summary"))
            query.where(query.Condition("d.title", pattern, "LIKE"))
            query.order("d.title")
            rows = query.execute(self.cursor).fetchall()
            if rows:
                return [tuple(row) for row in rows]
        return None


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

        self.control = control
        self.id = doc_id

    @cached_property
    def abstract(self):
        """Sequence of strings (without markup) for abstract paragraphs."""

        abstract = []
        path = "SummaryMetaData/SummaryAbstract/Para"
        for node in self.doc.root.findall(path):
            abstract.append(Doc.get_text(node, "").strip())
        return abstract

    @cached_property
    def advisory_board(self):
        """String for the name of the advisory board for this PDQ summary."""

        for name in self.boards:
            if "advisory" in name.lower():
                return name
        return None

    @cached_property
    def audience(self):
        """Patients or Health professionals."""

        node = self.doc.root.find("SummaryMetaData/SummaryAudience")
        return Doc.get_text(node)

    @cached_property
    def available_as_module(self):
        """Can this summary be used as a module?"""
        return self.doc.root.get("AvailableAsModule") == "Yes"

    @cached_property
    def boards(self):
        """Names of the boards which manage this PDQ summary."""

        boards = []
        path = "SummaryMetaData/PDQBoard/Board"
        for node in self.doc.root.findall(path):
            ref = node.get(self.CDR_REF)
            try:
                name = self.control.board_names[Doc.extract_id(ref)]
                if name:
                    boards.append(name)
            except Exception:
                message = "%s: No board name for %r"
                args = self.doc.cdr_id, ref
                self.control.logger.exception(message, *args)
        return boards

    @cached_property
    def description(self):
        """String for the description of the summary (stripped of markup)."""

        node = self.doc.root.find("SummaryMetaData/SummaryDescription")
        return Doc.get_text(node)

    @cached_property
    def doc(self):
        """`Doc` object for this PDQ summary document."""
        return Doc(self.control.session, id=self.id)

    @cached_property
    def editorial_board(self):
        """String for the name of the editorial board for this PDQ summary."""

        for name in self.boards:
            if "advisory" not in name.lower():
                return name
        return None

    @cached_property
    def general_table(self):
        """Add the top-level metadata for the PDQ summary."""

        rows = []
        for label, name in Control.ITEMS:
            if name and label in self.control.items:
                rows.append((label, getattr(self, name)))
        return Reporter.Table(rows, classes="general")

    @cached_property
    def keywords(self):
        """Sequence of strings for keywords associated with this summary."""

        keywords = []
        path = "SummaryMetaData/SummaryKeyWords/SummaryKeyWord"
        for node in self.doc.root.findall(path):
            keywords.append(Doc.get_text(node, "").strip())
        return keywords

    @cached_property
    def language(self):
        """English or Spanish."""

        node = self.doc.root.find("SummaryMetaData/SummaryLanguage")
        return Doc.get_text(node)

    @cached_property
    def link(self):
        """URL and accompanying label for this PDQ summary."""

        node = self.doc.root.find("SummaryMetaData/SummaryURL")
        return self.Link(node)

    @cached_property
    def pmid(self):
        """PubMed ID for the PDQ summary on NLM's web site."""

        node = self.doc.root.find("SummaryMetaData/PMID")
        return Doc.get_text(node)

    @cached_property
    def pretty_url(self):
        """Link to this PDQ summary."""
        return self.link.span

    @cached_property
    def purpose(self):
        """String for the purpose of this PDQ summary (stripped of markup)."""

        node = self.doc.root.find("SummaryMetaData/PurposeText")
        return Doc.get_text(node)

    @cached_property
    def section_metadata_table(self):
        """Table showing information about the sections of this PDQ summary."""

        if "Section Metadata" not in self.control.items:
            return None
        rows = [section.row for section in self.sections if section.row]
        opts = dict(columns=self.COLUMNS)
        return Reporter.Table(rows, **opts)

    @cached_property
    def sections(self):
        """Find all the sections of the summary recursively."""

        sections = []
        for node in self.doc.root.iter("SummarySection"):
            sections.append(self.Section(self.control, node))
        return sections

    @cached_property
    def tables(self):
        """Table(s) for this PDQ summary on the report."""

        tables = self.general_table, self.section_metadata_table
        return [table for table in tables if table]

    @cached_property
    def title(self):
        """String for the title of the summary (stripped of markup)."""

        title = Doc.get_text(self.doc.root.find("SummaryTitle"))
        if self.available_as_module:
            title += " [module]"
        return title

    @cached_property
    def topics(self):
        """Sequence of topics strings for this PDQ summary."""

        topics = []
        for tag in "MainTopics", "SecondaryTopics":
            path = f"SummaryMetaData/{tag}/Term"
            for node in self.doc.root.findall(path):
                topic = Doc.get_text(node, "").strip()
                if topic:
                    topics.append(f"{topic} ({tag[0]})")
        return topics

    @cached_property
    def type(self):
        """String for the type of this summary."""

        node = self.doc.root.find("SummaryMetaData/SummaryType")
        return Doc.get_text(node)

    class Section:
        """Nested class for all the sections of the summary."""

        CHECK_MARK = "\N{HEAVY CHECK MARK}"

        def __init__(self, control, node):
            """Remember the caller's values.

            Pass:
                control - provides cached diagnosis term name lookup
                node - location of this summary section in the summary doc
            """

            self.control = control
            self.node = node

        @cached_property
        def depth(self):
            """How deep is this section in the summary document?"""
            return len(self.path.split("/"))

        @cached_property
        def diagnoses(self):
            """Sequence of diagnosis term strings applied to this section."""

            diagnoses = []
            for node in self.node.findall("SectMetaData/Diagnosis"):
                ref = node.get(Summary.CDR_REF)
                try:
                    id = Doc.extract_id(ref)
                    name = self.control.diagnoses[id]
                    if not name:
                        name = f"diagnosis lookup failure for {ref!r}"
                except Exception:
                    self.control.logger.exception("%s lookup", ref)
                    name = f"diagnosis lookup failure for {ref!r}"
                diagnoses.append(name)
            return diagnoses

        @cached_property
        def in_scope(self):
            """Does this section have anything to contribute to the report?"""

            if self.needs_search_string:
                return True
            if self.diagnoses or self.types or self.title:
                return True
            return False

        @cached_property
        def needs_search_string(self):
            """True if the TrialSearchString attribute's value is 'No'."""
            return self.node.get("TrialSearchString") == "No"

        @cached_property
        def path(self):
            """String for where this section lives in the summary document."""
            return self.node.getroottree().getpath(self.node)

        @cached_property
        def row(self):
            """Optional sequence of values for this section."""

            if not self.in_scope:
                return None
            check_mark = self.CHECK_MARK if self.needs_search_string else ""
            level = {3: "top", 4: "mid"}.get(self.depth, "low")
            return (
                Reporter.Cell(self.title, classes=f"{level}-section"),
                "; ".join(self.diagnoses),
                Reporter.Cell(check_mark, center=True),
                "; ".join(self.types),
            )

        @cached_property
        def title(self):
            """String for this summary section's title."""
            return Doc.get_text(self.node.find("Title"))

        @cached_property
        def types(self):
            """Sequence of strings for the section's types."""

            types = []
            for node in self.node.findall("SectMetaData/SectionType"):
                types.append(Doc.get_text(node))
            return types

    class Link:
        """Holds the label and URL for the summary link."""

        def __init__(self, node):
            """Save the node for this summary's URL.

            Pass:
                node - element from the XML summary document
            """

            self.node = node

        @cached_property
        def span(self):
            """What to show in the table for this summary's URL."""

            if self.node is not None and self.node.text:
                B = Reporter.Cell.B
                url = self.node.get(f"{{{Doc.NS}}}xref")
                link = B.A(url, href=url)
                return B.SPAN(self.node.text, B.BR(), link)
            return None


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""

    control = Control()
    try:
        control.run()
    except Exception as e:
        control.logger.exception("failure")
        control.bail(e)
