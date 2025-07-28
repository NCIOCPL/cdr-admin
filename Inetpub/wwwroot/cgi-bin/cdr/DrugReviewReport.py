#!/usr/bin/env python

"""Show CDR drug Term documents.

The report is partitioned into three sections:
  * New NCI Thesaurus drug terms.
  * New CDR drug terms.
  * Drug terms requiring review.

Users enter a date range from which to select terms into a CGI form
and the software then produces the Excel format report.
"""

from datetime import date, datetime, timedelta
from functools import cached_property
from io import BytesIO
from sys import stdout
from xlsxwriter import Workbook
from cdrapi.docs import Doc
from cdrcgi import Controller


class Control(Controller):
    """Report-specific behavior implemented in this derived class."""

    SUBTITLE = "Drug Review Report"
    LOGNAME = "DrugReviewReport"
    INSTRUCTIONS = (
        "To prepare an Excel format report of Drug/Agent terms, "
        "enter a start date and an optional end date for the "
        "creation of Drug/Agent terms.  Terms of semantic "
        "type \"Drug/Agent\" that were created in the "
        "specified date range will be included in the report."
    )

    # Table names
    NCI_TITLE = "New Drugs from NCI Thesaurus"
    CDR_TITLE = "New Drugs from the CDR"
    RVW_TITLE = "Drugs to be Reviewed"

    # Column labels
    CDR_ID = "CDR ID"
    PREFERRED_NAME = "Preferred Name"
    OTHER_NAMES = "Other Names"
    OTHER_NAME_TYPE = "Other Name Type"
    SOURCE = "Source"
    TERM_TYPE = "TType"
    SOURCE_ID = "SourceID"
    DEFS = "Definition"
    CREATED = "Created"

    def populate_form(self, page):
        """Explain how to run the report and show the date fields.

        Pass:
            page - HTMLPage object for showing the form
        """

        end = date.today()
        start = end - timedelta(7)
        fieldset = page.fieldset()
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)
        fieldset = page.fieldset("Date Range")
        opts = dict(value=start, label="Start Date")
        fieldset.append(page.date_field("start", **opts))
        opts = dict(value=end, label="End Date")
        fieldset.append(page.date_field("end", **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Override so we have rich text in the cells."""

        ndocs = self.__collect_terms()
        self.__add_sheet(self.NCI_TITLE, self.nci_terms)
        self.__add_sheet(self.CDR_TITLE, self.cdr_terms)
        self.__add_sheet(self.RVW_TITLE, self.rvw_terms)
        self.book.close()
        self.output.seek(0)
        book_bytes = self.output.read()
        stamp = self.started.strftime("%Y%m%d%H%M%S")
        secs = (datetime.now() - self.started).total_seconds()
        name = f"DrugReviewReport-{stamp}-{ndocs:d}_docs-{secs}_secs.xlsx"
        self.logger.info("sending %s", name)
        if not self.testing:
            stdout.buffer.write(f"""\
Content-type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename={name}
Content-length: {len(book_bytes):d}
X-Content-Type-Options: nosniff

""".encode("utf-8"))
        stdout.buffer.write(book_bytes)

    @cached_property
    def book(self):
        """Excel workbook for the report."""
        return Workbook(self.output, dict(in_memory=True))

    @cached_property
    def end(self):
        """User's selection for the end of the report's date range."""
        return self.parse_date(self.fields.getvalue("end"))

    @cached_property
    def output(self):
        """Memory stream to capture the Excel workbook's bytes."""
        return BytesIO()

    @cached_property
    def start(self):
        """User's selection for the beginning of the report's date range."""
        return self.parse_date(self.fields.getvalue("start"))

    @cached_property
    def styles(self):
        """Formats for the reports."""

        styles = dict(
            comment=dict(italic=True, font_color="green"),
            data=dict(align="left", valign="top", text_wrap=True),
            divider=dict(fg_color="#C0C0C0"),
            header=dict(
                align="center",
                bold=True,
                fg_color="blue",
                font_color="white",
            ),
            merge=dict(align="center", bold=True),
        )

        class Styles:
            def __init__(self, book, styles):
                for name in styles:
                    setattr(self, name, book.add_format(styles[name]))
        return Styles(self.book, styles)

    @cached_property
    def testing(self):
        """Boolean flag for suppressing writing the HTML headers."""
        return True if self.fields.getvalue("test") else False

    def __add_sheet(self, name, terms):
        """Create and populate a sheet for one of the report's tables."""

        cols = self.__columns(name)
        positions = dict([(col.label, i) for i, col in enumerate(cols)])
        last_col = len(cols) - 1
        sheet = self.book.add_worksheet(name)
        sheet.freeze_panes(2, 0)
        # pylint: disable-next=no-member
        args = 0, 0, 0, last_col, name, self.styles.merge
        sheet.merge_range(*args)
        for i, col in enumerate(cols):
            sheet.set_column(i, i, col.width)
            # pylint: disable-next=no-member
            sheet.write(1, i, col.label, self.styles.header)
        row = 2
        divider = False
        for term in terms:
            row = term.add_rows(sheet, row, positions, divider)
            divider = True

    def __collect_terms(self):
        """Identify the terms needed for the report.

        Find all of the drug term documents created in the date range
        specified by the user. Populates three sequences of terms
        document references, one for each of the tables in the report:
          * terms imported from the NCI thesaurus
          * terms created in the CDR
          * terms requiring review because some part is marked "problematic"
            (also appearing in one of the first two tables)

        Return:
          integer for the number of terms selected
        """

        self.nci_terms = []
        self.cdr_terms = []
        self.rvw_terms = []
        subquery = self.Query("query_term", "doc_id")
        subquery.where("path = '/Term/PreferredName'")
        subquery.where("value = 'Drug/Agent'")
        query = self.Query("query_term t", "t.doc_id").unique()
        query.where("t.path = '/Term/SemanticType/@cdr:ref'")
        query.where(query.Condition("t.int_val", subquery))
        if self.start or self.end:
            query.join("audit_trail a", "a.document = t.doc_id")
            query.where("a.action = 1")
            if self.start:
                query.where(f"a.dt >= '{self.start}'")
            if self.end:
                query.where(f"a.dt <= '{self.end} 23:59:59'")
        doc_ids = [row[0] for row in query.execute(self.cursor).fetchall()]
        for doc_id in (sorted(doc_ids)):
            term = Drug(self, doc_id)
            if term.from_nci_thesaurus:
                self.nci_terms.append(term)
            else:
                self.cdr_terms.append(term)
            if term.problematic:
                self.rvw_terms.append(term)
        return len(doc_ids)

    def __columns(self, title):
        """Assemble the sequence of column definitions for the current table.

        We have the actual strings for the column and table names in a
        central place (class-level named values) to increase the chances
        that future changes to the arrangement and composition of the
        tables will not break the report.
        """

        class Column:
            def __init__(self, label, width):
                self.label = label
                self.width = width
        cols = [
            Column(self.CDR_ID, 10),
            Column(self.PREFERRED_NAME, 30),
            Column(self.OTHER_NAMES, 30),
            Column(self.OTHER_NAME_TYPE, 20)
        ]
        if title != self.CDR_TITLE:
            cols.append(Column(self.SOURCE, 17))
            cols.append(Column(self.TERM_TYPE, 15))
            cols.append(Column(self.SOURCE_ID, 10))
            cols.append(Column(self.DEFS, 100))
        cols.append(Column(self.CREATED, 12))
        return cols


class Comments:
    """Common functionality for collecting Comment children of a node."""

    PUBLIC = "External"

    @cached_property
    def comments(self):
        """Collect the Comment children of the node for this object."""

        comments = []
        for child in self.node.findall("Comment"):
            if child.get("audience") == self.PUBLIC:
                text = Doc.get_text(child, "").strip()
                if text:
                    comments.append(text)
        return comments


class Status:
    """Common functionality for determining the status of a node."""

    PROBLEMATIC = "Problematic"

    @property
    def problematic(self):
        """True if this definition needs review."""
        return self.status == self.PROBLEMATIC

    @cached_property
    def status(self):
        """The review status for the definition."""
        return Doc.get_text(self.node.find("ReviewStatus"))


class Drug(Comments, Status):
    """CDR drug/agent term, with definitions and other names."""

    THESAURUS = "NCI Thesaurus"

    def __init__(self, control, doc_id):
        """Capture the caller's arguments.

        Pass:
            control - access to the database and workbook styles
            doc_id - integer for the CDR Term document for the drug
        """

        self.__control = control
        self.__doc_id = doc_id

    def add_rows(self, sheet, row, cols, divider):
        """Add rows to the worksheet for the current table for this drug.

        For the last table (drug terms which need review) suppress
        display of other names and definitions which have not been
        flagged individually as problematic.

        Pass:
            sheet      - reference to object for the current Excel worksheet
            row        - integer for starting row number
            cols       - map of column position integers, indexed by the
                         column names, for those columns which should
                         be included on this table
            divider    - boolean indicating whether to precede the data
                         with a blank row (True for all but the first
                         drug term in the table)
        Return:
            integer for the next drug term's starting row number
        """

        other_names = self.other_names
        definitions = self.definitions
        if sheet.name == Control.RVW_TITLE:
            other_names = [n for n in other_names if n.problematic]
            definitions = [d for d in definitions if d.problematic]
        definitions = self.__wrap_definitions(definitions)
        styles = self.control.styles
        if divider:
            sheet.merge_range(row, 0, row, len(cols) - 1, "", styles.divider)
            row += 1
        rows = len(other_names) or 1
        last = row + rows - 1
        common = sheet, row, last
        self.write_cell(*common, cols[Control.CDR_ID], self.doc.id)
        self.write_cell(*common, cols[Control.PREFERRED_NAME], self.name)
        for i, other_name in enumerate(other_names):
            other_name.write_cells(self, sheet, row + i, cols)
        if Control.DEFS in cols:
            self.write_cell(*common, cols[Control.DEFS], definitions)
        self.write_cell(*common, cols[Control.CREATED], self.created)
        return last + 1

    def write_cell(self, sheet, first, last, col, values):
        """
        Write the data to a cell (or a set of merged cells).

        We centralize the code for this here because we have to handle
        four different cases:

          * single string value stored in a single cell
          * rich text sequence stored in a single cell
          * single string value stored in a set of merged cells
          * rich text sequence stored in a set of merged cells

        Note that there is a bug in Microsoft Excel, which prevents the
        auto-height feature from working properly. So the user may need to
        manually expand the height of a row containing large values in
        merged cells (see https://tinyurl.com/excel-merged-height-bug).
        To mitigate the impact of this bug, I have made the width of the
        affected columns larger than in the original version of this report.

        Pass:

            sheet  - spreadsheet for the current report table
            first  - integer for the first row in the range
            last   - integer for the last for in the range
            col    - integer for the column of the range
            values - a sequence of values, some containing rich text; or
                     a single value (string or integer)
        Return:
            No return value
        """

        cell_format = self.control.styles.data
        if isinstance(values, (list, tuple)):
            if len(values) == 2:
                if isinstance(values[0], str) and isinstance(values[1], str):
                    values = values[0], self.control.styles.comment, values[1]
            if first < last:
                sheet.merge_range(first, col, last, col, "", cell_format)
            sheet.write_rich_string(first, col, *values, cell_format)
            args = first, last, col, values
            self.control.logger.debug("write_cell(%d, %d, %d, %s)", *args)
        elif first == last:
            sheet.write(first, col, values, cell_format)
        else:
            sheet.merge_range(first, col, last, col, values, cell_format)

    @property
    def control(self):
        """Access to the database and workbook styles."""
        return self.__control

    @cached_property
    def created(self):
        """When the document was first created."""

        query = self.control.Query("audit_trail", "dt")
        query.where(query.Condition("document", self.__doc_id))
        query.where("action = 1")
        rows = query.execute(self.control.cursor).fetchall()
        return rows[0][0].strftime("%Y-%m-%d") if rows else ""

    @cached_property
    def definitions(self):
        """Alternate names for the drug term."""

        definitions = []
        for node in self.doc.root.findall("Definition"):
            definitions.append(self.Definition(node))
        return definitions

    @cached_property
    def doc(self):
        """`Doc` object for the CDR Term document."""
        return Doc(self.control.session, id=self.__doc_id)

    @cached_property
    def from_nci_thesaurus(self):
        """`True` iff the source for this drug term was the NCI thesaurus."""

        for other_name in self.other_names:
            if other_name.source and other_name.source.code == self.THESAURUS:
                return True
        return False

    @cached_property
    def last_modified(self):
        """When was this drug term document last modified?"""
        return Doc.get_text(self.doc.root.find("DateLastModified"))

    @cached_property
    def name(self):
        """String for the drug's preferred name.

        If there are any comments, this property will have a pair of
        strings, one for the name itself and the other for the comments.
        """

        name = Doc.get_text(self.doc.root.find("PreferredName"), "").strip()
        if not self.comments:
            return name
        comments = [f"\n[{comment}]" for comment in self.comments]
        return name, "".join(comments)

    @cached_property
    def node(self):
        """Top-level node for the Term document.

        Exposed so the Comments and Status base classes can find it.
        """
        return self.doc.root

    @cached_property
    def other_names(self):
        """Alternate names for the drug term."""

        names = []
        for node in self.doc.root.findall("OtherName"):
            names.append(self.OtherName(node))
        return names

    @cached_property
    def problematic(self):
        """True if the drug should a appear on the list of terms to review."""

        if self.status == self.PROBLEMATIC:
            return True
        for other_name in self.other_names:
            if other_name.problematic:
                return True
        for definition in self.definitions:
            if definition.problematic:
                return True
        return False

    def __wrap_definitions(self, definitions):
        """Assemble the cell contents for the drug term's definitions.

        Pass:
            definitions  - sequence of Definition objects for the drug term

        Return:
            A sequence of values, some with rich text formatting, if any of
            the definitions has a comment; otherwise return a concatenated
            string containing the definitions separated by a blank line
        """

        rich_text = False
        first = True
        pieces = []
        for definition in definitions:
            if not first:
                pieces.append("\n\n")
            if isinstance(definition.text, str):
                if definition.text:
                    pieces.append(definition.text)
            elif definition.text is not None:
                text, comments = definition.text
                if text:
                    pieces.append(text)
                pieces.append(self.control.styles.comment)
                pieces.append(comments)
                rich_text = True
            first = False
        if rich_text:
            return pieces
        else:
            return "".join(pieces)

    class Definition(Comments, Status):
        """One of the definitions for a drug term."""

        def __init__(self, node):
            """Save the node for this definition.

            Pass:
                node - portion of the Term document for a definition
            """
            self.__node = node

        @property
        def node(self):
            """Portion of the Term document for this definition."""
            return self.__node

        @cached_property
        def text(self):
            """The text of the definition, stripped of markup.

            If there are any comments, the value is a pair of strings,
            one for the definition itself, and the other for the concatenated
            comments, each comment on its own line.
            """

            text = Doc.get_text(self.node.find("DefinitionText"))
            if self.comments:
                comments = [f"\n[{comment}]" for comment in self.comments]
                text = text, "".join(comments)
            return text

    class OtherName(Comments, Status):
        """An alternate name for the drug term."""

        def __init__(self, node):
            """Remember the other name's node.

            Pass:
                node - portion of the Term document for this alternate name
            """
            self.__node = node

        def write_cells(self, term, sheet, row, cols):
            """Populate the cells for this alternate name."""

            values = {
                Control.OTHER_NAMES: self.name,
                Control.OTHER_NAME_TYPE: self.type
            }
            if self.source:
                values[Control.SOURCE] = self.source.code
                values[Control.TERM_TYPE] = self.source.term_type
                values[Control.SOURCE_ID] = self.source.term_id
            for key, value in values.items():
                col = cols.get(key)
                if col:
                    term.write_cell(sheet, row, row, col, value)

        @cached_property
        def name(self):
            """String for this alternate name.

            If there are any public comments associated with this name,
            they are concatenated and this property is a tuple with the
            first item in the tuple carrying the string for the name,
            and the second item being the string for the concatenated
            comments. This is so the comments can be given different
            format styling in the report.
            """

            name = Doc.get_text(self.node.find("OtherTermName"), "").strip()
            if self.comments:
                comments = [f"\n[{comment}]" for comment in self.comments]
                name = name, "".join(comments)
            return name

        @property
        def node(self):
            """Portion of the Term document for this alternate name."""
            return self.__node

        @cached_property
        def source(self):
            """Source information for this alternate name."""

            node = self.node.find("SourceInformation/VocabularySource")
            return None if node is None else self.Source(node)

        @cached_property
        def type(self):
            """String for the type of this other name."""
            return Doc.get_text(self.node.find("OtherNameType"))

        class Source:
            """Identification of the origin of the term's alternate name."""
            def __init__(self, node):
                self.code = Doc.get_text(node.find("SourceCode"))
                self.term_type = Doc.get_text(node.find("SourceTermType"))
                self.term_id = Doc.get_text(node.find("SourceTermId"))


if __name__ == "__main__":
    "Allow the file to be loaded as a module instead of a script."
    Control().run()
