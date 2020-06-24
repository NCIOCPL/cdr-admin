#!/usr/bin/env python

"""Report on glossary term documents by definition statuses.
"""

from datetime import timedelta
from lxml import etree
from cdrcgi import Controller, Reporter
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

    def build_tables(self):
        """Assemble the table for the report."""

        opts = dict(caption=self.caption, columns=self.columns)
        return Reporter.Table(self.rows, **opts)

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

    @property
    def audience(self):
        """String for the audience selected by the user for the report."""

        if not hasattr(self, "_audience"):
            default = self.AUDIENCES[0]
            self._audience = self.fields.getvalue("audience", default)
            if self._audience not in self.AUDIENCES:
                self.bail()
        return self._audience

    @property
    def caption(self):
        """String to be displayed at the top of the table."""

        caption = f"{self.audience} Concepts With {self.status} Status"
        if self.date_range:
            return caption, self.date_range
        return caption

    @property
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
            columns.append("QC Notes")
        return columns

    @property
    def concepts(self):
        """Glossary term concepts selected for the report."""

        if not hasattr(self, "_concepts"):
            query = self.Query("query_term", "doc_id").unique()
            query.where(query.Condition("path", self.status_date_path))
            if self.start:
                query.where(query.Condition("value", self.start, ">="))
            if self.end:
                end = f"{self.end} 23:59:59"
                query.where(query.Condition("value", end, "<="))
            self._concepts = []
            for row in query.order("doc_id").execute(self.cursor).fetchall():
                concept = Concept(self, row.doc_id)
                if concept.in_scope:
                    self._concepts.append(concept)
        return self._concepts

    @property
    def date_range(self):
        """Second caption line above the table."""

        if not hasattr(self, "_date_range"):
            if self.start:
                if self.end:
                    self._date_range = f"{self.start} to {self.end}"
                else:
                    self._date_range = f"Since {self.start}"
            elif self.end:
                self._date_range = f"Through {self.end}"
            else:
                self._date_range = None
        return self._date_range

    @property
    def default_end(self):
        """Default value for the end of the request form's date range."""
        return self.started.strftime("%Y-%m-%d")

    @property
    def default_start(self):
        """Default value for the start of the request form's date range."""
        return (self.started - timedelta(7)).strftime("%Y-%m-%d")

    @property
    def end(self):
        """End of the date range requested for the report."""

        if not hasattr(self, "_end"):
            self._end = self.fields.getvalue("end")
            if self._end:
                try:
                    self._end = str(self.parse_date(self._end))
                except Exception:
                    self.logger.exception(self._end)
                    self.bail("Invalid end date string")
        return self._end

    @property
    def include_blocked_documents(self):
        """True if we should include blocked term name documents."""

        if not hasattr(self, "_include_blocked_documents"):
            self._include_blocked_documents = "blocked" in self.options
        return self._include_blocked_documents

    @property
    def include_english(self):
        """True if we should include information about the original document.

        Applicable only when we are running the Spanish version of the report.
        """

        if not hasattr(self, "_include_english"):
            self._include_english = "english" in self.options
        return self._include_english

    @property
    def include_notes_column(self):
        """True if we should display a QC Notes column."""

        if not hasattr(self, "_include_notes_column"):
            self._include_notes_column = "notes" in self.options
        return self._include_notes_column

    @property
    def language(self):
        """String for the language selected by the user for the report."""

        if not hasattr(self, "_language"):
            self._language = self.fields.getvalue("language")
            if not self._language:
                self._language = self.fields.getvalue("report")
            if not self._language:
                self._language = self.LANGUAGES[0]
            if self._language not in self.LANGUAGES:
                self.bail()
        return self._language

    @property
    def options(self):
        """Miscellanous options for the report."""

        if not hasattr(self, "_options"):
            self._options = set(self.fields.getlist("opts"))
        return self._options

    @property
    def report_type(self):
        """Lowercase string for the report's selected language."""

        if not hasattr(self, "_report_type"):
            self._report_type = self.language.lower()
        return self._report_type

    @property
    def rows(self):
        """Assemble the table rows for the report."""

        if not hasattr(self, "_rows"):
            self._rows = []
            for concept in self.concepts:
                self._rows += concept.rows
        return self._rows

    @property
    def show_resources(self):
        """True if we should display pronunciation or translation resources."""

        if not hasattr(self, "_show_resources"):
            self._show_resources = "resources" in self.options
        return self._show_resources

    @property
    def start(self):
        """Beginning of the date range requested for the report."""

        if not hasattr(self, "_start"):
            self._start = self.fields.getvalue("start")
            if self._start:
                try:
                    self._start = str(self.parse_date(self._start))
                except Exception:
                    self.logger.exception(self._start)
                    self.bail("Invalid start date string")
        return self._start

    @property
    def status(self):
        """String for the status value selected by the user for the report."""

        if not hasattr(self, "_status"):
            self._status = self.fields.getvalue("status", self.STATUSES[0])
            if self._status not in self.STATUSES:
                self.bail()
        return self._status

    @property
    def status_date_path(self):
        """Query term path used to find the concepts for the report."""
        return f"/GlossaryTermConcept/{self.STATUS_DATE_PATHS[self.language]}"

    @property
    def subtitle(self):
        """What we display underneath the main banner."""

        if not hasattr(self, "_subtitle"):
            template = "Glossary Term Concept by {} Definition Status"
            self._subtitle = template.format(self.language)
        return self._subtitle


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

    @property
    def blocked(self):
        """True if the document is blocked from publication."""
        return self.doc.active_status != Doc.ACTIVE

    @property
    def control(self):
        """Access to the database and the report's options."""
        return self.__control

    @property
    def doc(self):
        """`Doc` object for the CDR GlossaryTermConcept document."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.control.session, id=self.__doc_id)
        return self._doc

    @property
    def english_definition(self):
        """English definition which is in scope for the report."""

        if not hasattr(self, "_english_definition"):
            self._english_definition = None
            for node in self.doc.root.findall("TermDefinition"):
                if not self._english_definition:
                    definition = Definition(self, node)
                    if definition.in_scope:
                        self._english_definition = definition
            if not self._english_definition:
                self._english_definition = Definition(self)
        return self._english_definition

    @property
    def english_name(self):
        """`Name` object for the English name selected for the report."""
        return self.name_doc.english

    @property
    def english_rows(self):
        """Assemble the rows for the English version of the report."""

        if not hasattr(self, "_english_rows"):
            Cell = Reporter.Cell
            row = [
                Cell(self.doc.id, rowspan=self.rowspan),
                self.name_docs[0].english.span,
            ]
            if self.control.show_resources:
                row.append(self.name_docs[0].english.resources)
            if self.control.status == "Revision pending":
                definition = self.name_doc.published_definition
                row.append(Cell(definition.span, rowspan=self.rowspan))
            definition = self.english_definition
            row.append(Cell(definition.span, rowspan=self.rowspan))
            row.append(Cell(definition.resources, rowspan=self.rowspan))
            if self.control.include_notes_column:
                row.append(Cell("", rowspan=self.rowspan, width="100px"))
            self._english_rows = [row]
            for doc in self.name_docs[1:]:
                row = [doc.english.span]
                if self.control.show_resources:
                    row.append(doc.english.resources)
                self._english_rows.append(row)
        return self._english_rows

    @property
    def in_scope(self):
        """Should we include this concept document in the report?"""
        return getattr(self, f"{self.control.report_type}_definition").in_scope

    @property
    def name_doc(self):
        """NameDoc object selected for filling in definition text placeholders.

        Pick the one with the latest publication date if possible.
        Otherwise, use the first one in the sort order for the docs.
        """

        if not hasattr(self, "_name_doc"):
            self._name_doc = None
            for doc in self.name_docs:
                if doc.last_published:
                    if self._name_doc:
                        if self._name_doc.last_published < doc.last_published:
                            self._name_doc = doc
                    else:
                        self._name_doc = doc
            if not self._name_doc:
                self._name_doc = self.name_docs[0]
        return self._name_doc

    @property
    def name_docs(self):
        """Sequence of `NameDoc` objects linked to this concept."""

        if not hasattr(self, "_name_docs"):
            docs = []
            query = self.control.Query("query_term", "doc_id").unique()
            query.where(query.Condition("path", self.NAME_PATH))
            query.where(query.Condition("int_val", self.doc.id))
            for row in query.execute(self.control.cursor).fetchall():
                doc = NameDoc(self, row.doc_id)
                if self.control.include_blocked_documents or not doc.blocked:
                    docs.append(doc)
            if docs:
                self._name_docs = sorted(docs)
            else:
                self._name_docs = [NameDoc(self)]
        return self._name_docs

    @property
    def replacements(self):
        """Dictionary of nodes for filling in placeholders in definitions."""

        if not hasattr(self, "_replacements"):
            self._replacements = {}
            for node in self.doc.root.iter("ReplacementText"):
                self._replacements[node.get("name")] = node
            self._replacements.update(self.name_doc.replacements)
        return self._replacements

    @property
    def rows(self):
        """Assemble the rows for the report."""
        return getattr(self, f"{self.control.report_type}_rows")

    @property
    def rowspan(self):
        """Number of table rows in total used for this concept document."""

        if not hasattr(self, "_rowspan"):
            self._rowspan = None
            if self.control.report_type == "english":
                if len(self.name_docs) > 1:
                    self._rowspan = len(self.name_docs)
            else:
                count = sum([len(doc.spanish) for doc in self.name_docs])
                if count > 1:
                    self._rowspan = count
        return self._rowspan

    @property
    def spanish_definition(self):
        """Spanish definition which is in scope for the report."""

        if not hasattr(self, "_spanish_definition"):
            self._spanish_definition = None
            for node in self.doc.root.findall("TranslatedTermDefinition"):
                if not self._spanish_definition:
                    definition = Definition(self, node)
                    if definition.in_scope:
                        self._spanish_definition = definition
            if not self._spanish_definition:
                self._spanish_definition = Definition(self)
        return self._spanish_definition

    @property
    def spanish_name(self):
        """`NameString` object for the Spanish name selected for the report."""
        return self.name_doc.spanish[0]

    @property
    def spanish_rows(self):
        """Assemble the rows for the Spanish version of the report."""

        if not hasattr(self, "_spanish_rows"):
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
                row.append(Cell(definition.resources, rowspan=self.rowspan))
            if self.control.include_notes_column:
                row.append(Cell("", rowspan=self.rowspan, width="100px"))
            self._spanish_rows = [row]
            for name in doc.spanish[1:]:
                self._spanish_rows.append([Cell(name.span)])
            for doc in self.name_docs[1:]:
                if self.control.include_english:
                    self._spanish_rows.append([
                        Cell(doc.english.span, rowspan=len(doc.spanish)),
                        Cell(doc.spanish[0].span),
                    ])
                    for name in doc.spanish[1:]:
                        self._spanish_rows.append([Cell(name.span)])
                else:
                    for name in doc.spanish:
                        self._spanish_rows.append([Cell(name.span)])
        return self._spanish_rows


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

    @property
    def blocked(self):
        """True if the name document may not be published."""
        return self.doc and self.doc.active_status != Doc.ACTIVE

    @property
    def concept(self):
        """Object for the document in which the name link was found."""
        return self.__concept

    @property
    def control(self):
        """Access to the report's options and report-creation tools."""
        return self.concept.control

    @property
    def doc(self):
        """`Doc` object for the GlossaryTermName document."""

        if not hasattr(self, "_doc"):
            self._doc = None
            try:
                if self.__doc_id:
                    self._doc = Doc(self.control.session, id=self.__doc_id)
            except Exception:
                self.control.bail(f"Name document CDR{self.__doc_id} missing")
        return self._doc

    @property
    def english(self):
        """`Name` object for the document's English name."""

        if not hasattr(self, "_english"):
            self._english = None
            if self.doc:
                node = self.doc.root.find("TermName")
                if node is not None:
                    self._english = EnglishName(self, node)
            if self._english is None:
                self._english = EnglishName(self)
        return self._english

    @property
    def last_published(self):
        """When the name document was most recently published."""

        if not hasattr(self, "_last_published"):
            self._last_published = None
            if self.doc:
                query = self.control.Query("pub_proc_cg c", "p.completed")
                query.join("pub_proc p", "p.id = c.pub_proc")
                query.where(query.Condition("c.id", self.doc.id))
                rows = query.execute(self.control.cursor).fetchall()
                self._last_published = rows[0].completed if rows else None
        return self._last_published

    @property
    def published_definition(self):
        """The latest published English definition for the report's audience.

        Get the denormalized (that is, with placeholders replaced)
        definition from the version of the GlossaryTerm document
        we last exported to cancer.gov and our content distribution
        partners.
        """

        if not hasattr(self, "_published_definition"):
            self._published_definition = None
            if self.doc:
                query = self.control.Query("pub_proc_cg", "xml")
                query.where(query.Condition("id", self.doc.id))
                rows = query.execute(self.control.cursor).fetchall()
                if rows:
                    root = etree.fromstring(rows[0].xml.encode("utf-8"))
                    for node in root.iter("TermDefinition"):
                        if not self._published_definition:
                            audience = Doc.get_text(node.find("Audience"))
                            if audience == self.control.audience:
                                definition = node.find("DefinitionText")
                                if definition is not None:
                                    pubdef = PublishedDefinition(self, node)
                                    self._published_definition = pubdef
            if not self._published_definition:
                self._published_definition = PublishedDefinition(self)
        return self._published_definition

    @property
    def replacements(self):
        """Dictionary of substitutions for placeholders in the definition."""

        if not hasattr(self, "_replacements"):
            self._replacements = {}
            if self.doc:
                for node in self.doc.root.iter("ReplacementText"):
                    self._replacements[node.get("name")] = node
        return self._replacements

    @property
    def sort_key(self):
        """Select and normalize the name used for sorting.

        Support sorting of the names of a glossary concept,
        based on the English name string or the "first" Spanish
        name string, depending on which report we're creating.
        """

        if not hasattr(self, "_sort_key"):
            if self.control.report_type == "english":
                name_key = self.english.sort_key
            else:
                name_key = self.spanish[0].sort_key
            self._sort_key = name_key, self.doc.id if self.doc else 0
        return self._sort_key

    @property
    def spanish(self):
        """Sequence of `TermNameString` objects for the Spanish names."""

        if not hasattr(self, "_spanish"):
            self._spanish = None
            if self.doc:
                nodes = self.doc.root.findall("TranslatedName")
                self._spanish = [SpanishName(self, node) for node in nodes]
            if not self._spanish:
                self._spanish = [SpanishName(self)]
        return self._spanish


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

    @property
    def control(self):
        """Access to the report options and report-building tools."""
        return self.__name_doc.control

    @property
    def language(self):
        """Override in derived classes."""
        raise Exception("Must override this method")

    @property
    def name_string_node(self):
        """Node from which the name's string is pulled."""

        if not hasattr(self, "_name_string_node"):
            self._name_string_node = None
            if self.__node is not None:
                self._name_string_node = self.__node.find("TermNameString")
        return self._name_string_node

    @property
    def pronunciation(self):
        """String for the pronunciation of the English name."""

        if not hasattr(self, "_pronunciation"):
            self._pronunciation = None
            if self.__node is not None:
                node = self.__node.find("TermPronunciation")
                self._pronunciation = Doc.get_text(node, "").strip()
        return self._pronunciation

    @property
    def resources(self):
        """Sequence of strings for pronunciation resources."""

        if not hasattr(self, "_resources"):
            self._resources = []
            if self.__node is not None:
                for node in self.__node.findall("PronunciationResource"):
                    resource = Doc.get_text(node, "").strip()
                    if resource:
                        self._resources.append(resource)
        return self._resources

    @property
    def sort_key(self):
        """Order the names on the report within the concept."""

        if not hasattr(self, "_sort_key"):
            self._sort_key = ""
            if self.__node is not None:
                self._sort_key = "".join(self.__node.itertext()).lower()
        return self._sort_key

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

    @property
    def audience(self):
        """Patient or Health professional."""

        if not hasattr(self, "_audience"):
            self._audience = None
            if self.__node is not None:
                self._audience = Doc.get_text(self.__node.find("Audience"))
        return self._audience

    @property
    def concept(self):
        """Object for the document in which the definition was found."""
        return self.__concept

    @property
    def control(self):
        """Access to the report's options and report-creation tools."""
        return self.concept.control

    @property
    def comment(self):
        """First comment found (last entered) for the definition, if any."""

        if not hasattr(self, "_comment"):
            comments = []
            if self.__node is not None:
                for node in self.__node.findall("Comment"):
                    comment = Doc.get_text(node, "").strip()
                    if comment:
                        comments.append(comment)
            self._comment = comments[0] if comments else ""
        return self._comment

    @property
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

    @property
    def language(self):
        """English or Spanish."""

        if not hasattr(self, "_language"):
            self._language = None
            if self.__node is not None:
                if self.__node.tag == "TermDefinition":
                    self._language = "English"
                else:
                    self._language = "Spanish"
        return self._language

    @property
    def not_found(self):
        """String displayed for a dummy definition object."""
        return f"NO {self.control.audience} DEFINITION FOUND"

    @property
    def resources(self):
        """Sequence of strings for definition resources."""

        if not hasattr(self, "_resources"):
            self._resources = []
            if self.__node is not None:
                tag = self.TAGS[self.language]["resource"]
                for node in self.__node.findall(tag):
                    self._resources.append(Doc.get_text(node, "").strip())
        return self._resources

    @property
    def span(self):
        """HTML wrapper for the marked-up definition display."""

        if not hasattr(self, "_span"):
            self._span = None
            if self.__node is not None:
                self._span = self.__parse(self.__node.find("DefinitionText"))
            if self._span is None:
                self._span = self.B.SPAN(self.not_found, style=Control.ERROR)
        return self._span

    @property
    def status(self):
        """String for the definition's status."""

        if not hasattr(self, "_status"):
            self._status = None
            if self.__node is not None:
                tag = self.TAGS[self.language]["status"]
                self._status = Doc.get_text(self.__node.find(tag), "").strip()
        return self._status

    @property
    def status_date(self):
        """String for the definition's status date."""

        if not hasattr(self, "_status_date"):
            self._status_date = None
            if self.__node is not None:
                node = self.__node.find(self.TAGS[self.language]["date"])
                self._status_date = Doc.get_text(node, "").strip()
        return self._status_date

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

    @property
    def not_found(self):
        """String displayed for a dummy definition object."""
        return f"NO PUBLISHED DEFINITION FOUND"

if __name__ == "__main__":
    """Only execute if loaded as a script."""
    Control().run()
