#!/usr/bin/env python

"""Report on terms within StandardWording and/or GlossaryTerm elements.

JIRA::OCECDR-4568
"""

from datetime import datetime
from functools import cached_property
from io import BytesIO
from re import compile, UNICODE, IGNORECASE
from sys import stdout, exit as sysexit
from lxml import etree
from lxml.html import builder as B
from xlsxwriter import Workbook
from cdrcgi import Controller, Reporter, BasicWebPage
from cdrapi import db
from cdrapi.docs import Doc


class Control(Controller):
    """
    Logic manager for report.
    """

    SUBTITLE = "Summaries Standard Wording"
    REGEX_FLAGS = UNICODE | IGNORECASE
    INSTRUCTIONS = (
        "This report retrieves both glossary terms and free text in summary "
        "documents, indicates whether they are in Standard Wording tags "
        "or not, and groups the results in a way that allows users to go "
        "into each summary once to address all terms retrieved for the "
        "summary, instead of going into one summary multiple times for each "
        "of the terms."
    )

    def populate_form(self, page):
        """Put the fields on the form.

        Pass:
            page   - `cdrcgi.HTMLPage` object
        """

        # If we have a complete hand-crafted URL, proceed to the report.
        if self.ready:
            self.show_report()

        # Explain the report.
        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)

        # Default fieldsets for summaries.
        opts = {"titles": self.summary_titles, "id-label": "CDR ID(s)"}
        opts["id-tip"] = "separate multiple IDs with spaces"
        self.add_summary_selection_fields(page, **opts)

        # Add initial fields for search terms (one for each term).
        fieldset = page.fieldset("Enter Search Terms", id="search-terms")
        legend = fieldset.find("legend")
        add_button = page.B.SPAN(
            page.B.IMG(
                page.B.CLASS("clickable"),
                src="/images/add.gif",
                onclick="add_term_field();",
                title="Add another term"
            ),
            page.B.CLASS("term-button")
        )
        legend.append(add_button)
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
        page.head.append(page.B.SCRIPT(src="/js/SummaryStandardWording.js"))

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
X-Content-Type-Options: nosniff

""".encode("utf-8"))
        stdout.buffer.write(book_bytes)
        sysexit(0)

    def show_report(self):
        """Overridden because the table is too wide for the standard layout."""

        if not self.ready:
            self.show_form()
        if self.format == "excel":
            return self.send_workbook()
        report = BasicWebPage()
        report.wrapper.append(report.B.H1("Standard Wording Report"))
        report.wrapper.append(self.table.node)
        report.wrapper.append(self.footer)
        report.send()

    @cached_property
    def audience(self):
        """Select summaries written for patients or health professionals."""

        audience = self.fields.getvalue("audience", "Patient")
        if audience not in self.AUDIENCES:
            self.bail()
        return audience

    @cached_property
    def board(self):
        """Sequence of IDs for the selected board(s) (or ["all"])."""

        values = self.fields.getlist("board")
        if not values:
            return []
        if "all" in values:
            return ["all"]
        ids = []
        boards = self.get_boards()
        for value in values:
            try:
                id = int(value)
            except Exception:
                self.bail()
            if id not in boards:
                self.bail()
            ids.append(id)
        return ids

    @cached_property
    def blocked(self):
        """Should we include blocked summaries?"""
        return True if self.fields.getvalue("blocked") else False

    @cached_property
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
        if self.board and "all" not in self.board:
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

    @cached_property
    def caption(self):
        """Sequence of caption row strings for the report."""

        top = "STANDARD WORDING REPORT"
        if self.selection_method == "board":
            top = f"{top} ({self.audience.upper()})"
        terms = "; ".join(sorted([term.lower() for term in self.terms]))
        return top, f"Search Terms: {terms}"

    @cached_property
    def cdr_id(self):
        """String entered by the user for selection by CDR ID."""
        return self.fields.getvalue("cdr-id")

    @cached_property
    def cdr_ids(self):
        """Integers for the selected documents, populated by `ready()`."""
        return set()

    @cached_property
    def columns(self):
        """
        Create a sequence of column definitions for the output report.

        Number and types of columns depend on config parms.

        Return:
            Sequence of column definitions to add to object.
        """

        if self.format == "html":
            return (
                Reporter.Column("Doc ID", width="5%"),
                Reporter.Column("Doc Title", width="30%"),
                Reporter.Column("Match", width="10%"),
                Reporter.Column("Context", width="50%"),
                Reporter.Column("Standard Wording?", width="5%"),
            )
        return (
            Reporter.Column("Doc ID", width="70px"),
            Reporter.Column("Doc Title", width="200px"),
            Reporter.Column("Match", width="100px"),
            Reporter.Column("Context", width="200px"),
            Reporter.Column("Standard Wording?", width="50px")
        )

    @cached_property
    def default_audience(self):
        """Override the default audience."""
        return "Patient"

    @cached_property
    def fragment(self):
        """String from the summary's title."""

        if self.selection_method != "title":
            return None
        return self.fields.getvalue("title")

    @cached_property
    def language(self):
        """Select summaries in English or Spanish."""

        language = self.fields.getvalue("language", "English")
        if language not in self.LANGUAGES:
            self.bail()
        return language

    @cached_property
    def ready(self):
        """True if we have what is needed for the report."""

        # If we're just getting started, we can't be ready.
        if not self.request:
            return False

        # Check condition applicable to all selection methods.
        if not self.terms:
            message = "At least one search term is required."
            self.alerts.append(dict(message=message, type="error"))

        # Check conditions specific to the selection method chosen.
        match self.selection_method:
            case "board":
                if not self.board:
                    message = "At least one board is required."
                    self.alerts.append(dict(message=message, type="error"))
                if not self.board_summaries:
                    target = f"{self.language} {self.audience} summaries"
                    action = "to report on"
                    message = f"No {target} {action} for selected board(s)."
                    self.alerts.append(dict(message=message, type="warning"))
            case "id":
                ids = (self.cdr_id or "").strip().split()
                if not ids:
                    message = "At least one document ID is required."
                    self.alerts.append(dict(message=message, type="error"))
                for id in ids:
                    try:
                        doc = Doc(self.session, id=id)
                        doctype = doc.doctype.name
                        if doctype != "Summary":
                            message = f"CDR{doc.id} is a {doctype} document."
                            alert = dict(message=message, type="warning")
                            self.alerts.append(alert)
                        else:
                            self.cdr_ids.add(doc.id)
                    except Exception:
                        message = f"Unable to find document {id}."
                        self.logger.exception(message)
                        self.alerts.append(dict(message=message, type="error"))
            case "title":
                if not self.fragment:
                    message = "Title fragment is required."
                    self.alerts.append(dict(message=message, type="error"))
                if not self.summary_titles:
                    message = f"No summaries match {self.fragment!r}."
                    self.alerts.append(dict(message=message, type="warning"))
                if len(self.summary_titles) > 1:
                    message = f"Multiple matches found for {self.fragment}."
                    self.alerts.append(dict(message=message, type="info"))
            case _:
                # Shouldn't happen, unless a hacker is at work.
                self.bail()

        # We're ready if no alerts have been queued.
        return False if self.alerts else True

    @cached_property
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
        return compile(expression, self.REGEX_FLAGS)

    @cached_property
    def rows(self):
        """Assemble the rows for the HTML version of the report."""

        rows = []
        for summary in self.summaries:
            opts = dict(summary=summary)
            for match in summary.matches:
                rows.append(match.html_row(**opts))
                opts = {}
        return rows

    @cached_property
    def same_window(self):
        """Reduce the number of new browser tabs opened."""
        return [self.SUBMIT] if self.request else []

    @cached_property
    def summaries(self):
        """PDQ Summaries included in the report."""

        # See if we have more narrowing of the summary selection to do.
        match self.selection_method:
            case "board":
                return sorted(self.board_summaries)
            case "id":
                return sorted([Summary(self, id) for id in self.cdr_ids])
            case "title":
                return [Summary(self, self.summary_titles[0].id)]
            case _:
                self.bail()

    @cached_property
    def table(self):
        """List with a single table for the HTML report."""

        opts = dict(
            banner=self.PAGE_TITLE,
            subtitle=self.subtitle,
            caption=self.caption,
            columns=self.columns,
        )
        return Reporter.Table(self.rows, **opts)

    @cached_property
    def terms(self):
        """Assemble the search terms to be matched.

        Start with the list of terms supplied by the user on the report
        request form, then expand the terms using the glossary term
        documents and the external mapping table.

        Return:
          sequence of normalized search strings
        """

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

        return sorted(terms.values())


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
        self.control = control

    def __lt__(self, other):
        """Support sorting of the `Summary` objects."""
        return self.title < other.title

    @cached_property
    def root(self):
        """Fetch and parse xml and clean up unwanted elements/markup"""

        query = db.Query("document", "xml")
        query.where(query.Condition("id", self.cdr_id))
        xml = query.execute(self.control.cursor).fetchone().xml
        root = etree.fromstring(xml.encode("utf-8"))
        etree.strip_elements(root, *self.DROP, with_tail=False)
        etree.strip_tags(root, *self.STRIP)
        return root

    @cached_property
    def title(self):
        """Extract the summary title from the document"""
        return Doc.get_text(self.root.find("SummaryTitle"))

    @cached_property
    def matches(self):
        """Assemble the sequence of matches for the caller's phrases."""

        matches = []
        regex = self.control.regex
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
        return matches

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
          using_tail - True if the match came from node.tail, not node.text
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

            self.node = node
            self.opts = opts
            self.__collector = self.__prefix = []
            self.__suffix = []
            self.__collect(self.wrapper)

        @cached_property
        def in_standard_wording(self):
            """True if the match was found inside a StandardWording block.

            Can be overrden by the `wrapper` property logic.
            """

            if self.node.tag == "StandardWording" and not self.using_tail:
                return True
            return False

        @cached_property
        def prefix(self):
            """Context string appearing before matched phrase"""
            return "".join(self.__prefix)

        @cached_property
        def suffix(self):
            """Context string appearing after matched phrase"""
            return "".join(self.__suffix)

        @cached_property
        def using_tail(self):
            """True if the match came from node.tail, not node.text."""
            return self.opts.get("using_tail")

        @cached_property
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

            if self.node.tag in self.OK:
                return self.node
            wrapper = self.node.getparent()
            while wrapper is not None:
                if wrapper.tag in self.OK:
                    return wrapper
                if wrapper.tag == "SummarySection":
                    return None
                if wrapper.tag == "StandardWording":
                    self.in_standard_wording = True
                wrapper = wrapper.getparent()
            return None

        def __collect(self, node):
            """
            Recursively populate self.__suffix and self.__prefix

            Required positional argument:
              node - element in which the match was found
            """

            # Safety check.
            if node is None:
                return

            # Special handling for the node in which the match is found.
            if node is self.node:

                # Only add the node's text if the match is from the tail.
                if self.using_tail:
                    if node.text is not None:
                        self.__collector.append(node.text)

                # Otherwise switch to collecting the context's suffix.
                else:
                    self.__collector = self.__suffix

                # Process the node's children. Avoid recursive blocks.
                for child in node.findall("*"):
                    if child.tag not in self.OK:
                        self.__collect(child)

                # If the match was in the tail, the rest is suffix.
                if self.using_tail:
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
                        self.__collect(child)
                if node.tail is not None:
                    self.__collector.append(node.tail)

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

        def html_row(self, **opts):
            """
            Construct an HTML report row for this match

            Optional keyword arguments:
              summary - where the match was found (first match in summary only)

            Return:
              sequence of column values for the report's row
            """

            standard_wording = self.standard_wording and "Yes" or "No"
            summary = opts.get("summary")
            if not summary:
                return [
                    self.text,
                    Reporter.Cell(self.span),
                    Reporter.Cell(standard_wording, classes="center"),
                ]
            rowspan = len(summary.matches)
            if rowspan < 2:
                rowspan = None
            return [
                Reporter.Cell(summary.cdr_id, rowspan=rowspan),
                Reporter.Cell(summary.title, rowspan=rowspan),
                self.text,
                Reporter.Cell(self.span),
                Reporter.Cell(standard_wording, classes="center"),
            ]

        @cached_property
        def section(self):
            """Guard against None for section title"""

            if self.__section is None:
                return "*** NO SECTION TITLE ***"
            return self.__section

        @cached_property
        def prefix(self):
            """Context string appearing before match.

            In some cases the users have incorrectly included leading
            whitespace inside GlossaryTermRef elements. Because that
            leading whitespace has been stripped when looking for
            matches, we need to make sure that any non-empty prefix
            string is separated from the match with a space.
            """

            prefix = Summary.normalize(self.__prefix)
            if prefix:
                end = prefix[-1]
                if end not in " ([":
                    prefix += " "
            return prefix

        @cached_property
        def suffix(self):
            """
            Context string appearing after match

            If the users have incorrectly put whitespace after the matched
            term inside the GlossaryTermRef element by mistake, we may need
            to make sure the match is separated from the following context
            string by a space if appropriate.
            """

            suffix = Summary.normalize(self.__suffix)
            if suffix:
                start = suffix[0]
                if start.isalnum() or start in "[(":
                    suffix = " " + suffix
            return suffix

        @property
        def span(self):
            """Assemble the HTML cell object for the match (uncached)."""

            section = B.B(self.section)
            section.tail = ' - "' + self.prefix.lstrip()
            term = B.B(self.text, B.CLASS("error"))
            term.tail = self.suffix.rstrip() + '"'
            return B.SPAN(section, term)


if __name__ == "__main__":
    """Don't execute if loaded as a module."""
    Control().run()
