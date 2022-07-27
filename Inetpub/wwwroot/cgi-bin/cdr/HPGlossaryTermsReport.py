#!/usr/bin/env python

"""Display health professional dictionary terms.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):

    SUBTITLE = "Health Professional Glossary Terms Report"
    LOGNAME = "HPGlossaryTerms"
    AUDIENCES = "Patient", "Health Professional"
    REVISION_LEVEL = Doc.REVISION_LEVEL_PUBLISHED_OR_APPROVED_OR_PROPOSED
    GENETICS = "Genetics"
    NONE = "None"
    DICTIONARIES = GENETICS, NONE
    LIST_OF_TERMS = "List of Terms"
    CONCEPTS = "Concepts"
    TYPES = LIST_OF_TERMS, CONCEPTS
    PRONUNCIATIONS = "Include pronunciations"
    LOE_TERMS = "Include level of evidence terms"
    BLOCKED_TERMS = "Include blocked terms"
    OPTIONS = (
        (PRONUNCIATIONS, "pronunciation-wrapper"),
        (LOE_TERMS, "loe-wrapper"),
        (BLOCKED_TERMS, "blocked-wrapper"),
    )
    SCRIPT = "../../js/HPGlossaryTermsReport.js"

    def build_tables(self):
        """Assemble the table for the report."""

        opts = dict(columns=self.columns, caption=self.caption)
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Add the fields to the report request form.

        Pass:
            page - HTMLPage where the form is drawn
        """

        fieldset = page.fieldset("Selections")
        fieldset.append(page.select("dictionary", options=self.DICTIONARIES))
        opts = dict(options=self.LANGUAGES, multiple=True)
        fieldset.append(page.select("language", **opts))
        default = self.TYPES[0]
        opts = dict(label="Report Type", options=self.TYPES, default=default)
        fieldset.append(page.select("type", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Date Filtering")
        fieldset.append(page.date_field("start"))
        fieldset.append(page.date_field("end"))
        page.form.append(fieldset)
        fieldset = page.fieldset("Options")
        for option, wrapper_id in self.OPTIONS:
            opts = dict(value=option, wrapper_id=wrapper_id)
            fieldset.append(page.checkbox("opts", **opts))
        page.form.append(fieldset)
        page.head.append(page.B.SCRIPT(src=self.SCRIPT))

    def show_report(self):
        """Override this method to add custom CSS."""

        elapsed = self.report.page.html.get_element_by_id("elapsed", None)
        if elapsed is not None:
            elapsed.text = str(self.elapsed)
        self.report.page.add_css(".report table { min-width: 500px; }")
        self.report.send(self.format)

    @property
    def blocked(self):
        """True if the report should include blocked terms."""
        return self.BLOCKED_TERMS in self.options

    @property
    def caption(self):
        """What we display at the top of the report table."""

        if not hasattr(self, "_caption"):
            languages = " and ".join(self.language)
            if self.type == self.LIST_OF_TERMS:
                self._caption = [f"{languages} HP Glossary Terms"]
            else:
                self._caption = [f"{languages} HP Glossary Concepts"]
            if self.dictionary == self.NONE:
                self._caption.append("Without Dictionary")
            else:
                self._caption.append("Genetics Dictionary")
            self._caption.append(self.started.strftime("%Y-%m-%d %H:%M:%S"))
            if self.start or self.end:
                if self.start:
                    if self.end:
                        range = f"From {self.start} to {self.end}"
                    else:
                        range = f"On or after {self.start}"
                else:
                    range = f"Before or on {self.end}"
                self._caption.append(range)

        return self._caption

    @property
    def columns(self):
        """Column headers for the report table."""

        if not hasattr(self, "_columns"):
            Column = self.Reporter.Column
            if self.type == self.LIST_OF_TERMS:
                self._columns = [Column(f"Terms ({len(self.rows)})")]
            else:
                names = "Term Names"
                if "English" in self.language and self.pronunciations:
                    names += " (Pronunciations)"
                self._columns = (
                    Column("CDR ID of GTC"),
                    Column(names),
                    Column("Definition"),
                )
        return self._columns

    @property
    def concepts(self):
        """GlossaryTermConcept documents selected for the report."""

        if not hasattr(self, "_concepts"):
            op = "="
            if self.language == ["English"]:
                d_path = "/GlossaryTermConcept/TermDefinition"
            elif self.language == ["Spanish"]:
                d_path = "/GlossaryTermConcept/TranslatedTermDefinition"
            else:
                d_path = "/GlossaryTermConcept/%TermDefinition"
                op = "LIKE"
            query = self.Query("query_term", "doc_id").unique().order(1)
            query.where(f"path {op} '{d_path}/Audience'")
            query.where("value = 'Health Professional'")
            self._concepts = []
            for row in query.execute(self.cursor).fetchall():
                concept = Concept(self, row.doc_id)
                if concept.in_scope:
                    self._concepts.append(concept)
            self.logger.info("%d concepts in scope", len(self._concepts))
        return self._concepts

    @property
    def dictionary(self):
        """Genetics or None."""

        if not hasattr(self, "_dictionary"):
            default = self.DICTIONARIES[0]
            self._dictionary = self.fields.getvalue("dictionary", default)
            if self._dictionary not in self.DICTIONARIES:
                self.bail()
        return self._dictionary

    @property
    def end(self):
        """Optional date filtering range end date."""

        if not hasattr(self, "_end"):
            try:
                self._end = self.parse_date(self.fields.getvalue("end"))
                if self._end:
                    self._end = str(self._end)
            except Exception:
                self.bail()
        return self._end

    @property
    def language(self):
        """English and/or Spanish."""

        if not hasattr(self, "_language"):
            self._language = self.fields.getlist("language")
            if not self._language:
                self._language = list(self.LANGUAGES)
            for language in self._language:
                if language not in self.LANGUAGES:
                    self.bail()
        return self._language

    @property
    def loe(self):
        """True if the report should include level-of-evidence terms."""
        return self.LOE_TERMS in self.options

    @property
    def options(self):
        """Report option flags."""

        if not hasattr(self, "_options"):
            self._options = self.fields.getlist("opts")
        return self._options

    @property
    def pronunciations(self):
        """True if the report should include pronunciations."""
        return self.PRONUNCIATIONS in self.options

    @property
    def rows(self):
        """Accumulate all of the table rows for the report."""

        if not hasattr(self, "_rows"):
            self._rows = []
            for concept in self.concepts:
                self._rows += concept.rows
            if self.type == self.LIST_OF_TERMS:
                terms = {row[0] for row in self._rows}
                self._rows = [[term] for term in sorted(terms, key=str.lower)]
        return self._rows

    @property
    def start(self):
        """Optional date filtering range start date."""

        if not hasattr(self, "_start"):
            try:
                self._start = self.parse_date(self.fields.getvalue("start"))
                if self._start:
                    self._start = str(self._start)
            except Exception:
                self.bail()
        return self._start

    @property
    def type(self):
        """Which type of report has been requested?"""

        if not hasattr(self, "_type"):
            self._type = self.fields.getvalue("type", self.TYPES[0])
            if self._type not in self.TYPES:
                self.bail()
        return self._type


class Concept:
    """Information on a CDR GlossaryTermConcept document."""

    LOE = "level of evidence"
    DEFS = dict(
        English="TermDefinition",
        Spanish="TranslatedTermDefinition",
    )

    def __init__(self, control, id):
        """Remember the caller's values.

        Pass:
            control - access to the database and the report options
            id - integer for the unique ID of this CDR concept document
        """

        self.__control = control
        self.__id = id

    @property
    def control(self):
        """Access to the current login session and the report options."""
        return self.__control

    @property
    def doc(self):
        """`Doc` object for the GlossaryTermConcept document."""

        if not hasattr(self, "_doc"):
            opts = dict(id=self.__id, level=Control.REVISION_LEVEL)
            self._doc = Doc(self.control.session, **opts)
        return self._doc

    @property
    def definitions(self):
        """Definitions for the concept needed for the report."""

        if not hasattr(self, "_definitions"):
            self._definitions = []
            for language in self.control.language:
                for node in self.root.findall(self.DEFS[language]):
                    definition = Definition(self, node)
                    if definition.in_scope:
                        self._definitions.append(definition)
        return self._definitions

    @property
    def in_scope(self):
        """Should this concept be included in the report?"""

        if self.control.dictionary == Control.NONE and not self.control.loe:
            if self.LOE in self.types:
                return False
        if not self.definitions or not self.name_docs:
            return False
        return True

    @property
    def name_docs(self):
        """GlossaryTermName documents linked to this concept."""

        if not hasattr(self, "_name_docs"):
            c_path = "/GlossaryTermName/GlossaryTermConcept/@cdr:ref"
            query = self.control.Query("query_term", "doc_id").unique()
            query.where(f"path = '{c_path}'")
            query.where(query.Condition("int_val", self.__id))
            self._name_docs = []
            for row in query.execute(self.control.cursor).fetchall():
                name_doc = NameDoc(self, row.doc_id)
                if name_doc.in_scope:
                    self._name_docs.append(name_doc)
        return self._name_docs

    @property
    def name_rows(self):
        """How many rows are needed for the concept's names?"""

        if not hasattr(self, "_name_rows"):
            self._name_rows = 0
            for name_doc in self.name_docs:
                self._name_rows += len(name_doc.names)
        return self._name_rows

    @property
    def root(self):
        """Root of the document after applying revision markup resolution."""

        if not hasattr(self, "_root"):
            self._root = self.doc.resolved
        return self._root

    @property
    def rows(self):
        """Rows to be added to the report for this concept."""

        if not hasattr(self, "_rows"):

            if self.control.type == Control.CONCEPTS:

                # Create the first row.
                Cell = self.control.Reporter.Cell
                row = [
                    Cell(self.__id, rowspan=self.rowspan),
                    self.name_docs[0].names[0].cell,
                    Cell(self.definitions[0].text, rowspan=self.name_rows),
                ]
                self._rows = [row]

                # Add rows for the rest of the names.
                for name in self.name_docs[0].names[1:]:
                    self._rows.append([name.cell])
                for name_doc in self.name_docs[1:]:
                    for name in name_doc.names:
                        self._rows.append([name.cell])

                # Add rows for the extra definitions.
                for i in range(1, len(self.definitions)):
                    self._rows.append(["", Cell(self.definitions[i].text)])
            else:
                self._rows = []
                for name_doc in self.name_docs:
                    for name in name_doc.names:
                        self._rows.append([name.string])

        return self._rows

    @property
    def rowspan(self):
        """How many rows in total will be generated for this concept doc?"""

        if not hasattr(self, "_rowspan"):
            self._rowspan = self.name_rows + len(self.definitions) - 1
        return self._rowspan

    @property
    def types(self):
        """Set of strings for the concept's type."""

        if not hasattr(self, "_types"):
            self._types = set()
            for node in self.root.findall("TermType"):
                concept_type = Doc.get_text(node, "").strip()
                if concept_type:
                    self._types.add(concept_type.lower())
        return self._types


class NameDoc:
    """Information collected from one CDR GlossaryTermName document."""

    NAMES = dict(
        English="TermName",
        Spanish="TranslatedName",
    )

    def __init__(self, concept, id):
        """Remember the caller's values.

        Pass:
            concept - access to the control object and the linked concept info
            id - integer for the CDR document's unique ID
        """

        self.__concept = concept
        self.__id = id

    @property
    def blocked(self):
        """Is this term marked as inactive?"""

        if not hasattr(self, "_blocked"):
            self._blocked = self.doc.active_status == Doc.BLOCKED
        return self._blocked

    @property
    def concept(self):
        """Access to the control object and the linked concept info."""
        return self.__concept

    @property
    def control(self):
        """Access to the current login session and the report options."""
        return self.concept.control

    @property
    def doc(self):
        """`Doc` object for the GlossaryTermName document."""

        if not hasattr(self, "_doc"):
            opts = dict(id=self.__id, level=Control.REVISION_LEVEL)
            self._doc = Doc(self.control.session, **opts)
        return self._doc

    @property
    def in_scope(self):
        """Can this term name document be used for the report?"""

        if self.blocked and not self.control.blocked:
            return False
        if not self.names:
            return False
        return True

    @property
    def names(self):
        """Sequence of `Name` objects usable for the report."""

        if not hasattr(self, "_names"):
            self._names = []
            for language in self.control.language:
                for node in self.root.findall(self.NAMES[language]):
                    name = self.Name(self, node)
                    if name.in_scope:
                        self._names.append(name)
        return self._names

    @property
    def replacements(self):
        """Dictionary of values for definition placeholders."""

        if not hasattr(self, "_replacements"):
            self._replacements = {}
            for node in self.root.findall("ReplacementText"):
                self._replacements[node.get("name")] = Doc.get_text(node, "")
        return self._replacements

    @property
    def root(self):
        """Root of the document after applying revision markup resolution."""

        if not hasattr(self, "_root"):
            self._root = self.doc.resolved
        return self._root

    class Name:
        """One of the names in a glossary name document."""

        def __init__(self, doc, node):
            """Remember the caller's values.

            Pass:
                doc - `NameDoc` object in which this name was found
                node - portion of the document where this name's info lives
            """

            self.__doc = doc
            self.__node = node

        @property
        def cell(self):
            """What goes in the cell for this term name."""

            if not hasattr(self, "_cell"):
                self._cell = self.string
                if self.__doc.control.pronunciations and self.pronunciation:
                    self._cell = f"{self._cell} ({self.pronunciation})"
                if self.__doc.blocked:
                    B = self.__doc.control.HTMLPage.B
                    blocked = B.SPAN("[Blocked]", B.CLASS("error"))
                    self._cell = B.SPAN(f"{self._cell} ", blocked)
            return self._cell

        @property
        def in_scope(self):
            """Make sure this name is usable for the report."""

            if not self.string:
                return False
            if self.__doc.concept.control.start:
                if not self.status_date:
                    return False
                if self.__doc.concept.control.start > self.status_date:
                    return False
            if self.__doc.concept.control.end:
                if not self.status_date:
                    return False
                if self.__doc.concept.control.end < self.status_date:
                    return False
            return True

        @property
        def pronunciation(self):
            """Crude representation of the way the term name is spoken."""

            if not hasattr(self, "_pronunciation"):
                node = self.__node.find("TermPronunciation")
                self._pronunciation = Doc.get_text(node, "").strip() or None
            return self._pronunciation

        @property
        def status_date(self):
            """When the name's current status was set."""

            if not hasattr(self, "_status_date"):
                if self.__node.tag == "TermName":
                    path = "../TermNameStatusDate"
                else:
                    path = "TranslatedNameStatusDate"
                self._status_date = Doc.get_text(self.__node.find(path))
            return self._status_date

        @property
        def string(self):
            """Plain text string for this term name."""

            if not hasattr(self, "_string"):
                node = self.__node.find("TermNameString")
                self._string = Doc.get_text(node, "").strip() or None
            return self._string


class Definition:
    """Object for a glossary term definition (English or Spanish)."""

    HP = "health professional"

    def __init__(self, concept, node):
        """Remember the caller's values.

        Pass:
            concept - access to the replacement values and report options
            node - portion of the document where this definition was found
        """

        self.__concept = concept
        self.__node = node

    @property
    def audiences(self):
        """Set of strings ("patient" and/or "health professional")."""

        if not hasattr(self, "_audiences"):
            self._audiences = set()
            for node in self.__node.findall("Audience"):
                self._audiences.add(Doc.get_text(node, "").lower())
        return self._audiences

    @property
    def dictionaries(self):
        """In which dictionaries should this definition appear?"""

        if not hasattr(self, "_dictionaries"):
            self._dictionaries = set()
            for node in self.__node.findall("Dictionary"):
                dictionary = Doc.get_text(node, "").strip()
                if dictionary:
                    self._dictionaries.add(dictionary)
        return self._dictionaries

    @property
    def in_scope(self):
        """Does this definition belong on the report?"""

        if self.HP not in self.audiences:
            return False
        dictionary = self.__concept.control.dictionary
        if dictionary == Control.NONE:
            return not self.dictionaries
        return dictionary in self.dictionaries

    @property
    def replacements(self):
        """Dictionary of substitutions for placeholders in the definition."""

        if not hasattr(self, "_replacements"):
            self._replacements = {}
            for node in self.__node.findall("ReplacementText"):
                self._replacements[node.get("name")] = Doc.get_text(node, "")
            self._replacements.update(self.__concept.name_docs[0].replacements)
        return self._replacements

    @property
    def term_name(self):
        """Name to be used for definition placeholder substitutions."""

        if not hasattr(self, "_term_name"):
            self._term_name = self.__concept.name_docs[0].names[0].string
        return self._term_name

    @property
    def text(self):
        """Resolved definition ready to be plugged into the report."""

        if not hasattr(self, "_text"):
            B = self.__concept.control.HTMLPage.B
            pieces = []
            spans = 0
            for chunk in self.__parse(self.__node.find("DefinitionText")):
                if not isinstance(chunk, self.PlaceHolder):
                    pieces.append(chunk)
                else:
                    default = f"[UNRESOLVED PLACEHOLDER {chunk.name}]"
                    if chunk.name == "TERMNAME" and self.term_name:
                        chunk = self.term_name
                    elif chunk.name == "CAPPEDTERMNAME" and self.term_name:
                        chunk = self.term_name.capitalize()
                    else:
                        chunk = self.replacements.get(chunk.name, default)
                    pieces.append(B.SPAN(chunk, B.CLASS("replacement")))
                    spans += 1
            self._text = B.SPAN(*pieces) if spans else "".join(pieces)
        return self._text

    @classmethod
    def __parse(cls, node, with_tail=False):
        """Pull out the text and placeholders from a definition.

        Pass:
            node - portion of the document to be parsed (recursively)
            with_tail - this is set to True when we recurse

        Return:
            sequence of alternating `str` and `PlaceHolder` objects
        """

        if node is None:
            return []
        pieces = []
        if node.text is not None:
            pieces = [node.text]
        for child in node.findall("*"):
            if child.tag == "PlaceHolder":
                pieces.append(cls.PlaceHolder(child.get("name")))
                if child.tail is not None:
                    pieces.append(child.tail)
            else:
                pieces += cls.__parse(child, True)
        if with_tail and node.tail is not None:
            pieces.append(node.tail)
        return pieces

    class PlaceHolder:
        """Object to represent a placeholder in a glossary definition."""
        def __init__(self, name):
            self.name = name


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
