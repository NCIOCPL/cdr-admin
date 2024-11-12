#!/usr/bin/env python

"""Show glossary term concepts of a given type.

"We need a new glossary term concept by type QC report to help us ensure
consistency in the wording of definitions."
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):

    SUBTITLE = "Glossary Term Concept By Type Report"
    LOGNAME = "GTCbyType"
    INSTRUCTIONS = (
        "You may specify either a term name start, and/or text from the "
        "definitions of the terms to be selected. All other selection "
        "criteria are required."
    )
    STATUSES = "Approved", "New pending", "Revision pending", "Rejected"
    AUDIENCES = "Patient", "Health Professional"
    A_PATH = "/GlossaryTermConcept/TermDefinition/Audience"
    S_PATH = "/GlossaryTermConcept/TermDefinition/DefinitionStatus"
    D_PATH = "/GlossaryTermConcept/TermDefinition/DefinitionText"
    T_PATH = "/GlossaryTermConcept/TermType"
    C_PATH = "/GlossaryTermName/GlossaryTermConcept/@cdr:ref"
    N_PATH = "/GlossaryTermName/TermName/TermNameString"
    REVISION_LEVEL = Doc.REVISION_LEVEL_PUBLISHED_OR_APPROVED_OR_PROPOSED

    def build_tables(self):
        """Assemble the table for the report."""

        args = len(self.concepts), self.names
        self.logger.info("%s concept objects loaded with %d names", *args)
        opts = dict(columns=self.columns, caption=self.caption)
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Add the fields to the report request form.

        Pass:
            page - HTMLPage where the form is drawn
        """

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)
        fieldset = page.fieldset("Selection Options")
        types = self.types
        opts = dict(label="Term Type", options=types, default=types[0])
        fieldset.append(page.select("type", **opts))
        fieldset.append(page.text_field("name", label="Term Name"))
        fieldset.append(page.text_field("text", label="Definition Text"))
        opts = dict(
            label="Definition Status",
            options=self.STATUSES,
            default=self.STATUSES[0],
        )
        fieldset.append(page.select("statuses", **opts))
        opts = dict(
            label="Audience",
            options=self.AUDIENCES,
            default=self.AUDIENCES[0],
        )
        fieldset.append(page.select("audience", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Display Options")
        opts = dict(label="English Only", value="N", checked=True)
        fieldset.append(page.radio_button("spanish", **opts))
        opts = dict(label="Include Spanish", value="Y")
        fieldset.append(page.radio_button("spanish", **opts))
        page.form.append(fieldset)

    @cached_property
    def audience(self):
        """Patient or Health professional."""

        audience = self.fields.getvalue("audience", self.AUDIENCES[0])
        if audience not in self.AUDIENCES:
            self.bail()
        return audience

    @cached_property
    def caption(self):
        """What we display at the top of the report table."""

        languages = "English & Spanish" if self.spanish else "English"
        return (
            f"{self.SUBTITLE} - {languages}",
            self.type,
            self.started.strftime("%Y-%m-%d %H:%M:%S"),
        )

    @cached_property
    def columns(self):
        """Column headers for the report table."""

        if self.spanish:
            return (
                self.Reporter.Column("CDR ID of GTC"),
                self.Reporter.Column("Term Names (English)"),
                self.Reporter.Column("Term Names (Spanish)"),
                self.Reporter.Column("Definition (English)"),
                self.Reporter.Column("Definition (Spanish)"),
            )
        return (
            self.Reporter.Column("CDR ID of GTC"),
            self.Reporter.Column("Term Names (Pronunciations)"),
            self.Reporter.Column("Definition (English)"),
        )

    @cached_property
    def concepts(self):
        """GlossaryTermConcept documents selected for the report."""

        query = self.Query("query_term t", "t.doc_id").unique().order(1)
        query.join("query_term s", "s.doc_id = t.doc_id")
        query.join("query_term a", "a.doc_id = s.doc_id",
                   "LEFT(a.node_loc, 4) = LEFT(s.node_loc, 4)")
        query.where(f"t.path = '{self.T_PATH}'")
        query.where(f"s.path = '{self.S_PATH}'")
        query.where(f"a.path = '{self.A_PATH}'")
        query.where(query.Condition("t.value", self.type))
        query.where(query.Condition("s.value", self.status))
        query.where(query.Condition("a.value", self.audience))
        if self.name:
            pattern = f"{self.name}%"
            query.join("query_term c", "c.int_val = t.doc_id")
            query.join("query_term n", "n.doc_id = c.doc_id")
            query.where(f"c.path = '{self.C_PATH}'")
            query.where(f"n.path = '{self.N_PATH}'")
            query.where(query.Condition("n.value", pattern, "LIKE"))
        if self.text:
            pattern = f"%{self.text}%"
            query.join("query_term d", "d.doc_id = a.doc_id",
                       "LEFT(d.node_loc, 4) = LEFT(a.node_loc, 4)")
            query.where(f"d.path = '{self.D_PATH}'")
            query.where(query.Condition("d.value", pattern, "LIKE"))
        # FOR DEBUGGING query.log(label="GTC-BY-TYPE QUERY")
        # Use a fresh one-time connection for a longer timeout.
        rows = query.execute(timeout=600).fetchall()
        self.logger.info("found %d concept IDs", len(rows))
        return [Concept(self, row.doc_id) for row in rows]

    @cached_property
    def footer(self):
        """Override to get in the count of concepts in the report."""

        B = self.HTMLPage.B
        user = self.session.User(self.session, id=self.session.user_id)
        name = user.fullname or user.name
        today = self.started.strftime("%Y-%m-%d")
        generated = f"Report generated {today} by {name}"
        elapsed = B.SPAN(str(self.elapsed), id="elapsed")
        processed = f"Processed {len(self.concepts):d} concepts in "
        args = generated, B.BR(), processed, elapsed, B.CLASS("report-footer")
        return B.E("footer", B.P(*args))

    @cached_property
    def name(self):
        """For selecting concepts by term name start."""
        return self.fields.getvalue("name")

    @cached_property
    def names(self):
        """Integer for total number of GlossaryConceptName documents found."""
        return sum([len(concept.names) for concept in self.concepts])

    @cached_property
    def report_css(self):
        """Override vertical alignment of table cells."""
        return ".usa-table td { vertical-align: top; }"

    @cached_property
    def rows(self):
        """Accumulate all of the table rows for the report."""
        return sum([concept.rows for concept in self.concepts], start=[])

    @cached_property
    def spanish(self):
        """True if we are to display Spanish info, not just English."""
        return self.fields.getvalue("spanish") == "Y"

    @cached_property
    def status(self):
        """Concept docs with this status will be in the report."""

        status = self.fields.getvalue("status", self.STATUSES[0])
        if status not in self.STATUSES:
            self.bail()
        return status

    @cached_property
    def text(self):
        """For selecting concepts containing a definition phrase."""
        return self.fields.getvalue("text")

    @cached_property
    def type(self):
        """Concept type selected for the report."""

        type = self.fields.getvalue("type", self.types[0])
        if type not in self.types:
            self.bail()
        return type

    @cached_property
    def types(self):
        """Term types for the form picklist."""

        query = self.Query("query_term", "value").unique().order("value")
        query.where("path = '/GlossaryTermConcept/TermType'")
        query.where("value <> 'Other'")
        rows = query.execute(self.cursor).fetchall()
        return [row.value for row in rows] + ["Other"]

    @cached_property
    def wide_css(self):
        """Widen the table so the definitions have some breathing room."""
        return self.Reporter.Table.WIDE_CSS if self.spanish else None


class Concept:
    """Information on a CDR GlossaryTermConcept document."""

    def __init__(self, control, id):
        """Remember the caller's values.

        Pass:
            control - access to the database and the report options
            id - integer for the unique ID of this CDR concept document
        """

        self.__control = control
        self.__id = id

    @cached_property
    def audience(self):
        """Audience for the report, normalized for testing."""
        return self.control.audience.lower()

    @cached_property
    def control(self):
        """Access to the current login session and the report options."""
        return self.__control

    @cached_property
    def definition_rows(self):
        """How many rows are needed for the concept's definitions?"""

        return max(
            len(self.english_definitions),
            len(self.spanish_definitions)
        )

    @cached_property
    def doc(self):
        """`Doc` object for the GlossaryTermConcept document."""

        opts = dict(id=self.__id, level=Control.REVISION_LEVEL)
        return Doc(self.control.session, **opts)

    @cached_property
    def english_definitions(self):
        """English definitions for the concept needed for the report."""

        english_definitions = []
        for node in self.root.findall("TermDefinition"):
            definition = Definition(self, node)
            if self.audience in definition.audiences:
                english_definitions.append(definition)
        return english_definitions

    @cached_property
    def name_rows(self):
        """How many rows are needed for the concept's names?"""

        name_rows = 0
        for name in self.names:
            if name.spanish:
                name_rows += len(name.spanish)
            else:
                name_rows += 1
        return name_rows

    @cached_property
    def names(self):
        """GlossaryTermName documents linked to this concept."""

        query = self.control.Query("query_term", "doc_id").unique()
        query.where(f"path = '{Control.C_PATH}'")
        query.where(query.Condition("int_val", self.__id))
        rows = query.execute(self.control.cursor).fetchall()
        return [Name(self, row.doc_id) for row in rows]

    @cached_property
    def root(self):
        """Root of the document after applying revision markup resolution."""
        return self.doc.resolved

    @cached_property
    def rows(self):
        """Rows to be added to the report for this concept."""

        # Create the first row.
        Cell = self.control.Reporter.Cell
        row = [Cell(self.__id, rowspan=self.rowspan)]
        if self.names:
            row.append(self.names[0].english_cell)
            if self.control.spanish:
                if self.names[0].spanish:
                    row.append(self.names[0].spanish[0])
                else:
                    row.append("")
        else:
            row.append("")
            if self.control.spanish:
                row.append("")
        if self.english_definitions:
            definition = self.english_definitions[0].text
        else:
            definition = ""
        row.append(Cell(definition, rowspan=self.name_rows))
        if self.control.spanish:
            if self.spanish_definitions:
                definition = self.spanish_definitions[0].text
            else:
                definition = ""
            row.append(Cell(definition, rowspan=self.name_rows))
        rows = [row]

        # Add rows for the rest of the names.
        if self.names:
            for name in self.names[0].spanish[1:]:
                rows.append([name])
            for name in self.names[1:]:
                row = [name.english_cell]
                if self.control.spanish:
                    row.append(name.spanish[0] if name.spanish else "")
                rows.append(row)
                for spanish in name.spanish[1:]:
                    rows.append([spanish])

        # Add rows for the extra definitions.
        for i in range(1, self.definition_rows):
            if i < len(self.english_definitions):
                row = [Cell(self.english_definitions[i].text)]
            else:
                row = [""]
            if self.control.spanish:
                if i < len(self.spanish_definitions):
                    row.append(Cell(self.spanish_definitions[i].text))
                else:
                    row.append("")
            rows.append(row)

        return rows

    @cached_property
    def rowspan(self):
        """How many rows in total will be generated for this concept doc?"""

        rowspan = self.name_rows or 1
        if self.definition_rows > 1:
            rowspan += self.definition_rows - 1
        return rowspan

    @cached_property
    def spanish_definitions(self):
        """Spanish definitions for the concept needed for the report."""

        spanish_definitions = []
        for node in self.root.findall("TranslatedTermDefinition"):
            definition = Definition(self, node)
            if self.audience in definition.audiences:
                spanish_definitions.append(definition)
        return spanish_definitions


class Name:
    """Information collected from one CDR GlossaryTermName document."""

    def __init__(self, concept, id):
        """Remember the caller's values.

        Pass:
            concept - access to the control object and the linked concept info
            id - integer for the CDR document's unique ID
        """

        self.__concept = concept
        self.__id = id

    @cached_property
    def blocked(self):
        """Is this term marked as inactive?"""
        return self.doc.active_status == Doc.BLOCKED

    @cached_property
    def concept(self):
        """Access to the control object and the linked concept info."""
        return self.__concept

    @cached_property
    def control(self):
        """Access to the current login session and the report options."""
        return self.concept.control

    @cached_property
    def doc(self):
        """`Doc` object for the GlossaryTermName document."""

        opts = dict(id=self.__id, level=Control.REVISION_LEVEL)
        return Doc(self.control.session, **opts)

    @cached_property
    def english(self):
        """The term name we'll use for placeholders in English definitions.

        Note that this property is a single string, whereas `spanish`
        is a sequence.
        """

        node = self.root.find("TermName/TermNameString")
        return Doc.get_text(node, "").strip()

    @cached_property
    def english_cell(self):
        """What goes in the cell for the doc's English name.

        English and Spanish names are handled differently. For one
        thing, a GlossaryTermName document can have only one English
        name string, but an unlimited number of Spanish name strings,
        so we'll need a 'rowspan' attribute to make the table cells
        line up. For another thing, we add the pronunciation string
        to the English name (if we're not also displaying Spanish
        term name strings and definitions), whereas we don't do that
        for Spanish term name strings (in fact, the schema doesn't
        even provide for pronunciation strings of Spanish names,
        presumably because Spanish pronunciation is easier to figure
        out without assistance than English -- if you ignore the regional
        variations). Finally, if a GlossaryTermName document is blocked,
        we convey that information only in the cell for the English
        name. So we need markup for the English name string's cell,
        but plain strings are sufficient for the Spanish names. That's
        why there is no spanish_cells property.
        """

        name = self.english
        if self.pronunciation:
            name = f"{name} ({self.pronunciation})"
        if self.blocked:
            B = self.control.HTMLPage.B
            blocked = B.SPAN("[Blocked]", B.CLASS("error"))
            name = B.SPAN(f"{name} ", blocked)
        rowspan = len(self.spanish) or None
        Cell = self.control.Reporter.Cell
        return Cell(name, rowspan=rowspan)

    @cached_property
    def pronunciation(self):
        """Crude representation of the way the English name is spoken."""

        path = "TermName/TermPronunciation"
        return Doc.get_text(self.root.find(path), "").strip() or None

    @cached_property
    def replacements(self):
        """Dictionary of values for definition placeholders."""

        replacements = {}
        for node in self.root.findall("ReplacementText"):
            replacements[node.get("name")] = Doc.get_text(node, "")
        return replacements

    @cached_property
    def root(self):
        """Root of the document after applying revision markup resolution."""
        return self.doc.resolved

    @cached_property
    def spanish(self):
        """Possibly empty sequence of Spanish term name strings."""

        spanish = []
        if self.control.spanish:
            path = "TranslatedName/TermNameString"
            for node in self.root.findall(path):
                name = Doc.get_text(node, "").strip()
                if name:
                    spanish.append(name)
        return spanish


class Definition:
    """Object for a glossary term definition (English or Spanish)."""

    def __init__(self, concept, node):
        """Remember the caller's values.

        Pass:
            concept - access to the replacement values and report options
            node - portion of the document where this definition was found
        """

        self.__concept = concept
        self.__node = node

    @cached_property
    def audiences(self):
        """Set of strings ("patient" and/or "health professional")."""

        audiences = set()
        for node in self.__node.findall("Audience"):
            audiences.add(Doc.get_text(node, "").lower())
        return audiences

    @cached_property
    def replacements(self):
        """Dictionary of substitutions for placeholders in the definition."""

        replacements = {}
        for node in self.__node.findall("ReplacementText"):
            replacements[node.get("name")] = Doc.get_text(node, "")
        if self.__concept.names:
            name = self.__concept.names[0]
            replacements.update(name.replacements)
        return replacements

    @cached_property
    def term_name(self):
        """Name to be used for definition placeholder substitutions."""

        if self.__concept.names:
            name = self.__concept.names[0]
            if self.__node.tag == "TermDefinition":
                return name.english
            elif name.spanish:
                return name.spanish[0]
        return None

    @cached_property
    def text(self):
        """Resolved definition ready to be plugged into the report."""

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
        return B.SPAN(*pieces) if spans else "".join(pieces)

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
