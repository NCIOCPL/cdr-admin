#!/usr/bin/env python

"""Report on terms within StandardWording and/or GlossaryTerm elements.

JIRA::OCECDR-4568
"""

from datetime import date, datetime
from io import BytesIO
from re import compile, UNICODE, IGNORECASE
from sys import stdout, exit as sysexit
from lxml import etree
from lxml.html import builder as B
from xlsxwriter import Workbook
from cdrcgi import Controller, Reporter
from cdrapi import db
from cdrapi.docs import Doc


class Control(Controller):
    """
    Logic manager for report.
    """

    SUBTITLE = "Summaries Standard Wording"
    REGEX_FLAGS = UNICODE | IGNORECASE

    def populate_form(self, page, titles=None):
        """Put the fields on the form.

        Pass:
            page   - `cdrcgi.HTMLPage` object
            titles - if not None, show the followup page for selecting
                     from multiple matches with the user's title fragment;
                     otherwise, show the report's main request form
                     (logic handled in add_summary_selection_fields())
        """

        # Default fieldsets for summaries.
        opts = {"titles": titles, "id-label": "CDR ID(s)"}
        opts["id-tip"] = "separate multiple IDs with spaces"
        self.add_summary_selection_fields(page, **opts)

        # Add initial fields for search terms (one for each term).
        fieldset = page.fieldset("Enter Search Terms", id="search-terms")
        terms = self.fields.getlist("term") or [""]
        opts = dict(classes="term")
        for term in terms:
            fieldset.append(page.text_field("term", value=term, **opts))
        page.form.append(fieldset)

        # Flag for including blocked summaries.
        fieldset = page.fieldset("Options")
        opts = dict(label="Include Blocked Documents", value="N")
        if self.blocked:
            opts["checked"] = True
        fieldset.append(page.checkbox("blocked", **opts))
        page.form.append(fieldset)

        # Section to select output format (HTML, Excel).
        page.add_output_options(default=self.format)

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

    def send_workbook(self):
        """Create and send the Excel version of the report.

        We're using the xlsxwriter package in order to support the
        requirement of inline rich text.
        """

        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = "standard-wording-{}.xlsx".format(stamp)
        output = BytesIO()
        book = Workbook(output, {"in_memory": True})
        sheet = book.add_worksheet("Matches")
        formats = dict(
            header=book.add_format(dict(bold=True, align="center")),
            center=book.add_format(dict(align="center", valign="top")),
            bold=book.add_format(dict(bold=True)),
            term=book.add_format(dict(bold=True, color="red")),
            wrap=book.add_format(dict(text_wrap=True)),
            top=book.add_format(dict(valign="top"))
        )
        title, subtitle = self.caption
        sheet.merge_range("A1:E1", title, formats["header"])
        sheet.merge_range("A2:E2", subtitle, formats["header"])
        widths = 10, 50, 30, 80, 18
        headers = ("Doc ID", "Doc Title", "Match",
                   "Context", "Standard Wording?")
        for i, width in enumerate(widths):
            sheet.set_column(i, i, width)
            sheet.write(3, i, headers[i], formats["header"])
        row = 4
        for summary in self.summaries:
            doc_id, title = summary.cdr_id, summary.title
            for match in summary.matches:
                row = match.excel_row(sheet, row, formats, doc_id, title)
                doc_id = title = ""
        book.close()
        output.seek(0)
        book_bytes = output.read()
        stdout.buffer.write(f"""\
Content-type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename={filename}
Content-length: {len(book_bytes)}

""".encode("utf-8"))
        stdout.buffer.write(book_bytes)
        sysexit(0)

    @property
    def audience(self):
        """Select summaries written for patients or health professionals."""

        if not hasattr(self, "_audience"):
            self._audience = self.fields.getvalue("audience", "Patient")
            if self._audience not in self.AUDIENCES:
                self.bail()
        return self._audience

    @property
    def board(self):
        """Sequence of IDs for the selected board(s) (or "all")."""

        if not hasattr(self, "_board"):
            ids = self.fields.getlist("board")
            self._board = []
            if ids:
                if "all" in ids:
                    self._board = ["all"]
                else:
                    boards = self.get_boards()
                    for id in ids:
                        try:
                            id = int(id)
                        except Exception:
                            self.bail()
                        if id not in boards:
                            self.bail()
                        self._board.append(id)
        return self._board

    @property
    def blocked(self):
        """Should we include blocked summaries?"""
        return True if self.fields.getvalue("blocked") else False

    @property
    def board_summaries(self):
        """`Summary` objects for the selected board(s), language."""

        b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        t_path = "/Summary/TranslationOf/@cdr:ref"
        table = "document d" if self.blocked else "active_doc d"
        query = db.Query(table, "d.id")
        query.join("query_term_pub a", "a.doc_id = d.id")
        query.where("a.path = '/Summary/SummaryMetaData/SummaryAudience'")
        query.where(query.Condition("a.value", self.audience + "s"))
        query.join("query_term_pub l", "l.doc_id = d.id")
        query.where("l.path = '/Summary/SummaryMetaData/SummaryLanguage'")
        query.where(query.Condition("l.value", self.language))
        if "all" not in self.board:
            if self.language == "English":
                query.join("query_term_pub b", "b.doc_id = d.id")
            else:
                query.join("query_term_pub t", "t.doc_id = d.id")
                query.where(query.Condition("t.path", t_path))
                query.join("query_term b", "b.doc_id = t.int_val")
            query.where(query.Condition("b.path", b_path))
            query.where(query.Condition("b.int_val", self.board, "IN"))
        rows = query.unique().execute(self.cursor).fetchall()
        return [Summary(self, row.id) for row in rows]

    @property
    def caption(self):
        """Sequence of caption row strings for the report."""

        if not hasattr(self, "_caption"):
            top = "STANDARD WORDING REPORT"
            if self.selection_method == "board":
                top = f"{top} ({self.audience.upper()})"
            terms = "; ".join(sorted([term.lower() for term in self.terms]))
            self._caption = top, f"Search Terms: {terms}"
        return self._caption

    @property
    def cdr_id(self):
        """Set of one or more CDR document ID integers."""

        if not hasattr(self, "_cdr_id"):
            self._cdr_id = set()
            for word in self.fields.getvalue("cdr-id", "").strip().split():
                try:
                    self._cdr_id.add(Doc.extract_id(word))
                except Exception:
                    self.bail("Invalid format for CDR ID")
        return self._cdr_id

    @property
    def columns(self):
        """
        Create a sequence of column definitions for the output report.

        Number and types of columns depend on config parms.

        Return:
            Sequence of column definitions to add to object.
        """

        return (
            Reporter.Column("Doc ID", width="70px"),
            Reporter.Column("Doc Title", width="200px"),
            Reporter.Column("Match", width="100px"),
            Reporter.Column("Context", width="200px"),
            Reporter.Column("Standard Wording?", width="50px")
        )

    @property
    def default_audience(self):
        """Override the default audience."""
        return "Patient"

    @property
    def fragment(self):
        """String from the summary's title."""
        return self.fields.getvalue("title")

    @property
    def language(self):
        """Select summaries in English or Spanish."""

        if not hasattr(self, "_language"):
            self._language = self.fields.getvalue("language", "English")
            if self._language not in self.LANGUAGES:
                self.bail()
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
            phrases = [Summary.normalize(phrase) for phrase in self.terms]
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
    def report(self):
        """This report is too specialized to use the base class version.

        Take off the buttons and add the banners/titles.

        If the user chooses the "by summary title" method for
        selecting which summary to use for the report, and the
        fragment supplied matches more than one summary document,
        display the form a second time so the user can pick the
        summary.
        """

        # Make sure we have something to look for.
        if not self.terms:
            self.bail("At least one search term is required")

        # If the user wants an Excel workbook, create it.
        if self.format == "excel":
            return self.send_workbook()

        # Otherwise, assemble the options for an HTML report.
        if not hasattr(self, "_report"):
            opts = {
                "banner": "Standard Wording Report",
                "footer": self.footer,
                "subtitle": f"Report produced {date.today()}",
                "no_results": self.no_results,
                "page_opts": {
                    "buttons": [],
                    "session": self.session,
                    "action": None,
                }
            }
            self._report = Reporter(self.title, self.tables, **opts)
        return self._report

    @property
    def rows(self):
        """Assemble the rows for the HTML version of the report."""

        if not hasattr(self, "_rows"):
            self._rows = []
            for summary in self.summaries:
                doc_id, title = summary.cdr_id, summary.title
                for match in summary.matches:
                    self._rows.append(match.html_row(doc_id, title))
                    doc_id = title = ""
        return self._rows

    @property
    def summaries(self):
        """PDQ Summaries included in the report."""

        if not hasattr(self, "_summaries"):

            # See if we have more narrowing of the summary selection to do.
            if self.selection_method == "title":
                if not self.fragment:
                    self.bail("Title fragment is required.")
                if not self.summary_titles:
                    self.bail("No summaries match that title fragment")
                if len(self.summary_titles) == 1:
                    summaries = [Summary(self, self.summary_titles[0].id)]
                else:
                    buttons = [self.HTMLPage.button(b) for b in self.buttons]
                    opts = dict(
                        buttons=buttons,
                        action=self.script,
                        subtitle=self.subtitle,
                        session=self.session,
                        method=self.method,
                    )
                    page = self.HTMLPage(self.title, **opts)
                    self.populate_form(page, self.summary_titles)
                    page.send()
            elif self.selection_method == "id":
                if not self.cdr_id:
                    self.bail("At least one CDR ID is required.")
                summaries = [Summary(self, cdr_id) for cdr_id in self.cdr_id]
            else:
                if not self.board:
                    self.bail("At least one board is required.")
                summaries = self.board_summaries

            # Make sure we have something to report on.
            if not summaries:
                pattern = "No {} summaries available for selected board"
                self.bail(pattern.format(self.audience))
            self._summaries = sorted(summaries)

        return self._summaries

    @property
    def tables(self):
        """List with a single table for the HTML report."""

        if not hasattr(self, "_tables"):
            opts = dict(
                banner=self.PAGE_TITLE,
                subtitle=self.subtitle,
                caption=self.caption,
                columns=self.columns,
            )
            self._tables = [Reporter.Table(self.rows, **opts)]
        return self._tables

    @property
    def terms(self):
        """Assemble the search terms to be matched.

        Start with the list of terms supplied by the user on the report
        request form, then expand the terms using the glossary term
        documents and the external mapping table.

        Return:
          sequence of normalized search strings
        """

        # Use the cached value if we've already done this.
        if hasattr(self, "_terms"):
            return self._terms

        # Set up the language-dependent values.
        prefix = "Spanish " if self.language == "Spanish" else ""
        name = f"{prefix}GlossaryTerm Phrases"
        query = db.Query("external_map_usage", "id")
        query.where(query.Condition("name", name))
        usage = query.execute(self.cursor).fetchone().id
        prefix = "Translated" if self.language == "Spanish" else "Term"
        path = f"/GlossaryTermName/{prefix}Name/TermNameString"

        # Loop through the user's phrases.
        ids = set()
        terms = dict()
        for term in self.fields.getlist("term"):
            if term and term.strip():

                # See if the term matches a glossary term name document.
                term = Summary.normalize(term).strip()
                query = db.Query("query_term", "doc_id")
                query.where(query.Condition("path", path))
                query.where(query.Condition("value", term))
                row = query.execute(self.cursor).fetchone()
                doc_id = row.doc_id if row else None

                # If not, see if the term is in the variant mapping table.
                if not doc_id:
                    query = db.Query("external_map", "doc_id")
                    query.where(query.Condition("usage", usage))
                    query.where(query.Condition("value", term))
                    row = query.execute(self.cursor).fetchone()
                    doc_id = row.doc_id if row else None

                # If we have a glossary term, pull in its names.
                if doc_id:
                    if doc_id not in ids:
                        ids.add(doc_id)
                        query = db.Query("query_term", "value")
                        query.where(query.Condition("path", path))
                        query.where(query.Condition("doc_id", doc_id))
                        for row in query.execute(self.cursor).fetchall():
                            if row.value and row.value.strip():
                                value = Summary.normalize(row.value).strip()
                                terms[value.lower()] = value
                        query = db.Query("external_map", "value")
                        query.where(query.Condition("usage", usage))
                        query.where(query.Condition("doc_id", doc_id))
                        for row in query.execute(self.cursor).fetchall():
                            if row.value and row.value.strip():
                                value = Summary.normalize(row.value).strip()
                                terms[value.lower()] = value

                # If we didn't find a matching glossary term, use the phrase.
                else:
                    terms[term.lower()] = term

        self._terms = sorted(terms.values())
        return self._terms


class Summary:
    """Information from a single PDQ summary for the report

    Properties:
      cdr_id - unique ID for the summary document
      title - plain text title for the summary
      root - parsed document object, streamlined for the report
    """

    WHITESPACE = compile(r"\s+")
    DROP = (
        "CitationLink",
        "Comment",
        "Deletion",
        "KeyPoint",
        "MiscellaneousDocLink",
        "ResponseToComment",
        "SecMetaData",
    )
    STRIP = (
        "Caption",
        "Emphasis",
        "ExternalRef",
        "FigureNumber",
        "ForeignWord",
        "GeneName",
        "GlossaryTermLink",
        "GlossaryTermRef",
        "Insertion",
        "InterventionName",
        "LOERef",
        "MediaID",
        "MediaLink",
        "Note",
        "ProtocolLink",
        "ProtocolRef",
        "ReferencedFigureNumber",
        "ReferencedTableNumber",
        "ScientificName",
        "Strong",
        "Subscript",
        "SummaryFragmentRef",
        "SummaryRef",
        "Superscript",
        "TT",
    )

    def __init__(self, control, cdr_id):
        """
        Capture the initial summary values

        Pass:
          control - access to cursor, logging, etc.
          cdr_id - unique ID for the summary document
        """

        self.cdr_id = cdr_id
        self.__control = control

    def __lt__(self, other):
        """Support sorting of the `Summary` objects."""
        return self.title < other.title

    @property
    def root(self):
        """Fetch and parse xml and clean up unwanted elements/markup"""
        if not hasattr(self, "_root"):
            query = db.Query("document", "xml")
            query.where(query.Condition("id", self.cdr_id))
            xml = query.execute(self.__control.cursor).fetchone().xml
            self._root = etree.fromstring(xml.encode("utf-8"))
            etree.strip_elements(self._root, *self.DROP, with_tail=False)
            etree.strip_tags(self._root, *self.STRIP)
        return self._root

    @property
    def title(self):
        """Extract the summary title from the document"""
        if not hasattr(self, "_title"):
            self._title = Doc.get_text(self.root.find("SummaryTitle"))
        return self._title

    @property
    def matches(self):
        """Assemble the sequence of matches for the caller's phrases."""

        if not hasattr(self, "_matches"):
            matches = []
            regex = self.__control.regex
            for section in self.root.findall("SummarySection"):
                title = Doc.get_text(section.find("Title"))
                for node in section.iter():

                    # Look for matches in the node's text property.
                    if node.text is not None and node.text.strip():
                        normalized = self.normalize(node.text)
                        context = self.Context(node)
                        if context.wrapper is not None:
                            args = title, regex, normalized, context, matches
                            self.scan_string(*args)

                    # Do a second pass looking for matches in the node's tail.
                    if node.tail is not None and node.tail.strip():
                        normalized = self.normalize(node.tail)
                        context = self.Context(node, using_tail=True)
                        if context.wrapper is not None:
                            args = title, regex, normalized, context, matches
                            self.scan_string(*args)
            self._matches = matches
        return self._matches

    @classmethod
    def scan_string(cls, section, regex, string, context, matches):
        """
        Apply the regular expression to the caller's text string

        Pass:
          section - string for the top-level summary section's title
          regex - compiled regular expression for matching the search terms
          string - text string to be searched for matches
          matches - sequence of `Summary.Match` objects to which we append
        """

        opts = dict(standard_wording=context.in_standard_wording)
        for match in regex.finditer(string):
            start, end = match.span()
            before = string[:start]
            text = string[start:end]
            after = string[end:]
            prefix = context.prefix + before
            suffix = after + context.suffix
            matches.append(cls.Match(section, text, prefix, suffix, **opts))

    @staticmethod
    def normalize(me):
        """
        Reduce contiguous sequences of whitespace to single spaces

        Pass:
          me - string to be normalized

        Return:
          processed string
        """

        return Summary.WHITESPACE.sub(" ", me)

    class Context:
        """
        Information about the surrounding context for a match

        Note that the Context prefix and suffix may need to be combined
        with text already extracted by the caller from the node in which
        the match was found (unlike the context strings stored in the
        `Summary.Match` objects, which have the complete prefix and
        suffix).

        Note, KeyPoint, and Title were originally in the list of possible
        wrapper elements, but they have been removed.

        Properties:
          prefix - string preceding the match
          suffix - string following the match
          in_standard_wording - True if one of the ancestors is StandardWording
          wrapper - top-level node from which we extract context
        """

        OK = {"entry", "ListItem", "Para"}

        def __init__(self, node, **opts):
            """
            Assemble the context information for a match

            Required positional argument:
              node - element in which the match was found

            Optional keyword arguments:
              using_tail - True if the match came from node.tail, not node.text
            """

            self.__standard_wording = False
            if node.tag == "StandardWording" and not opts.get("using_tail"):
                self.__standard_wording = True
            self.__node = node
            self.__collector = self.__prefix = []
            self.__suffix = []
            self.__collect(self.wrapper, **opts)

        def __collect(self, node, **opts):
            """
            Recursively populate self.__suffix and self.__prefix

            Required positional argument:
              node - element in which the match was found

            Optional keyword arguments:
              using_tail - True if the match came from node.tail, not node.text
            """

            # Safety check.
            if node is None:
                return

            # Special handling for the node in which the match is found.
            if node is self.__node:

                # Only add the node's text if the match is from the tail.
                using_tail = opts.get("using_tail")
                if using_tail:
                    if node.text is not None:
                        self.__collector.append(node.text)

                # Otherwise switch to collecting the context's suffix.
                else:
                    self.__collector = self.__suffix

                # Process the node's children. Avoid recursive blocks.
                for child in node.findall("*"):
                    if child.tag not in self.OK:
                        self.__collect(child, **opts)

                # If the match was in the tail, the rest is suffix.
                if using_tail:
                    self.__collector = self.__suffix

                # Otherwise, pick up the tail if there is one.
                else:
                    if node.tail is not None:
                        self.__collector.append(node.tail)

            # Simpler processing for all the other nodes.
            else:
                if node.text is not None:
                    self.__collector.append(node.text)
                for child in node.findall("*"):
                    if child.tag not in self.OK:
                        self.__collect(child, **opts)
                if node.tail is not None:
                    self.__collector.append(node.tail)

        @property
        def prefix(self):
            """Context string appearing before matched phrase"""
            if not hasattr(self, "_prefix"):
                self._prefix = "".join(self.__prefix)
            return self._prefix

        @property
        def suffix(self):
            """Context string appearing after matched phrase"""
            if not hasattr(self, "_suffix"):
                self._suffix = "".join(self.__suffix)
            return self._suffix

        @property
        def wrapper(self):
            """
            Enclosing element from which context should be drawn

            We walk up through the ancestors of the node in which the
            match was found to find an element which represents a self-
            contained unit of free text, such as a paragraph or a list
            item (that is, one of the elements listed in `self.OK`).
            If the element in which the match was found is itself such
            an element, the property is set to that element.

            If we run into a SummarySection parent we set the wrapper
            to None, because we're not in a block which should be
            searched.

            As a side effect, we set the flag indicating whether or not
            the match is enclosed by a StandardWording block.
            """

            if not hasattr(self, "_wrapper"):
                self._wrapper = None
                if self.__node.tag in self.OK:
                    self._wrapper = self.__node
                else:
                    parent = self.__node.getparent()
                    node = None
                while self._wrapper is None and parent is not None:
                    if parent.tag == "SummarySection":
                        parent = None
                    elif parent.tag == "StandardWording":
                        self.__standard_wording = True
                    elif parent.tag in self.OK:
                        self._wrapper = parent
                    node = parent
                    parent = node.getparent() if node is not None else None
            return self._wrapper

        @property
        def in_standard_wording(self):
            """Was the match was found inside a StandardWording block?"""
            return self.__standard_wording

    class Match:
        """
        Information needed for a single row in the report

        Properties:
          section - string for the top-level section's title
          text - string for the matched phrase
          prefix - string preceding the match
          suffix - string following the match
          td - assembled HTML table cell object displaying the match in context
          standard_wording - True if match was found in a StandardWording block
        """

        def __init__(self, section, text, prefix, suffix, **opts):
            """
            Capture the caller's values

            Save assembly of the processed property values until they
            are used, so that the mapping dictionary will have all of
            the entries we need.

            Required positional arguments:
              section - string for the top-level section's title
              text - string for the matched phrase
              prefix - context string before match
              suffix - context string after match

            Optional keyword argument:
              standard_wording - the match was found in a StandardWording block
            """

            self.__section = section
            self.text = text
            self.__prefix = prefix
            self.__suffix = suffix
            self.standard_wording = opts.get("standard_wording") or False

        def excel_row(self, sheet, row, formats, doc_id, title):
            """
            Add a rows to the Excel version of the report

            Pass:
              sheet - reference to Excel worksheet object
              row - integer for the vertical position on the sheet
              formats - dictionary of styles for the data
              doc_id - integer for Summary document ID
              title - string for Summary document title

            Return:
              integer for next row position
            """

            standard_wording = "Yes" if self.standard_wording else "No"
            bold, red, wrap = formats["bold"], formats["term"], formats["wrap"]
            prefix = ' - "' + self.prefix.lstrip()
            suffix = self.suffix.rstrip() + '"'
            context = bold, self.section, prefix, red, self.text, suffix, wrap
            sheet.write(row, 0, doc_id, formats["top"])
            sheet.write(row, 1, title, formats["top"])
            sheet.write(row, 2, self.text, formats["top"])
            sheet.write_rich_string(row, 3, *context)
            sheet.write(row, 4, standard_wording, formats["center"])
            return row + 1

        def html_row(self, summary_id, summary_title):
            """
            Construct an HTML report row for this match

            Pass:
              summary_id - unique integer for the CDR summary document ID
              summary_title - string for the summary's title

            Return:
              sequence of column values for the report's row
            """

            standard_wording = self.standard_wording and "Yes" or "No"
            return [
                summary_id,
                summary_title,
                self.text,
                Reporter.Cell(self.span),
                Reporter.Cell(standard_wording, classes="center"),
            ]

        @property
        def section(self):
            """Guard against None for section title"""
            if self.__section is None:
                return "*** NO SECTION TITLE ***"
            return self.__section

        @property
        def prefix(self):
            """
            Context string appearing before match

            In some cases the users have incorrectly included leading
            whitespace inside GlossaryTermRef elements. Because that
            leading whitespace has been stripped when looking for
            matches, we need to make sure that any non-empty prefix
            string is separated from the match with a space.

            """
            if not hasattr(self, "_prefix"):
                self._prefix = Summary.normalize(self.__prefix)
                if self._prefix:
                    end = self._prefix[-1]
                    if end not in " ([":
                        self._prefix += " "
            return self._prefix

        @property
        def suffix(self):
            """
            Context string appearing after match

            If the users have incorrectly put whitespace after the matched
            term inside the GlossaryTermRef element by mistake, we may need
            to make sure the match is separated from the following context
            string by a space if appropriate.
            """

            if not hasattr(self, "_suffix"):
                self._suffix = Summary.normalize(self.__suffix)
                if self._suffix:
                    start = self._suffix[0]
                    if start.isalnum() or start in "[(":
                        self._suffix = " " + self._suffix
            return self._suffix

        @property
        def span(self):
            """Assemble the HTML cell object for the match"""
            section = B.B(self.section)
            section.tail = ' - "' + self.prefix.lstrip()
            term = B.B(self.text, B.CLASS("error"))
            term.tail = self.suffix.rstrip() + '"'
            return B.SPAN(section, term)


if __name__ == "__main__":
    """Don't execute if loaded as a module."""
    Control().run()
