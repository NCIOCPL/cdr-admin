#----------------------------------------------------------------------
# Produce an Excel spreadsheet showing problematic drug terms, divided
# into three categories:
#
#   New NCI Thesaurus drug terms.
#   New CDR drug terms.
#   Drug terms requiring review.
#
# Each category appears on a separate worksheet (page) within the overall
# spreadsheet.
#
# Users enter a date range from which to select terms into an HTML form
# and the software then produces the Excel format report.
#
# JIRA::OCECDR-3800
# JIRA::OCECDR-4170 - complete rewrite
#----------------------------------------------------------------------
import datetime
import os
import sys
import lxml.etree as etree
import cdrcgi
import cdrdb

class Control(cdrcgi.Control):
    """
    Report-specific behavior implemented in this derived class.
    """

    DIVIDER = "pattern: pattern solid, fore_color gray25"
    COMMENT_FONT = "italic true, color_index green"
    INSTRUCTIONS = (
        "To prepare an Excel format report of Drug/Agent terms, "
        "enter a start date and an optional end date for the "
        "creation or import of Drug/Agent terms.  Terms of semantic "
        "type \"Drug/Agent\" that were created or imported in the "
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
    LAST_MOD = "Last Modified"

    def __init__(self):
        """
        Validate the parameters to prevent hacking.
        """

        cdrcgi.Control.__init__(self, "Drug Review Report")
        self.begin = datetime.datetime.now()
        self.start = self.fields.getvalue("start")
        self.end = self.fields.getvalue("end")
        self.test = self.fields.getvalue("test")
        cdrcgi.valParmDate(self.start, empty_ok=True, msg=cdrcgi.TAMPERING)
        cdrcgi.valParmDate(self.end, empty_ok=True, msg=cdrcgi.TAMPERING)

    def populate_form(self, form):
        """
        Explain how to run the report and show the date fields.
        """

        end = datetime.date.today()
        start = end - datetime.timedelta(7)
        form.add(form.B.FIELDSET(form.B.P(self.INSTRUCTIONS)))
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Date Range"))
        form.add_date_field("start", "Start Date", value=start)
        form.add_date_field("end", "End Date", value=end)
        form.add("</fieldset>")

    def show_report(self):
        """
        Generate the Excel spreadsheet and return it to the client's browser.
        It is important to create styles before calling collect_terms()!!!
        """

        self.styles = cdrcgi.ExcelStyles()
        self.styles.set_color(self.styles.header, "white")
        self.styles.set_background(self.styles.header, "blue")
        self.styles.comment_font = self.styles.font(self.COMMENT_FONT)
        self.styles.divider = self.styles.style(self.DIVIDER)
        self.collect_terms()
        self.add_sheet(self.NCI_TITLE, self.nci_terms)
        self.add_sheet(self.CDR_TITLE, self.cdr_terms)
        self.add_sheet(self.RVW_TITLE, self.rvw_terms)
        if sys.platform == "win32":
            import msvcrt
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        secs = (datetime.datetime.now() - self.begin).total_seconds()
        ndocs = self.ndocs
        name = "DrugReviewReport-%s-%d_docs-%s_secs.xls" % (stamp, ndocs, secs)
        if not self.test:
            print "Content-type: application/vnd.ms-excel"
            print "Content-Disposition: attachment; filename=%s" % name
            print
        self.styles.book.save(sys.stdout)

    def collect_terms(self):
        """
        Find all of the drug term documents last modified in the date
        range specified by the user. Populates three sequences of terms
        document references, one for each of the tables in the report:
          * terms imported from the NCI thesaurus
          * terms created in the CDR
          * terms requiring review because some part is marked "problematic"
            (also appearing in one of the first two tables)
        """

        self.nci_terms = []
        self.cdr_terms = []
        self.rvw_terms = []
        subquery = cdrdb.Query("query_term", "doc_id")
        subquery.where("path = '/Term/PreferredName'")
        subquery.where("value = 'Drug/Agent'")
        query = cdrdb.Query("query_term t", "t.doc_id").unique()
        query.where("t.path = '/Term/SemanticType/@cdr:ref'")
        query.where(query.Condition("t.int_val", subquery))
        if self.start or self.end:
            query.join("query_term m", "m.doc_id = t.doc_id")
            query.where("m.path = '/Term/DateLastModified'")
            if self.start:
                query.where("m.value >= '%s'" % self.start)
            if self.end:
                query.where("m.value <= '%s 23:59:59'" % self.end)
        doc_ids = [row[0] for row in query.execute(self.cursor).fetchall()]
        self.ndocs = len(doc_ids)
        for doc_id in (sorted(doc_ids)):
            term = Drug(self, doc_id)
            if term.from_nci_thesaurus():
                self.nci_terms.append(term)
            else:
                self.cdr_terms.append(term)
            if term.problematic():
                self.rvw_terms.append(term)

    def add_sheet(self, name, terms):
        """
        Create and populate a sheet for one of the report's tables.
        """

        opts = { "frozen_rows": 2, "cell_overwrite_ok": True }
        sheet = self.styles.add_sheet(name, **opts)
        cols = self.columns(name)
        positions = dict([(col.label, i) for i, col in enumerate(cols)])
        sheet.write_merge(0, 0, 0, len(cols) - 1, name, self.styles.bold)
        for i, col in enumerate(cols):
            sheet.col(i).width = self.styles.chars_to_width(col.width)
            sheet.write(1, i, col.label, self.styles.header)
        row = 2
        divider = False
        for term in terms:
            row = term.add_rows(sheet, row, positions, divider)
            divider = True

    def columns(self, title):
        """
        Assemble the sequence of column definitions for the current table.

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
        cols.append(Column(self.LAST_MOD, 12))
        return cols

class Drug:
    """
    CDR drug/agent term, with definitions and other names.
    """

    PROBLEMATIC = "Problematic"
    THESAURUS = "NCI Thesaurus"

    def __init__(self, control, doc_id):
        """
        Fetch and parse the Term document. Perform the wrapping of
        values with comments at object construction time so we don't
        have to do it multiple times for terms which appear in more
        than one table.
        """

        Drug.comment_font = control.styles.comment_font
        self.control = control
        self.doc_id = doc_id
        self.other_names = []
        self.definitions = []
        self.comments = []
        self.status = None
        query = cdrdb.Query("document", "xml")
        query.where(query.Condition("id", doc_id))
        xml = query.execute(control.cursor).fetchone()[0]
        root = etree.fromstring(xml.encode("utf-8"))
        self.name = self.get_text(root.find("PreferredName"))
        self.last_mod = self.get_text(root.find("DateLastModified"))
        self.other_names = [self.OtherName(n) for n in root.findall("other")]
        for node in root.findall("OtherName"):
            self.other_names.append(self.OtherName(node))
        for node in root.findall("Definition"):
            self.definitions.append(self.Definition(node))
        for node in root.findall("Comment"):
            self.comments.append(self.Comment(node))
        self.name = Drug.add_comments(self, "name")

    def add_rows(self, sheet, row, cols, divider):
        """
        Add rows to the worksheet for the current table for this drug.

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

        self.sheet = sheet
        other_names = self.other_names
        definitions = self.definitions
        if sheet.name == Control.RVW_TITLE:
            other_names = [n for n in other_names if n.problematic()]
            definitions = [d for d in definitions if d.problematic()]
        definitions = self.wrap_definitions(definitions)
        styles = self.control.styles
        if divider:
            sheet.write_merge(row, row, 0, len(cols) - 1, "", styles.divider)
            row += 1
        rows = len(other_names) or 1
        last = row + rows - 1
        self.write_cell(row, last, cols[Control.CDR_ID], self.doc_id)
        self.write_cell(row, last, cols[Control.PREFERRED_NAME], self.name)
        for i, other_name in enumerate(other_names):
            other_name.write_cells(self, row + i, cols)
        if Control.DEFS in cols:
            self.write_cell(row, last, cols[Control.DEFS], definitions)
        self.write_cell(row, last, cols[Control.LAST_MOD], self.last_mod)
        return last + 1

    def write_cell(self, first, last, col, values):
        """
        Write the data to a cell (or a set of merged cells).

        We centralize the code for this here because many cases could
        involved any of four different cases:

          * single string value stored in a single cell
          * rich text sequence stored in a single cell
          * single string value stored in a set of merged cells
          * rich text sequence stored in a set of merged cells

        Note that the xlwt package does not have a method for
        storing rich text in a multi-cell range. What you have to
        do instead is perform the operation in two steps:

          * write a styled placeholder to the range
          * store the rich text sequence in the first cell of the range

        In order to make this work, you have to suppress the block
        which prevents overwriting the contents of a cell you've already
        written to (see http://stackoverflow.com/questions/41770461).

        Note that there is a bug in Microsoft Excel, which prevents the
        auto-height feature from working properly. So the user may need to
        manually expand the height of a row containing large values in
        merged cells (see http://tinyurl.com/excel-merged-height-bug).
        To mitigate the impact of this bug, I have made the width of the
        affected columns larger than in the original version of this report.

        Pass:

            first  - integer for the first row in the range
            last   - integer for the last for in the range
            col    - integer for the column of the range
            values - a sequence of values, some containing rich text; or
                     a single value (string or integer)
        Return:
            No return value
        """

        left = self.control.styles.left
        sheet = self.sheet
        if isinstance(values, (list, tuple)):
            if first == last:
                sheet.write_rich_text(first, col, values, left)
            else:
                sheet.write_merge(first, last, col, col, "", left)
                sheet.row(first).set_cell_rich_text(col, values, left)
        elif first == last:
            sheet.write(first, col, values, left)
        else:
            sheet.write_merge(first, last, col, col, values, left)

    def wrap_definitions(self, definitions):
        """
        Assemble the cell contents for the drug term's definitions.

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
            if isinstance(definition.with_comments, basestring):
                pieces.append(definition.with_comments)
            else:
                pieces += definition.with_comments
                rich_text = True
            first = False
        if rich_text:
            return pieces
        else:
            return "".join(pieces)

    def problematic(self):
        """
        Determine whether drug should a appear on the list of terms to review.
        """

        if self.status == self.PROBLEMATIC:
            return True
        for other_name in self.other_names:
            if other_name.problematic():
                return True
        for definition in self.definitions:
            if definition.problematic():
                return True
        return False

    def from_nci_thesaurus(self):
        """
        Determine whether the source for drug term was the NCI thesaurus.
        """

        for other_name in self.other_names:
            if other_name.source and other_name.source.code == self.THESAURUS:
                return True
        return False

    @classmethod
    def add_comments(cls, obj, value_name):
        """
        Append the comments associated with a value for its cell display.

        We only show public (audience="External") comments.

        Pass:
            obj        - object containing the value and associated comments
            value_name - name of the object's attribute containing the value

        Return:
            single string if the object has no public comments; otherwise
            a sequence of values, some with rich text formatting
        """

        pieces = [getattr(obj, value_name)]
        for comment in obj.comments:
            wrapper = comment.wrap(cls.comment_font)
            if wrapper:
                pieces.append(wrapper)
        if len(pieces) == 1:
            return pieces[0]
        return pieces

    @staticmethod
    def get_text(node):
        """
        Assemble the concatenated text nodes for an element of the document.

        Note that the call to node.itertext() must include the wildcard
        string argument to specify that we want to avoid recursing into
        nodes which are not elements. Otherwise we will get the content
        of processing instructions, and how ugly would that be?!?
        """

        if node is None:
            return u""
        return u"".join(node.itertext("*"))

    class Definition:
        """
        One of the definitions for a drug term
        """

        def __init__(self, node):
            """
            Collect the definition's text, comments and status.

            We perform the assembly of the text with comments here
            to avoid doing it multiple times in case the definition
            appears in more than one table.
            """

            self.text = Drug.get_text(node.find("DefinitionText"))
            self.status = None
            self.comments = []
            for child in node.findall("ReviewStatus"):
                self.status = Drug.get_text(child)
            for child in node.findall("Comment"):
                self.comments.append(Drug.Comment(child))
            self.with_comments = Drug.add_comments(self, "text")

        def problematic(self):
            """
            Determine whether this definition should appear in the
            table of drug terms which need review.
            """

            return self.status == Drug.PROBLEMATIC

    class OtherName:
        """
        An alternate name for the drug term.
        """

        def __init__(self, node):
            """
            Extract the name, type, source and comments from the document node.

            We perform the assembly of the name with comments here in order
            to avoid doing it multiple times in case the name appears in more
            than one table.
            """

            self.name = Drug.get_text(node.find("OtherTermName"))
            self.type = Drug.get_text(node.find("OtherNameType"))
            self.source = self.status = None
            self.comments = []
            for child in node.findall("SourceInformation/VocabularySource"):
                self.source = self.Source(child)
            for child in node.findall("ReviewStatus"):
                self.status = Drug.get_text(child)
            for child in node.findall("Comment"):
                self.comments.append(Drug.Comment(child))
            self.with_comments = Drug.add_comments(self, "name")

        def problematic(self):
            """
            Determine whether this other name should appear in the
            table of drug terms which need review.
            """

            return self.status == Drug.PROBLEMATIC

        def write_cells(self, term, row, cols):
            """
            Populate the cells for the name's string, type, and
            (optionally) the name's source's code, type, and ID.
            """

            sheet = term.sheet
            values = {
                Control.OTHER_NAMES: self.with_comments,
                Control.OTHER_NAME_TYPE: self.type
            }
            if self.source:
                values[Control.SOURCE] = self.source.code
                values[Control.TERM_TYPE] = self.source.term_type
                values[Control.SOURCE_ID] = self.source.term_id
            for key, value in values.items():
                col = cols.get(key)
                if col:
                    term.write_cell(row, row, col, value)

        class Source:
            """
            Identification of the origin of the term's alternate name.
            """

            def __init__(self, node):
                self.code = Drug.get_text(node.find("SourceCode"))
                self.term_type = Drug.get_text(node.find("SourceTermType"))
                self.term_id = Drug.get_text(node.find("SourceTermId"))

    class Comment:
        """
        Comment attached to the drug term or one of its other names or
        definitions. We only report on external comments.
        """

        PUBLIC = "External"

        def __init__(self, node):
            """
            Fetch the text and audience for the comment.
            """

            self.text = Drug.get_text(node)
            self.audience = node.get("audience")

        def wrap(self, font):
            """
            Prepare the comment for display as rich text.

            Pass:
                font - xlwt Font object

            Return:
                sequence of comment text (on a separate line and enclosed
                in brackets) and font if this is a public comment;
                otherwise None
            """

            if self.audience == self.PUBLIC:
                return (u"\n[%s]" % self.text, font)
            return None

if __name__ == "__main__":
    "Allow the file to be loaded as a module instead of a script."
    Control().run()
