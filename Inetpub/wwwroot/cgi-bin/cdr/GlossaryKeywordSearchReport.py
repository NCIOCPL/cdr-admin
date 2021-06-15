#!/usr/bin/env python

"""Find phrases in Glossary documents.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc, Doctype
from lxml import etree
from re import compile, IGNORECASE, UNICODE

import sys, os

class Control(Controller):
    """Logic manager for the report."""

    SUBTITLE = "Glossary Keyword Search Report"
    LOGNAME = "GlossaryKeywordSearchReport"
    REGEX_FLAGS = UNICODE | IGNORECASE
    CONCEPT_PATH = "/GlossaryTermName/GlossaryTermConcept/@cdr:ref"

    def build_tables(self):
        """Assemble the report."""

        if not self.terms:
            self.bail("No search terms specified")
        return self.Reporter.Table(self.rows, columns=self.columns)

    def populate_form(self, page):
        """Put the fields on the form.

        Pass:
            page   - `cdrcgi.HTMLPage` object
        """

        # Put up the field sets
        fieldset = page.fieldset("Report Filters")
        languages = "Any", "English", "Spanish"
        opts = dict(options=languages, default="Spanish")
        fieldset.append(page.select("language", **opts))
        audiences = "Any", "Patient", "Health professional"
        opts = dict(options=audiences, default="Patient")
        fieldset.append(page.select("audience", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Enter Search Terms", id="search-terms")
        fieldset.append(page.text_field("term", classes="term"))
        page.form.append(fieldset)
        page.add_output_options(default="html")

        # Button/script for adding new search term fields.
        page.add_css(".term-button { padding-left: 10px; }")
        page.add_script("""\
function add_button() {
  green_button().insertAfter(jQuery(".term").first());
}
function green_button() {
  var span = jQuery("<span>", {class: "term-button"});
  var img = jQuery("<img>", {
    src: "/images/add.gif",
    onclick: "add_term_field()",
    class: "clickable",
    title: "Add another term"
  });
  span.append(img);
  return span;
}
function add_term_field() {
  var id = "term-" + (jQuery(".term").length + 1);
  var field = jQuery("<div>", {class: "labeled-field"});
  field.append(jQuery("<label>", {for: id, text: "Term"}));
  field.append(jQuery("<input>", {class: "term", name: "term", id: id}));
  jQuery("#search-terms").append(field);
}
jQuery(document).ready(function() {
  add_button();
});""")

    @property
    def audience(self):
        """Optional audience for narrowing the report."""

        if not hasattr(self, "_audience"):
            self._audience = self.fields.getvalue("audience")
        return self._audience

    @property
    def columns(self):
        """Headers for the report's table."""

        return (
            self.Reporter.Column("GTN ID", width="75px"),
            self.Reporter.Column("GTC ID", width="75px"),
            self.Reporter.Column("Term Names", width="400px"),
            self.Reporter.Column("Definitions", width="600px"),
        )

    @property
    def docs(self):
        """Sequence of GlossaryDoc objects containing the user's term(s)."""

        if not hasattr(self, "_docs"):
            self._docs = []
            query = self.Query("pub_proc_cg p", "p.id", "c.int_val", "p.xml")
            query.join("query_term_pub c", "c.doc_id = p.id")
            query.where(query.Condition("c.path", self.CONCEPT_PATH))
            row = query.execute(self.cursor).fetchone()
            while row:
                doc = GlossaryDoc(self, row.id, row.int_val, row.xml)
                if doc.row:
                    self._docs.append(doc)
                row = self.cursor.fetchone()
        return self._docs

    @property
    def language(self):
        """Optional language for narrowing the report."""

        if not hasattr(self, "_language"):
            self._language = None
            language = self.fields.getvalue("language")
            if language in ("English", "Spanish"):
                self._language = language
        return self._language

    @property
    def regex(self):
        """
        Create a compiled regular expression for finding the caller's phrases.

        The ugly wrapper surrounding the phrases ensures that we
        match on word boundaries, so that (for example) "breast"
        isn't matched in the phrase "they were walking abreast."

        Escape characters which have special meaning in a regular expression.

        We also make sure that Microsoft doesn't mess up the matching
        when it replaces apostrophes with "smart quotes" (as it frequently
        does).
        """

        if not hasattr(self, "_regex"):
            phrases = [GlossaryDoc.normalize(phrase) for phrase in self.terms]
            phrases = sorted(phrases, key=len, reverse=True)
            expressions = []
            for phrase in phrases:
                expressions.append(phrase
                                   .replace("\\", r"\\")
                                   .replace("+",  r"\+")
                                   .replace(" ",  r"\s+")
                                   .replace(".",  r"\.")
                                   .replace("^",  r"\^")
                                   .replace("$",  r"\$")
                                   .replace("*",  r"\*")
                                   .replace("?",  r"\?")
                                   .replace("{",  r"\{")
                                   .replace("}",  r"\}")
                                   .replace("[",  r"\[")
                                   .replace("]",  r"\]")
                                   .replace("|",  r"\|")
                                   .replace("(",  r"\(")
                                   .replace(")",  r"\)")
                                   .replace("'",  "['\u2019]"))
            expressions = "|".join(expressions)
            expression = f"(?<!\\w)({expressions})(?!\\w)"
            self._regex = compile(expression, self.REGEX_FLAGS)
        return self._regex

    @property
    def rows(self):
        """Rows for the report's table."""

        if not hasattr(self, "_rows"):
            self._rows = [doc.row for doc in sorted(self.docs)]
        return self._rows

    @property
    def terms(self):
        """Phrases to look for."""

        if not hasattr(self, "_terms"):
            self._terms = []
            for term in self.fields.getlist("term"):
                term = term.strip()
                if term:
                    self._terms.append(term)
        return self._terms


class GlossaryDoc:
    """CDR Glossary document which knows how to find specific phrases."""

    WHITESPACE = compile(r"\s+")
    AUDIENCES = {"Patient", "Health professional"}

    def __init__(self, control, gtn_id, gtc_id, xml):
        """Look for matches with the user's term phrases.

        Sets `self.row` if any matches found. Otherwise `self.row` is `None`.
        The constructor assembles the calculated values because we don't
        want the original document retained in memory, as it would be if
        we were using `@property` to calculate those values as needed.

        Pass:
          control - access to the database and the user's report criteria
          gtn_id - integer for the CDR GlossaryTermName document's unique ID
          gtc_id - integer for the CDR GlossaryTermConcept document's ID
          xml - filtered GlossaryTerm document exported to cancer.gov
        """

        self.control = control
        self.row = None
        self.matched = False
        try:
            root = etree.fromstring(xml.encode("utf-8"))
        except Exception:
            control.logger.exception("parsing CDR%d", gtn_id)
            root = None
        if root is not None:
            self.sort_key = self.__get_sort_key(root)
            names = self.__get_names(root)
            definitions = self.__get_definitions(root)
            if self.matched:
                self.row = gtn_id, gtc_id, names, definitions

    def __lt__(self, other):
        """Support sorting the documents by term name."""
        return self.sort_key < other.sort_key

    def __get_sort_key(self, root):
        """Find the name in the appropriate language for sorting.

        Pass:
            root - parsed export document

        Return:
            English or Spanish term name used for sorting
        """

        path = "TermName"
        if self.control.language == "Spanish":
            path = "SpanishTermName"
        return Doc.get_text(root.find(path), "").strip().lower()

    def __get_names(self, root):
        """Assemble the term's names.

        Only get the ones matching the user's language. If any match any
        of the user's terms, highlight the match and set `self.matched`
        to `True`.

        Pass:
            root - parsed export document

        Return:
            sequence of term name strings
        """

        if self.control.language == "English":
            paths = ["TermName"]
        elif self.control.language == "Spanish":
            paths = ["SpanishTermName"]
        else:
            paths = ["TermName", "SpanishTermName"]
        names = []
        for path in paths:
            for node in root.findall(path):
                text = Doc.get_text(node, "").strip()
                if text:
                    text = self.normalize(text)
                    name = self.__add_highlights(text)
                    if name != text:
                        self.matched = True
                    names.append(name)
        return names

    def __get_definitions(self, root):
        """Assemble the term's definitions.

        Only get the ones matching the user's language and audience.
        If any contain matches for any of the user's terms, highlight
        the match and set `self.matched` to `True`.

        Pass:
            root - parsed export document

        Return:
            sequence of term definition strings
        """

        if self.control.language == "English":
            paths = ["TermDefinition"]
        elif self.control.language == "Spanish":
            paths = ["SpanishTermDefinition"]
        else:
            paths = ["TermDefinition", "SpanishTermDefinition"]
        definitions = []
        for path in paths:
            for node in root.findall(path):
                if self.control.audience in self.AUDIENCES:
                    audience = Doc.get_text(node.find("Audience"), "").strip()
                    if audience != self.control.audience:
                        continue
                text = Doc.get_text(node.find("DefinitionText"), "").strip()
                if text:
                    text = self.normalize(text)
                    definition = self.__add_highlights(text)
                    if definition != text:
                        self.matched = True
                        definitions.append(definition)
        return definitions

    def __add_highlights(self, text):
        """Highlight matches with the user's target strings.

        Pass:
            text - original string for term name or definition

        Return:
            possibly altered string to highlight matched term phrases
        """

        matches = [m for m in self.control.regex.finditer(text)]
        if not matches:
            return text
        position = 0
        segments = []
        for match in matches:
            start, end = match.span()
            if start > position:
                segments.append(text[position:start])
            segments.append("\u25b6")
            segments.append(text[start:end])
            segments.append("\u25c0")
            position = end
        if position < len(text):
            segments.append(text[position:])
        return "".join(segments)

    @staticmethod
    def normalize(me):
        """
        Reduce contiguous sequences of whitespace to single spaces

        Pass:
          me - string to be normalized

        Return:
          processed string
        """

        return GlossaryDoc.WHITESPACE.sub(" ", me)


if __name__ == "__main__":
    """Don't execute if loaded as a module."""
    Control().run()
