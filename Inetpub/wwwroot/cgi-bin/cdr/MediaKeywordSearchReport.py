#!/usr/bin/env python

"""Find phrases in Media documents.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc, Doctype
from re import compile, IGNORECASE, UNICODE

class Control(Controller):
    """Logic manager for the report."""

    SUBTITLE = "Media Keyword Search Report"
    LOGNAME = "MediaKeywordSearchReport"
    REGEX_FLAGS = UNICODE | IGNORECASE

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
        fieldset = page.fieldset("Optionally select specific document(s)")
        fieldset.append(page.text_field("id", label="CDR ID"))
        fieldset.append(page.text_field("title", label="Title"))
        page.form.append(fieldset)
        fieldset = page.fieldset("Optionally narrow by processing status")
        fieldset.append(page.select("status", options=self.statuses))
        page.form.append(fieldset)
        fieldset = page.fieldset("Optionally narrow by language")
        fieldset.append(page.checkbox("language", value="English"))
        opts = dict(value="Spanish", checked=True)
        fieldset.append(page.checkbox("language", **opts))
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
    def columns(self):
        """Headers for the report's table."""

        return (
            self.Reporter.Column("CDR ID", width="75px"),
            self.Reporter.Column("Title", width="400px"),
            self.Reporter.Column("Terms", width="600px"),
        )

    @property
    def doc_ids(self):
        """Media document IDs matched by preliminary filtering."""

        if not hasattr(self, "_doc_ids"):
            doc_id = self.fields.getvalue("id")
            if doc_id:
                try:
                    doc_id = Doc.extract_id(doc_id)
                except:
                    self.bail("Invalid document ID")
                query = self.Query("active_doc", "COUNT(*)")
                query.where(query.Condition("id", doc_id))
                count = query.execute(self.cursor()).fetchone()[0]
                if count != 1:
                    self.bail(f"CDR{doc_id} is not an active CDR document")
                self._doc_ids = [doc_id]
            else:
                query = self.Query("active_doc a", "a.id", "a.title").unique()
                if self.fragment:
                    fragment = self.fragment
                    query.where(query.Condition("a.title", fragment, "LIKE"))
                if self.language == "English":
                    query.outer("query_term t", "t.doc_id = a.id",
                                "t.path = '/Media/TranslationOf/@cdr:ref'")
                    query.where("t.doc_id IS NULL")
                elif self.language == "Spanish":
                    query.join("query_term t", "t.doc_id = a.id")
                    query.where("t.path = '/Media/TranslationOf/@cdr:ref'")
                if self.language != "Spanish":
                    query.join("doc_type d", "d.id = a.doc_type")
                    query.where("d.name = 'Media'")
                query.order("title")
                rows = query.execute(self.cursor).fetchall()
                self._doc_ids = [row.id for row in rows]
            self.logger.info("identified %d document IDs", len(self._doc_ids))
        return self._doc_ids

    @property
    def fragment(self):
        """Substring for matching documents by title."""
        return self.fields.getvalue("title")

    @property
    def language(self):
        """Optional language for narrowing the report."""

        if not hasattr(self, "_language"):
            self._language = None
            languages = self.fields.getlist("language")
            if len(languages) == 1:
                self._language = languages.pop()
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
            phrases = [MediaDoc.normalize(phrase) for phrase in self.terms]
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
            self._rows = []
            for doc_id in self.doc_ids:
                doc = MediaDoc(self, doc_id)
                if doc.inscope:
                    self._rows += doc.rows
        return self._rows

    @property
    def status(self):
        """Status value selected for narrowing the report's scope."""

        if not hasattr(self, "_status"):
            self._status = self.fields.getvalue("status")
        return self._status

    @property
    def statuses(self):
        """Valid values for the processing status picklist."""

        if not hasattr(self, "_statuses"):
            doctype = Doctype(self.session, name="Media")
            statuses = doctype.vv_lists.get("ProcessingStatusValue", [])
            self._statuses = [""] + sorted(statuses)
        return self._statuses

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


class MediaDoc:
    """CDR Media document which knows how to find specific phrases."""

    BLOCKS = "MediaTitle", "MediaCaption", "ContentDescription", "LabelName"
    WHITESPACE = compile(r"\s+")
    STATUS = "ProcessingStatuses/ProcessingStatus/ProcessingStatusValue"

    def __init__(self, control, doc_id):
        """Capture the caller's values.

        Pass:
          control - access to the database and the user's report criteria
          doc_id - integer for the CDR Media document's unique identifier
        """

        self.__control = control
        self.__doc_id = doc_id

    @property
    def doc(self):
        """Object with access to the document's DOM node."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.__control.session, id=self.__doc_id)
        return self._doc

    @property
    def inscope(self):
        """True if the document meets the user's filtering criteria."""

        if not hasattr(self, "_inscope"):
            self._inscope = True
            if self.__control.status:
                if self.__control.status != self.status:
                    self._inscope = False
            if self._inscope and self.__control.language:
                if self.__control.language != self.language:
                    self._inscope = False
        return self._inscope

    @property
    def language(self):
        """English or Spanish."""

        if not hasattr(self, "_language"):
            self._language = "English"
            if self.doc.root.findall("TranslationOf"):
                self._language = "Spanish"
        return self._language

    @property
    def rows(self):
        """Rows for the report's table."""

        if not hasattr(self, "_rows"):
            self._rows = []
            for block in self.textblocks:
                matches = [m for m in self.__control.regex.finditer(block)]
                if matches:
                    position = 0
                    segments = []
                    for match in matches:
                        start, end = match.span()
                        if start > position:
                            segments.append(block[position:start])
                        #segments.append("***")
                        #segments.append(">>>>")
                        segments.append("\u25b6")
                        #segments.append("\u2b1b\u25b6")
                        segments.append(block[start:end])
                        #segments.append("***")
                        #segments.append("<<<<")
                        segments.append("\u25c0")
                        #segments.append("\u25c0\u2b1b")
                        position = end
                    if position < len(block):
                        segments.append(block[position:])
                    row = self.doc.id, self.doc.title, "".join(segments)
                    self._rows.append(row)
        return self._rows

    @property
    def status(self):
        """Most recent processing status."""

        if not hasattr(self, "_status"):
            if self.doc.root is None:
                self.__control.bail(f"{self.doc.cdr_id} is malformed")
            element = self.doc.root.find(self.STATUS)
            self._status = Doc.get_text(element)
        return self._status

    @property
    def textblocks(self):
        """List of portions of the document to be searched for term matches."""

        if not hasattr(self, "_textblocks"):
            self._textblocks = []
            for tag in self.BLOCKS:
                if self.doc.root is None:
                    self.__control.bail(f"{self.doc.cdr_id} is malformed")
                for element in self.doc.root.iter(tag):
                    block = Doc.get_text(element, "").strip()
                    if block:
                        self._textblocks.append(self.normalize(block))
        return self._textblocks

    @staticmethod
    def normalize(me):
        """
        Reduce contiguous sequences of whitespace to single spaces

        Pass:
          me - string to be normalized

        Return:
          processed string
        """

        return MediaDoc.WHITESPACE.sub(" ", me)



if __name__ == "__main__":
    """Don't execute if loaded as a module."""
    Control().run()
