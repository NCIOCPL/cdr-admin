#!/usr/bin/env python

"""Show glossary documents (concept and name) for a given processing status.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc, Doctype


class Control(Controller):

    SUBTITLE = "Glossary Processing Status Report"
    AUDIENCES = "Patient", "Health professional"
    STATUS_PATH = "ProcessingStatuses/ProcessingStatus/ProcessingStatusValue"
    CONCEPT_STATUS_PATH = f"/GlossaryTermConcept/{STATUS_PATH}"
    NAME_STATUS_PATH = f"/GlossaryTermName/{STATUS_PATH}"
    INSTRUCTIONS = (
        "All fields are required. The option to include linked glossary "
        "documents causes the report to include glossary term concept "
        "documents which do not have the selected status but are linked "
        "by at least one glossary term name document which does have "
        "that status. It also causes the inclusion of glossary term name "
        "documents which do not have the selected status but whose concept "
        "document has that status."
    )
    INCLUDE_LINKED_OPTS = (
        (
            "no",
            "Show only documents with selected status",
            True,
        ),
        (
            "yes",
            "Also show linked glossary documents with other statuses",
            False,
        ),
    )
    COLUMNS = (
        "CDR ID",
        "Processing Status",
        "Last Comment",
        "Term Names",
        "Processing Status",
        "Last Comment",
    )

    def build_tables(self):
        """Assemble the table for the report."""
        return self.Reporter.Table(self.rows, columns=self.COLUMNS)

    def populate_form(self, page):
        """Add the fields to the request form for the report.

        Pass:
            page - HTMLPage object where we put the fields
        """

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)
        fieldset = page.fieldset("Select Processing Status")
        fieldset.append(page.select("status", options=self.statuses))
        page.form.append(fieldset)
        fieldset = page.fieldset("Include Linked Glossary Documents?")
        for value, label, checked in self.INCLUDE_LINKED_OPTS:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("all", **opts))
        page.form.append(fieldset)
        self.add_language_fieldset(page)
        self.add_audience_fieldset(page)

    @cached_property
    def audience(self):
        """Audience selected for the report."""

        self._audience = self.fields.getvalue("audience", "Patient")
        if self._audience not in self.AUDIENCES:
            self.bail()
        return self._audience

    @cached_property
    def concepts(self):
        """Dictionary of glossary concepts to be included on the report."""

        concepts = {}
        query = self.Query("query_term", "doc_id AS id").unique()
        query.where(f"path = '{self.CONCEPT_STATUS_PATH}'")
        query.where(query.Condition("value", self.status))
        for row in query.execute(self.cursor).fetchall():
            concept = Concept(self, row.id)
            if concept.status == self.status:
                concepts[row.id] = concept
        query = self.Query("query_term", "doc_id AS id").unique()
        query.where(f"path = '{self.NAME_STATUS_PATH}'")
        query.where(query.Condition("value", self.status))
        for row in query.execute(self.cursor).fetchall():
            name = Name(self, row.id)
            if name.status == self.status and name.concept_id:
                concept = concepts.get(name.concept_id)
                if concept is None:
                    concept_id = name.concept_id if self.show_all else None
                    concept = Concept(self, concept_id)
                    concepts[name.concept_id] = concept
                concept.names[row.id] = name
        if self.show_all:
            query = self.Query("query_term", "doc_id AS id").unique()
            query.where(f"path = '{Name.CONCEPT_PATH}'")
            query.where(query.Condition("int_val", 0))
            query = str(query)
            for id in concepts:
                concept = concepts[id]
                if concept.doc:
                    for row in self.cursor.execute(query, id).fetchall():
                        if row.id not in concept.names:
                            concept.names[row.id] = Name(self, row.id, id)
        return concepts

    @cached_property
    def language(self):
        """Language selected for the report."""

        language = self.fields.getvalue("language", "English")
        if language not in self.LANGUAGES:
            self.bail()
        return language

    @cached_property
    def report(self):
        """Inject spanned header cells."""

        report = super().report
        thead = report.page.main.find(".//thead")
        if thead is not None:
            B = self.HTMLPage.B
            tr = B.TR(
                B.TH("Glossary Term Concept", colspan="3"),
                B.TH("Glossary Term Name", colspan="3")
            )
            thead.insert(0, tr)
        return report

    @cached_property
    def report_css(self):
        """Customization for the table's style rules."""

        return (
            ".alt { color: red; }\n"
            ".usa-table td { vertical-align: top; }\n"
        )

    @cached_property
    def rows(self):
        """Collect the table rows for the report."""

        rows = []
        for id in sorted(self.concepts):
            rows += self.concepts[id].rows
        return rows

    @cached_property
    def show_all(self):
        """True means include docs linked from terms with the status."""
        return self.fields.getvalue("all") == "yes"

    @cached_property
    def spanish_names(self):
        """True if we should show Spanish term names instead of English."""
        return "spanish" in self.status.lower()

    @cached_property
    def status(self):
        """Processing status selected for the report."""

        status = self.fields.getvalue("status")
        if status and status not in self.statuses:
            self.bail()
        return status

    @cached_property
    def statuses(self):
        """Valid values for the processing status picklist."""

        values = set()
        for name in ("GlossaryTermName", "GlossaryTermConcept"):
            doctype = Doctype(self.session, name=name)
            # pylint: disable-next=unsubscriptable-object
            values |= set(doctype.vv_lists["ProcessingStatusValue"])
        return sorted(values, key=str.lower)

    @cached_property
    def wide_css(self):
        """Make room for the report's wider table."""
        return self.Reporter.Table.WIDE_CSS


class GlossaryTermDocument:
    """Base class for Concepts and Names."""

    STATUS_PATH = "ProcessingStatuses/ProcessingStatus/ProcessingStatusValue"

    @cached_property
    def doc(self):
        """`Doc` object for this CDR GlossaryConceptName document."""

        doc = Doc(self.control, id=self.id) if self.id else None
        if doc and not doc.root is not None:
            message = f"CDR{self.id} has no parsed XML."
            self.control.alerts.append(dict(message=message, type="warning"))
        return doc

    @cached_property
    def status(self):
        """First processing status found for the document."""

        if self.doc and self.doc.root is not None:
            for node in self.doc.root.findall(self.STATUS_PATH):
                status = Doc.get_text(node, "").strip()
                if status:
                    return status
        return None


class Concept(GlossaryTermDocument):
    """Glossary term concept document included on the report."""

    def __init__(self, control, id):
        """Remember the caller's values.

        Pass:
            control - access to the database and report-creation tools
            id - integer for the concept document (None if the concept
                 doesn't have the selected status but at least one of
                 its linked names does)
        """

        self.__control = control
        self.__id = id

    @cached_property
    def comment(self):
        """Comment for the definition for the selected language/audience."""

        if self.doc and self.doc.root is not None:
            control = self.__control
            tag = "TermDefinition"
            if control.language != "English":
                tag = "TranslatedTermDefinition"
            for definition in self.doc.root.findall(tag):
                audience = Doc.get_text(definition.find("Audience"))
                if audience == control.audience:
                    comment_node = definition.find("Comment")
                    if comment_node is not None:
                        return Comment(comment_node)
        return None

    @cached_property
    def control(self):
        """Access to the report's options and report-building tools."""
        return self.__control

    @cached_property
    def id(self):
        """Integer for this document's CDR ID."""
        return self.__id

    @cached_property
    def names(self):
        """Dictionary of linked GTN documents (populated by controller)."""
        return {}

    @cached_property
    def rows(self):
        """Assemble this concept's rows for the report."""

        names = [self.names[id] for id in sorted(self.names)]
        rowspan = max(len(names), 1)
        Cell = self.__control.Reporter.Cell
        rows = [(
            Cell(self.doc.id if self.doc else None, rowspan=rowspan),
            Cell(self.status, rowspan=rowspan),
            Cell(self.comment, rowspan=rowspan),
            names[0].names if names else None,
            names[0].status if names else None,
            names[0].comment if names else None,
        )]
        for name in names[1:]:
            rows.append((
                name.names,
                name.status,
                name.comment,
            ))
        return rows


class Name(GlossaryTermDocument):
    """GlossaryTermName document to be included on the report."""

    CONCEPT_PATH = "/GlossaryTermName/GlossaryTermConcept/@cdr:ref"

    def __init__(self, control, name_id, concept_id=None):
        """Remember the caller's values.

        Pass:
            control - access to the report options and report-building tools
            id - integer for this document's unique CDR ID
            concept_id - optional integer for the concept document
        """

        self.__control = control
        self.__name_id = name_id
        self.__concept_id = concept_id

    @cached_property
    def comment(self):
        """First comment found for the report's selected language."""

        if not self.doc or not self.doc.root:
            return None
        path = "TermName/Comment"
        if self.control.language != "English":
            path = "TranslatedName/Comment"
        node = self.doc.root.find(path)
        if node is not None:
            return Comment(node)
        return None

    @cached_property
    def concept_id(self):
        """Integer for the linked GlossaryTermConcept document.

        If the call the the constructor already gave us this value,
        use it. Otherwise find it using the query_term table.
        """

        if not self.doc:
            return None
        if self.__concept_id is not None:
            return self.__concept_id
        query = self.control.Query("query_term", "int_val")
        query.where(f"path = '{self.CONCEPT_PATH}'")
        query.where(query.Condition("doc_id", self.doc.id))
        rows = query.execute(self.control.cursor).fetchall()
        return rows[0].int_val if rows else None

    @cached_property
    def control(self):
        """Access to the report's options and report-building tools."""
        return self.__control

    @cached_property
    def id(self):
        """Integer for this document's CDR ID."""
        return self.__name_id

    @cached_property
    def names(self):
        """Show the appropriate names for the document."""

        if self.control.spanish_names and self.spanish_names:
            B = self.control.HTMLPage.B
            names = B.SPAN(self.spanish_names[0].span)
            for name in self.spanish_names[1:]:
                names.append(B.SPAN("; "))
                names.append(name.span)
            names.append(B.SPAN(f" (CDR{self.doc.id})"))
            return names
        else:
            return f"{self.english_name} (CDR{self.doc.id})"

    @cached_property
    def english_name(self):
        """String for the only English name in this document."""

        if not self.doc or not self.doc.root:
            return "[NO NAME]"
        node = self.doc.root.find("TermName/TermNameString")
        return Doc.get_text(node, "").strip() or "[NO NAME]"

    @cached_property
    def spanish_names(self):
        """At most one primary and other optional alternate Spanish names."""

        if not self.doc or not self.doc.root:
            return []
        spanish_names = []
        for node in self.doc.root.findall("TranslatedName"):
            spanish_name = SpanishNameString(self.control, node)
            spanish_names.append(spanish_name)
        return spanish_names


class SpanishNameString:
    """Special handling for Spanish names, to identify the alternates."""

    def __init__(self, control, node):
        """Save the caller's values.

        Pass:
            control - access to report-building tools
            node - wrapper for the name string
        """

        self.__control = control
        self.__node = node

    @cached_property
    def span(self):
        """HTML span element wrapping the display of this Spanish name."""

        text = Doc.get_text(self.__node.find("TermNameString"), "")
        span = self.__control.HTMLPage.B.SPAN(text)
        if self.__node.get("NameType") == "alternate":
            span.set("class", "alt")
        return span


class Comment:
    """Object which knows how to serialize a comment for the report."""

    NO_TEXT = "[NO TEXT ENTERED FOR COMMENT]"

    def __init__(self, node):
        """Remember the node which holds the comment information."""
        self.__node = node

    def __str__(self):
        """Roll up the information about the comment into one string."""
        return f"[{self.audience}; {self.date}; {self.user}] {self.text}"

    @cached_property
    def audience(self):
        """Serialization of the audience for the comment."""
        return f"audience={self.__node.get('audience', '')}"

    @cached_property
    def date(self):
        """Serialization of the date for the comment."""
        return f"date={self.__node.get('date', '')}"

    @cached_property
    def text(self):
        """String carrying the payload for the comment."""
        return Doc.get_text(self.__node, "").strip() or self.NO_TEXT

    @cached_property
    def user(self):
        """Serialization of the user who entered the comment."""
        return f"user={self.__node.get('user', '')}"


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
