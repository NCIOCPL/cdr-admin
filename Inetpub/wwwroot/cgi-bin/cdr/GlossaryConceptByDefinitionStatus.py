#!/usr/bin/env python

"""Report on glossary term documents by definition statuses.
"""

from datetime import timedelta
from functools import cached_property
from lxml import etree
from cdrcgi import Controller, Reporter, BasicWebPage
from cdrapi.docs import Doc


class Control(Controller):
    """Access to report-building tools."""

    AUDIENCES = "Patient", "Health professional"
    ENGLISH = "English"
    SPANISH = "Spanish"
    STATUSES = "Approved", "New pending", "Revision pending", "Rejected"
    OPTIONS = dict(
        English=(
            ("resources", "Display Pronunciation Resources"),
            ("notes", "Display QC Notes Column"),
            ("blocked", "Include Blocked Term Name Documents"),
        ),
        Spanish=(
            ("english", "Include columns for English document information"),
            ("resources", "Display Translation Resources"),
            ("notes", "Display QC Notes Column"),
            ("blocked", "Include Blocked Term Name Documents"),
        ),
    )
    STATUS_DATE_PATHS = dict(
        English="TermDefinition/StatusDate",
        Spanish="TranslatedTermDefinition/TranslatedStatusDate",
    )
    STYLES = dict(
        Insertion="color: red;",
        Deletion="text-decoration: line-through;",
        Strong="font-weight: bold;",
        Emphasis="font-style: italic;",
        ScientificName="font-style: italic;",
    )
    ERROR = "font-weight: bold; color: red;"
    CSS = (
        'body { font-family: "Source Sans Pro Web", Arial, sans-serif; }',
        "body > div { width: 95%; margin: 2rem auto; }",
        "table { border-collapse: collapse; }",
        "table caption { font-weight: bold; padding: .25rem; }",
        "th, td { font-size: .95em; border: 1px solid black; }",
        "th { vertical-align: middle; }",
        "td { padding: .25rem; vertical-align: top; }",
        ".report-footer { font-style: italic; font-size: .9em; ",
        "                 text-align: center; }",
        "#elapsed { color: green; }",
    )

    def populate_form(self, page):
        """Add the fields to the request form.

        Pass:
            page - HTMLPage object for the form page
        """

        page.form.append(page.hidden_field("language", self.language))
        fieldset = page.fieldset("Date Range")
        opts = dict(label="Start Date", value=self.default_start)
        fieldset.append(page.date_field("start", **opts))
        opts = dict(label="End Date", value=self.default_end)
        fieldset.append(page.date_field("end", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Definition Status")
        checked = True
        for status in Control.STATUSES:
            opts = dict(value=status, label=status, checked=checked)
            fieldset.append(page.radio_button("status", **opts))
            checked = False
        page.form.append(fieldset)
        self.add_audience_fieldset(page)
        fieldset = page.fieldset("Miscellaneous Options")
        for value, label in self.OPTIONS[self.language]:
            opts = dict(value=value, label=label)
            fieldset.append(page.checkbox("opts", **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Overridden because the table is too wide for the standard layout."""

        opts = dict(caption=self.caption, columns=self.columns)
        table = self.Reporter.Table(self.rows, **opts)
        report = BasicWebPage()
        report.wrapper.append(report.B.H1(self.subtitle))
        report.wrapper.append(table.node)
        report.wrapper.append(self.footer)
        report.send()

    @cached_property
    def audience(self):
        """String for the audience selected by the user for the report."""

        default = self.AUDIENCES[0]
        audience = self.fields.getvalue("audience", default)
        if audience not in self.AUDIENCES:
            self.bail()
        return audience

    @cached_property
    def caption(self):
        """String to be displayed at the top of the table."""

        caption = f"{self.audience} Concepts With {self.status} Status"
        if self.date_range:
            return caption, self.date_range
        return caption

    @cached_property
    def columns(self):
        """Strings for headers at the top of the report's table columns."""

        columns = ["CDR ID of GTC"]
        if self.language == self.ENGLISH:
            columns.append("Term Name (Pronunciation)")
            if self.show_resources:
                columns.append("Pronun. Resource")
            columns.append("Definition")
            if self.status == "Revision pending":
                columns.append("Definition (Revision pending)")
            columns.append("Definition Resource")
        else:
            if self.include_english:
                columns.append("Term Name (EN)")
            columns.append("Term Name (ES)")
            if self.include_english:
                columns.append("Definition (EN)")
            columns.append("Definition (ES)")
            columns.append("Comment")
            if self.show_resources:
                columns.append("Translation Resource")
        if self.include_notes_column:
            columns.append(self.Reporter.Column("QC Notes", width="10rem"))
        return columns

    @cached_property
    def concepts(self):
        """Glossary term concepts selected for the report."""

        query = self.Query("query_term", "doc_id").unique()
        query.where(query.Condition("path", self.status_date_path))
        if self.start:
            query.where(query.Condition("value", self.start, ">="))
        if self.end:
            end = f"{self.end} 23:59:59"
            query.where(query.Condition("value", end, "<="))
        concepts = []
        for row in query.order("doc_id").execute(self.cursor).fetchall():
            concept = Concept(self, row.doc_id)
            if concept.in_scope:
                concepts.append(concept)
        return concepts

    @cached_property
    def date_range(self):
        """Second caption line above the table."""

        if self.start:
            if self.end:
                return f"{self.start} to {self.end}"
            else:
                return f"Since {self.start}"
        elif self.end:
            return f"Through {self.end}"
        else:
            return None

    @cached_property
    def default_end(self):
        """Default value for the end of the request form's date range."""
        return self.started.strftime("%Y-%m-%d")

    @cached_property
    def default_start(self):
        """Default value for the start of the request form's date range."""
        return (self.started - timedelta(7)).strftime("%Y-%m-%d")

    @cached_property
    def end(self):
        """End of the date range requested for the report."""

        end = self.fields.getvalue("end")
        if not end:
            return None
        try:
            return str(self.parse_date(end))
        except Exception:
            self.logger.exception(end)
            self.bail("Invalid end date string")

    @cached_property
    def include_blocked_documents(self):
        """True if we should include blocked term name documents."""
        return "blocked" in self.options

    @cached_property
    def include_english(self):
        """True if we should include information about the original document.

        Applicable only when we are running the Spanish version of the report.
        """

        return "english" in self.options

    @cached_property
    def include_notes_column(self):
        """True if we should display a QC Notes column."""
        return "notes" in self.options

    @cached_property
    def language(self):
        """String for the language selected by the user for the report."""

        language = self.fields.getvalue("language")
        if not language:
            language = self.fields.getvalue("report")
        if not language:
            language = self.LANGUAGES[0]
        if language not in self.LANGUAGES:
            self.bail()
        return language

    @cached_property
    def options(self):
        """Miscellanous options for the report."""
        return set(self.fields.getlist("opts"))

    @cached_property
    def report_type(self):
        """Lowercase string for the report's selected language."""
        return self.language.lower()

    @cached_property
    def rows(self):
        """Assemble the table rows for the report."""
        return sum([concept.rows for concept in self.concepts], start=[])

    @cached_property
    def show_resources(self):
        """True if we should display pronunciation or translation resources."""
        return "resources" in self.options

    @cached_property
    def start(self):
        """Beginning of the date range requested for the report."""

        start = self.fields.getvalue("start")
        if not start:
            return None
        try:
            return str(self.parse_date(start))
        except Exception:
            self.logger.exception(start)
            self.bail("Invalid start date string")

    @cached_property
    def status(self):
        """String for the status value selected by the user for the report."""

        status = self.fields.getvalue("status", self.STATUSES[0])
        if status not in self.STATUSES:
            self.bail()
        return status

    @cached_property
    def status_date_path(self):
        """Query term path used to find the concepts for the report."""
        return f"/GlossaryTermConcept/{self.STATUS_DATE_PATHS[self.language]}"

    @cached_property
    def subtitle(self):
        """What we display underneath the main banner."""
        return f"GTC by {self.language} Definition Status"


class Concept:
    """Top-level object for CDR glossary terms.

    Each concept has one or more definitions (for different
    languages and audiences) and possibly many names.
    """

    NAME_PATH = "/GlossaryTermName/GlossaryTermConcept/@cdr:ref"

    def __init__(self, control, doc_id):
        """Remember the caller's values.

        Pass:
            control - access to the database and the report's options
            doc_id - integer for the CDR GlossaryTermConcept document ID
        """

        self.__control = control
        self.__doc_id = doc_id

    @cached_property
    def blocked(self):
        """True if the document is blocked from publication."""
        return self.doc.active_status != Doc.ACTIVE

    @cached_property
    def control(self):
        """Access to the database and the report's options."""
        return self.__control

    @cached_property
    def doc(self):
        """`Doc` object for the CDR GlossaryTermConcept document."""
        return Doc(self.control.session, id=self.__doc_id)

    @cached_property
    def english_definition(self):
        """English definition which is in scope for the report."""

        english_definition = None
        for node in self.doc.root.findall("TermDefinition"):
            if not english_definition:
                definition = Definition(self, node)
                if definition.in_scope:
                    english_definition = definition
        return english_definition or Definition(self)

    @cached_property
    def english_name(self):
        """`Name` object for the English name selected for the report."""
        return self.name_doc.english

    @cached_property
    def english_rows(self):
        """Assemble the rows for the English version of the report."""

        row = [
            Reporter.Cell(self.doc.id, rowspan=self.rowspan, classes="nowrap"),
            self.name_docs[0].english.span,
        ]
        if self.control.show_resources:
            resources = self.name_docs[0].english.resources
            row.append(Reporter.Cell(resources, classes="break-all"))
        if self.control.status == "Revision pending":
            definition = self.name_doc.published_definition
            row.append(Reporter.Cell(definition.span, rowspan=self.rowspan))
        definition = self.english_definition
        row.append(Reporter.Cell(definition.span, rowspan=self.rowspan))
        opts = dict(rowspan=self.rowspan, classes="break-all")
        row.append(Reporter.Cell(definition.resources, **opts))
        if self.control.include_notes_column:
            row.append(Reporter.Cell("", rowspan=self.rowspan))
        rows = [row]
        for doc in self.name_docs[1:]:
            row = [doc.english.span]
            if self.control.show_resources:
                opts = dict(classes="break-all")
                row.append(Reporter.Cell(doc.english.resources, **opts))
            rows.append(row)
        return rows

    @cached_property
    def in_scope(self):
        """Should we include this concept document in the report?"""
        return getattr(self, f"{self.control.report_type}_definition").in_scope

    @cached_property
    def name_doc(self):
        """NameDoc object selected for filling in definition text placeholders.

        Pick the one with the latest publication date if possible.
        Otherwise, use the first one in the sort order for the docs.
        """

        name_doc = None
        for doc in self.name_docs:
            if doc.last_published:
                if name_doc:
                    if name_doc.last_published < doc.last_published:
                        name_doc = doc
                else:
                    name_doc = doc
        if not name_doc:
            name_doc = self.name_docs[0]
        return name_doc

    @cached_property
    def name_docs(self):
        """Sequence of `NameDoc` objects linked to this concept."""

        docs = []
        query = self.control.Query("query_term", "doc_id").unique()
        query.where(query.Condition("path", self.NAME_PATH))
        query.where(query.Condition("int_val", self.doc.id))
        for row in query.execute(self.control.cursor).fetchall():
            doc = NameDoc(self, row.doc_id)
            if self.control.include_blocked_documents or not doc.blocked:
                docs.append(doc)
        return sorted(docs) if docs else [NameDoc(self)]

    @cached_property
    def replacements(self):
        """Dictionary of nodes for filling in placeholders in definitions."""

        replacements = {}
        for node in self.doc.root.iter("ReplacementText"):
            replacements[node.get("name")] = node
        replacements.update(self.name_doc.replacements)
        return replacements

    @cached_property
    def rows(self):
        """Assemble the rows for the report."""
        return getattr(self, f"{self.control.report_type}_rows")

    @cached_property
    def rowspan(self):
        """Number of table rows in total used for this concept document."""

        if self.control.report_type == "english":
            count = len(self.name_docs)
        else:
            count = sum([len(doc.spanish) for doc in self.name_docs])
        return count if count > 1 else None

    @cached_property
    def spanish_definition(self):
        """Spanish definition which is in scope for the report."""

        spanish_definition = None
        for node in self.doc.root.findall("TranslatedTermDefinition"):
            if not spanish_definition:
                definition = Definition(self, node)
                if definition.in_scope:
                    spanish_definition = definition
        if not spanish_definition:
            spanish_definition = Definition(self)
        return spanish_definition

    @cached_property
    def spanish_name(self):
        """`NameString` object for the Spanish name selected for the report."""
        return self.name_doc.spanish[0]

    @cached_property
    def spanish_rows(self):
        """Assemble the rows for the Spanish version of the report."""

        Cell = Reporter.Cell
        row = [Cell(self.doc.id, rowspan=self.rowspan)]
        doc = self.name_docs[0]
        if self.control.include_english:
            row.append(Cell(doc.english.span, rowspan=len(doc.spanish)))
        row.append(Cell(doc.spanish[0].span))
        if self.control.include_english:
            definition = self.english_definition
            row.append(Cell(definition.span, rowspan=self.rowspan))
        definition = self.spanish_definition
        row.append(Cell(definition.span, rowspan=self.rowspan))
        row.append(Cell(definition.comment, rowspan=self.rowspan))
        if self.control.show_resources:
            opts = dict(rowspan=self.rowspan, classes="break-all")
            row.append(Cell(definition.resources, **opts))
        if self.control.include_notes_column:
            row.append(Cell("", rowspan=self.rowspan))
        spanish_rows = [row]
        for name in doc.spanish[1:]:
            spanish_rows.append([Cell(name.span)])
        for doc in self.name_docs[1:]:
            if self.control.include_english:
                spanish_rows.append([
                    Cell(doc.english.span, rowspan=len(doc.spanish)),
                    Cell(doc.spanish[0].span),
                ])
                for name in doc.spanish[1:]:
                    spanish_rows.append([Cell(name.span)])
            else:
                for name in doc.spanish:
                    spanish_rows.append([Cell(name.span)])
        return spanish_rows


class NameDoc:
    """GlossaryTermName document linked to one of the report's concepts.

    One of the English names of a CDR glossary term concept, along
    with the Spanish names associated with that English name.
    See notes on the `Name` class below.

    In the degenerate case of a concept document without any name
    documents linking to it, a dummy placeholder object will be
    created to show that the concept has no names.
    """

    def __init__(self, concept, doc_id=None):
        """Save the caller's values.

        Pass:
            concept - object for the document in which the name link was found
            doc_id - integer for the CDR ID of the GlossaryTermName document
                     (None if this is a dummy placeholder object)
        """

        self.__concept = concept
        self.__doc_id = doc_id

    def __lt__(self, other):
        """Support sorting based on the calculated name-based sort key."""
        return self.sort_key < other.sort_key

    @cached_property
    def blocked(self):
        """True if the name document may not be published."""
        return self.doc and self.doc.active_status != Doc.ACTIVE

    @cached_property
    def concept(self):
        """Object for the document in which the name link was found."""
        return self.__concept

    @cached_property
    def control(self):
        """Access to the report's options and report-creation tools."""
        return self.concept.control

    @cached_property
    def doc(self):
        """`Doc` object for the GlossaryTermName document."""

        doc = Doc(self.control.session, id=self.__doc_id)
        if not doc.id:
            return None
        if doc.title is None:
            self.control.bail(f"Name document CDR{doc.id} not found.")
        return doc

    @cached_property
    def english(self):
        """`Name` object for the document's English name."""

        if self.doc:
            node = self.doc.root.find("TermName")
            if node is not None:
                return EnglishName(self, node)
        return EnglishName(self)

    @cached_property
    def last_published(self):
        """When the name document was most recently published."""

        if not self.doc:
            return None
        query = self.control.Query("pub_proc_cg c", "p.completed")
        query.join("pub_proc p", "p.id = c.pub_proc")
        query.where(query.Condition("c.id", self.doc.id))
        rows = query.execute(self.control.cursor).fetchall()
        return rows[0].completed if rows else None

    @cached_property
    def published_definition(self):
        """The latest published English definition for the report's audience.

        Get the denormalized (that is, with placeholders replaced)
        definition from the version of the GlossaryTerm document
        we last exported to cancer.gov and our content distribution
        partners.
        """

        if self.doc:
            query = self.control.Query("pub_proc_cg", "xml")
            query.where(query.Condition("id", self.doc.id))
            rows = query.execute(self.control.cursor).fetchall()
            if rows:
                root = etree.fromstring(rows[0].xml.encode("utf-8"))
                for node in root.iter("TermDefinition"):
                    audience = Doc.get_text(node.find("Audience"))
                    if audience == self.control.audience:
                        definition = node.find("DefinitionText")
                        if definition is not None:
                            return PublishedDefinition(self, node)
        return PublishedDefinition(self)

    @cached_property
    def replacements(self):
        """Dictionary of substitutions for placeholders in the definition."""

        replacements = {}
        if self.doc:
            for node in self.doc.root.iter("ReplacementText"):
                replacements[node.get("name")] = node
        return replacements

    @cached_property
    def sort_key(self):
        """Select and normalize the name used for sorting.

        Support sorting of the names of a glossary concept,
        based on the English name string or the "first" Spanish
        name string, depending on which report we're creating.
        """

        if self.control.report_type == "english":
            name_key = self.english.sort_key
        else:
            name_key = self.spanish[0].sort_key
        return name_key, self.doc.id if self.doc else 0

    @cached_property
    def spanish(self):
        """Sequence of `TermNameString` objects for the Spanish names."""

        if self.doc:
            nodes = self.doc.root.findall("TranslatedName")
            if nodes:
                return [SpanishName(self, node) for node in nodes]
        return [SpanishName(self)]


class Name:
    """Object for a TermName or TranslatedName node.

    The CDR glossary documents have an odd structure, in order to
    meet some fairly complicated requirements. Each glossary concept
    can have one or more GlossaryTermName documents and each valid
    GlossaryTermName document will have one English name string
    and zero or more Spanish name strings. Each of those name
    strings is represented by one of these objects.
    """

    B = Reporter.Cell.B

    def __init__(self, name_doc, node=None):
        """Remember the caller's values.

        Pass:
            name_doc - `NameDoc` object in which this name was found
            node - TermName or TranslatedName node from the document
        """

        self.__name_doc = name_doc
        self.__node = node

    @cached_property
    def control(self):
        """Access to the report options and report-building tools."""
        return self.__name_doc.control

    @property
    def language(self):
        """Override in derived classes."""
        raise Exception("Must override this method")

    @cached_property
    def name_string_node(self):
        """Node from which the name's string is pulled."""
        return None if self.node is None else self.node.find("TermNameString")

    @cached_property
    def node(self):
        """TermName or TranslatedName node from the document."""
        return self.__node

    @cached_property
    def pronunciation(self):
        """String for the pronunciation of the English name."""

        if self.node is None:
            return None
        return Doc.get_text(self.node.find("TermPronunciation"), "").strip()

    @cached_property
    def resources(self):
        """Sequence of strings for pronunciation resources."""

        resources = []
        if self.node is not None:
            for node in self.node.findall("PronunciationResource"):
                resource = Doc.get_text(node, "").strip()
                if resource:
                    resources.append(resource)
        return resources

    @cached_property
    def sort_key(self):
        """Order the names on the report within the concept."""

        key = "" if self.node is None else "".join(self.node.itertext())
        return key.lower()

    @property
    def span(self):
        """String or wrapping object for what we show for the name."""

        text = self.text
        if text is None:
            return self.B.SPAN("NAME NOT FOUND", style=Control.ERROR)
        if self.control.report_type == "english":
            if self.pronunciation:
                text.tail = f" ({self.pronunciation})"
        if self.__name_doc.blocked:
            return self.B.SPAN(text, style=Control.ERROR)
        return text

    @property
    def text(self):
        """String for this term name."""
        return self.__parse(self.name_string_node)

    def __parse(self, node, with_tail=False):
        """Recursively assemble the segments of this name string.

        It's true that inline CSS rules are generally not a best
        practice, but there are bugs in Microsoft word which lose
        formatting instructions applied any other way.

        Pass:
            node - DOM node to be parsed
            with_tail - True if the node's tail should be included

        Return:
            HTML span element object (or None if node is None)
        """

        if node is None:
            return None
        pieces = []
        if node.text is not None:
            pieces = [node.text]
        for child in node.findall("*"):
            pieces.append(self.__parse(child, with_tail=True))
        span = self.B.SPAN(*pieces)
        if node.tag in Control.STYLES:
            span.set("style", Control.STYLES.get(node.tag))
        if with_tail and node.tail is not None:
            span.tail = node.tail
        return span


class EnglishName(Name):
    """Derived class which knows the language of the term name."""

    @property
    def language(self):
        """Names of this class are in English."""
        return Control.ENGLISH


class SpanishName(Name):
    """Derived class which knows the language of the term name."""

    @property
    def language(self):
        """Names of this class are in Spanish."""
        return Control.SPANISH


class Definition:
    """Definition found in a GlossaryTermConcept document.

    If the object has no node, it is being used as a dummy
    placeholder, solely to show in the report that a definition
    was not found.
    """

    B = Reporter.Cell.B
    TAGS = dict(
        English=dict(
            resource="DefinitionResource",
            status="DefinitionStatus",
            date="StatusDate",
        ),
        Spanish=dict(
            resource="TranslationResource",
            status="TranslatedStatus",
            date="TranslatedStatusDate",
        ),
    )

    def __init__(self, concept, node=None):
        """Remember the caller's values.

        Pass:
            concept - object for the document in which the definition was found
            node - block of elements with the defintion's information
                   (None for a dummy placeholder)
        """

        self.__concept = concept
        self.__node = node

    @cached_property
    def audience(self):
        """Patient or Health professional."""

        if self.__node is None:
            return None
        return Doc.get_text(self.__node.find("Audience"))

    @property
    def concept(self):
        """Object for the document in which the definition was found."""
        return self.__concept

    @property
    def control(self):
        """Access to the report's options and report-creation tools."""
        return self.concept.control

    @cached_property
    def comment(self):
        """First comment found (last entered) for the definition, if any."""

        if self.__node is not None:
            for node in self.__node.findall("Comment"):
                comment = Doc.get_text(node, "").strip()
                if comment:
                    return comment
        return ""

    @cached_property
    def in_scope(self):
        """True if this definition matches the options for the report."""

        if self.__node is None:
            return False
        if self.audience != self.control.audience:
            return False
        if self.language != self.control.language:
            return True
        if self.status != self.control.status:
            return False
        if self.control.start or not self.control.end:
            if not self.status_date:
                return False
        if self.control.start and self.control.start > self.status_date:
            return False
        if self.control.end and self.control.end < self.status_date:
            return False
        return True

    @cached_property
    def language(self):
        """English or Spanish."""

        if self.__node is None:
            return None
        return "English" if self.__node.tag == "TermDefinition" else "Spanish"

    @cached_property
    def not_found(self):
        """String displayed for a dummy definition object."""
        return f"NO {self.control.audience} DEFINITION FOUND"

    @cached_property
    def resources(self):
        """Sequence of strings for definition resources."""

        resources = []
        if self.__node is not None:
            tag = self.TAGS[self.language]["resource"]
            for node in self.__node.findall(tag):
                resources.append(Doc.get_text(node, "").strip())
        return resources

    @cached_property
    def span(self):
        """HTML wrapper for the marked-up definition display."""

        if self.__node is not None:
            span = self.__parse(self.__node.find("DefinitionText"))
            if span is not None:
                return span
        return self.B.SPAN(self.not_found, style=Control.ERROR)

    @cached_property
    def status(self):
        """String for the definition's status."""

        if self.__node is None:
            return None
        tag = self.TAGS[self.language]["status"]
        return Doc.get_text(self.__node.find(tag), "").strip()

    @cached_property
    def status_date(self):
        """String for the definition's status date."""

        if self.__node is None:
            return None
        node = self.__node.find(self.TAGS[self.language]["date"])
        return Doc.get_text(node, "").strip()

    def __parse(self, node, with_tail=False):
        """Recursively assemble the segments of this definition.

        Pass:
            node - DOM node to be parsed
            with_tail - True if the node's tail should be included

        Return:
            HTML span element object (or None if node is None)
        """

        if node is None:
            return None
        pieces = []
        if node.text is not None:
            pieces = [node.text]
        for child in node.findall("*"):
            if child.tag == "PlaceHolder":
                pieces.append(self.__resolve(child))
                if child.tail is not None:
                    pieces.append(child.tail)
            else:
                if child.tag == "Deletion":
                    if self.control.status == "Revision pending":
                        if self.control.language == Control.ENGLISH:
                            if child.tail is not None:
                                pieces.append(child.tail)
                            continue
                pieces.append(self.__parse(child, with_tail=True))
        span = self.B.SPAN(*pieces)
        if node.tag in Control.STYLES:
            span.set("style", Control.STYLES.get(node.tag))
        if with_tail and node.tail is not None:
            span.tail = node.tail
        return span

    def __resolve(self, node):
        """Replace a placeholder in the definition with an HTML span.

        Pass:
            node - object for a PlaceHolder element

        Return:
            HTML span element object containing the replacement
        """

        name = node.get("name")
        if not name:
            error = f"CDR{self.concept.doc.id}: PlaceHolder without name"
            self.control.bail(error)
        if name in ("TERMNAME", "CAPPEDTERMNAME"):
            attr_name = f"{self.language.lower()}_name"
            replacement = getattr(self.concept, attr_name).text
            if name == "CAPPEDTERMNAME" and replacement is not None:
                if replacement.text:
                    replacement.text = replacement.text.capitalize()
                else:
                    for child in replacement.iter("*"):
                        if child.text and child.tag != "Deletion":
                            child.text = child.text.capitalize()
                            break
                        elif child.tail:
                            if child.getparent().tag() != "Deletion":
                                child.tail = child.tail.capitalize()
                                break
        else:
            replacement = self.concept.replacements.get(name)
        if replacement is None:
            args = name, self.concept.doc.id, self.concept.replacements
            self.control.logger.warning("%r not found in CDR%s (%s)", *args)
            replacement = f"*** NO REPLACEMENT FOR {name!r} ***"
            span = self.B.SPAN(replacement, style=Control.ERROR)
        else:
            if not isinstance(replacement, str):
                replacement = self.__parse(replacement)
            span = self.B.SPAN(replacement, style="font-weight: bold;")
        return span


class PublishedDefinition(Definition):
    """Provides custom display for missing definition."""

    @cached_property
    def not_found(self):
        """String displayed for a dummy definition object."""
        return "NO PUBLISHED DEFINITION FOUND"


if __name__ == "__main__":
    """Only execute if loaded as a script."""
    Control().run()
