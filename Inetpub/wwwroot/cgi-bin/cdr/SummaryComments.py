#!/usr/bin/env python

"""Report on comments in summaries.
"""

from collections import OrderedDict
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Access to the database and report-creation tools."""

    SUBTITLE = "Summary Comments Report"
    RESPONSE = "ResponseToComment"
    BOARD_PATH = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
    TRANSLATION_PATH = "/Summary/TranslationOf/@cdr:ref"
    AUDIENCE_PATH = "/Summary/SummaryMetaData/SummaryAudience"
    TYPES = OrderedDict(
        C="All Comments",
        I="Internal Comments (excluding permanent comments)",
        P="Permanent Comments (internal & external)",
        E="External Comments (excluding advisory comments)",
        A="Advisory Board Comments (internal & external)",
        R="Responses to Comments",
    )
    SELECTION_METHODS = (
        ("board", "By PDQ Board", True),
        ("id", "By CDR ID", False),
        ("title", "By Summary Title", False),
    )
    BLANK = "blank"
    USER_AND_DATE = "user-and-date"
    EXTRAS = (
        (USER_AND_DATE, "User ID and Date"),
        (BLANK, "Blank Column"),
    )
    SCRIPT = "../../js/SummaryComments.js"
    CSS = "../../stylesheets/html-for-word.css"

    def build_tables(self):
        """Assemble the report's tables, one for each selected summary."""
        return [summary.table for summary in self.summaries]

    def populate_form(self, page):
        """Decide which form we're using and populate it.

        Pass:
            page - HTMLPage object which implements the form page
        """

        default_extras = self.extra
        if self.titles:
            page.form.append(page.hidden_field("selection_method", "id"))
            fieldset = page.fieldset("Choose Summary")
            for t in self.titles:
                opts = dict(value=t.id, label=t.display, tooltip=t.tooltip)
                fieldset.append(page.radio_button("id", **opts))
            page.form.append(fieldset)
            page.add_css("fieldset { width: 600px; }")
            self.new_tab_on_submit(page)
        else:
            if not default_extras:
                default_extras = [self.BLANK]
            fieldset = page.fieldset("Selection Method")
            for value, label, checked in self.SELECTION_METHODS:
                opts = dict(value=value, label=label, checked=checked)
                fieldset.append(page.radio_button("selection_method", **opts))
            page.form.append(fieldset)
            fieldset = page.fieldset("Board")
            fieldset.set("class", "by-board-block")
            for id, name in self.boards.items():
                opts = dict(value=id, label=name)
                fieldset.append(page.radio_button("board", **opts))
            page.form.append(fieldset)
            self.add_audience_fieldset(page)
            self.add_language_fieldset(page)
            fieldset = page.fieldset("Summary Document ID")
            fieldset.set("class", "by-id-block")
            fieldset.append(page.text_field("id", label="CDR ID"))
            page.form.append(fieldset)
            fieldset = page.fieldset("Summary Title")
            fieldset.set("class", "by-title-block")
            tooltip = "Use wildcard (%) as appropriate."
            fieldset.append(page.text_field("title", tooltip=tooltip))
            page.form.append(fieldset)
        fieldset = page.fieldset("Comment Types", id="types-block")
        for key, label in self.TYPES.items():
            opts = dict(
                value=key,
                label=label,
                classes="" if key in "CR" else "specific-comment-types",
                checked=key in self.types,
            )
            fieldset.append(page.checkbox("types", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Extra Columns")
        for value, label in self.EXTRAS:
            checked = value in default_extras
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.checkbox("extra", **opts))
        page.form.append(fieldset)
        page.head.append(page.B.SCRIPT(src=self.SCRIPT))

    def show_report(self):
        """Override the base class version to add a custom stylesheet."""

        page = self.report.page
        page.head.append(page.B.LINK(href=self.CSS, rel="stylesheet"))
        page.add_css("header h1 {font-size:32px;} td {word-break:break-word;}")
        self.report.send(self.format)

    @property
    def audience(self):
        """Patient or Health professional."""

        if not hasattr(self, "_audience"):
            default = self.AUDIENCES[0]
            self._audience = self.fields.getvalue("audience", default)
            if self._audience not in self.AUDIENCES:
                self.bail()
        return self._audience

    @property
    def board(self):
        """Integer ID of the PDQ Board selected for the report."""

        if not hasattr(self, "_board"):
            self._board = self.fields.getvalue("board")
            if self._board:
                try:
                    self._board = int(self.board)
                except Exception:
                    self.bail()
                if self._board not in self.boards:
                    self.bail()
        return self._board

    @property
    def boards(self):
        """Ordered dictionary of short PDQ board names, indexed by board ID."""

        if not hasattr(self, "_boards"):
            self._boards = self.get_boards()
        return self._boards

    @property
    def columns(self):
        """Column headers for the report tables."""

        if not hasattr(self, "_columns"):
            Column = self.Reporter.Column
            styles = self.styles
            self._columns = [
                Column("Summary Section Title", style=styles[0]),
                Column("Comments", style=styles[1])
            ]
            if Control.USER_AND_DATE in self.extra:
                self._columns.append(Column("User ID (Date)", style=styles[2]))
            if Control.BLANK in self.extra:
                self._columns.append(Column("Blank", style=styles[3]))
        return self._columns

    @property
    def extra(self):
        """Which additional columns has the user requested?"""

        if not hasattr(self, "_extra"):
            self._extra = set(self.fields.getlist("extra"))
        return self._extra

    @property
    def fragment(self):
        """String used to match summary titles."""

        if not hasattr(self, "_fragment"):
            self._fragment = self.fields.getvalue("title")
        return self._fragment

    @property
    def id(self):
        """Integer ID of the PDQ summary selected for the report."""

        if not hasattr(self, "_id"):
            self._id = self.fields.getvalue("id")
            if self._id:
                try:
                    self._id = Doc.extract_id(self._id)
                except Exception:
                    self.bail("Invalid document ID")
        return self._id

    @property
    def language(self):
        """English or Spanish."""

        if not hasattr(self, "_language"):
            default = self.LANGUAGES[0]
            self._language = self.fields.getvalue("language", default)
            if self._language not in self.LANGUAGES:
                self.bail()
        return self._language

    @property
    def selection_method(self):
        """How the user wants to select summaries."""

        if not hasattr(self, "_selection_method"):
            method = self.fields.getvalue("selection_method", "board")
            if method not in [m[0] for m in self.SELECTION_METHODS]:
                self.bail()
            self._selection_method = method
        return self._selection_method

    @property
    def styles(self):
        """Sequence of strings for the columns' CSS width style rules."""

        if not hasattr(self, "_styles"):
            self._styles = [f"width: {width:d}px;" for width in self.widths]
        return self._styles

    @property
    def subtitle(self):
        """What we display directly under the main banner."""

        if not hasattr(self, "_subtitle"):
            if self.request == self.SUBMIT and self.summaries:
                if len(self.summaries) > 1:
                    board_name = self.boards[self.board]
                    args = self.language, self.audience, board_name
                    template = "Comments for {} {} {} Summaries"
                    subtitle = template.format(*args)
                else:
                    subtitle = f"Comments for {self.summaries[0].title}"
                today = self.started.strftime("%Y-%m-%d")
                self._subtitle = f"{subtitle} \N{EN DASH} {today}"
            else:
                self._subtitle = self.SUBTITLE
        return self._subtitle

    @property
    def summaries(self):
        """Collect the summaries using the user's selected method.

        If the user chooses the "by summary title" method for
        selecting which summary to use for the report, and the
        fragment supplied matches more than one summary document,
        display the form a second time so the user can pick the
        summary.
        """

        if not hasattr(self, "_summaries"):
            self._summaries = None
            if self.selection_method == "title":
                if not self.fragment:
                    self.bail("Title fragment is required.")
                if not self.titles:
                    self.bail("No summaries match that title fragment")
                if len(self.titles) == 1:
                    self._summaries = [Summary(self, self.titles[0].id)]
                else:
                    self.show_form()
            elif self.selection_method == "id":
                if not self.id:
                    self.bail("CDR ID is required.")
                self._summaries = [Summary(self, self.id)]
            else:
                if not self.board:
                    self.bail("Board is required.")
                query = self.Query("query_term a", "a.doc_id").unique()
                query.where(f"a.path = '{self.AUDIENCE_PATH}'")
                query.where(query.Condition("a.value", f"{self.audience}s"))
                if self.language == "English":
                    query.join("query_term b", "b.doc_id = a.doc_id")
                else:
                    query.join("query_term t", "t.doc_id = a.doc_id")
                    query.where(f"t.path = '{self.TRANSLATION_PATH}'")
                    query.join("query_term b", "b.doc_id = t.int_val")
                query.where(f"b.path = '{self.BOARD_PATH}'")
                query.where(query.Condition("b.int_val", self.board))
                query.join("active_doc d", "d.id = a.doc_id")
                query.join("doc_version v", "v.id = d.id")
                query.where("v.publishable = 'Y'")
                rows = query.execute(self.cursor).fetchall()
                summaries = [Summary(self, row.doc_id) for row in rows]
                self._summaries = sorted(summaries)
        return self._summaries

    @property
    def tags(self):
        """Which comment elements should we search for by tag?"""

        if not hasattr(self, "_tags"):
            self._tags = []
            if "R" in self.types:
                self._tags = [self.RESPONSE]
            if self.types - {"R"}:
                self._tags.append("Comment")
        return self._tags

    @property
    def titles(self):
        """Summary titles matching the user's fragment string."""

        if not hasattr(self, "_titles"):
            self._titles = None
            if self.request == self.SUBMIT:
                if self.selection_method == "title":
                    self._titles = self.summary_titles
        return self._titles

    @property
    def types(self):
        """Which types of comments has the user requested for the report?"""

        if not hasattr(self, "_types"):
            self._types = set(self.fields.getlist("types")) or set("ER")
        return self._types

    @property
    def widths(self):
        """Adjust column widths based on requested extra columns."""

        if not hasattr(self, "_widths"):
            self._widths = [250, 500, 175, 150]
            if self.USER_AND_DATE not in self.extra:
                self._widths[1] += self._widths[2]
            if self.BLANK not in self.extra:
                self._widths[1] += self._widths[2]
        return self._widths


class Summary:
    """A PDQ summary selected for the report."""

    def __init__(self, control, doc_id):
        """Remember the caller's values.

        Pass:
            control - access to the database and report-creation tools
            doc_id - integer for the summary document's CDR ID
        """

        self.__id = doc_id
        self.__control = control

    def __lt__(self, other):
        """Make the Summary list sortable."""
        return self.sort_key < other.sort_key

    @property
    def comments(self):
        """Comments found in the summary and matching the report's options."""

        if not hasattr(self, "_comments"):
            self._comments = []
            for node in self.doc.root.iter(*self.control.tags):
                comment = self.Comment(self.control, node)
                if comment.in_scope:
                    self._comments.append(comment)
        return self._comments

    @property
    def control(self):
        """Object with access to the database and report-creation tools."""
        return self.__control

    @property
    def doc(self):
        """`Doc` object for the PDQ summary."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.control.session, id=self.__id)
        return self._doc

    @property
    def rows(self):
        """Assemble this summary's table rows for the report."""

        if not hasattr(self, "_rows"):
            self._rows = []
            for section in self.sections:
                self._rows += section.rows
        return self._rows

    @property
    def sections(self):
        """Sequence of sections of the summary with comments."""

        if not hasattr(self, "_sections"):
            self._sections = []
            title = None
            comments = []
            for comment in self.comments:
                if comment.section_title != title and comments:
                    self._sections.append(self.Section(self, title, comments))
                    comments = []
                title = comment.section_title
                comments.append(comment)
            if comments:
                self._sections.append(self.Section(self, title, comments))
        return self._sections

    @property
    def sort_key(self):
        """Normalized title plus document ID used to order the summaries."""
        return self.title.lower() if self.title else "", self.doc.id

    @property
    def table(self):
        """Assemble the table for the comments in this summary."""

        opts = dict(caption=self.title, columns=self.control.columns)
        return self.control.Reporter.Table(self.rows, **opts)

    @property
    def title(self):
        """String for the summary's title."""

        if not hasattr(self, "_title"):
            self._title = Doc.get_text(self.doc.root.find("SummaryTitle"))
            if not self._title:
                self._title = self.doc.title
        return self._title

    class Section:
        """PDQ summary section with comments."""

        def __init__(self, summary, title, comments):
            """Capture the caller's values.

            Pass:
                summary - access to the report controller
                title - string for the secion't title
                comments - sequence of `Comment` objects
            """

            self.__summary = summary
            self.__title = title
            self.__comments = comments

        @property
        def rows(self):
            """One row for each comment in this summary section."""

            if not hasattr(self, "_rows"):
                self._rows = []
                Cell = self.__summary.control.Reporter.Cell
                opts = dict(width=self.__summary.control.widths[0])
                if len(self.__comments) > 1:
                    opts["rowspan"] = len(self.__comments)
                row = [Cell(self.__title, **opts)] + self.__comments[0].cells
                self._rows = [row]
                for comment in self.__comments[1:]:
                    self._rows.append(comment.cells)
            return self._rows

    class Comment:
        """A comment found in a PDQ summary section."""

        NO_SECTION_TITLE = "No Section Title"  # In case we don't find one.

        def __init__(self, control, node):
            """Save the caller's passed values.

            Comment elements (as well as ResponseToComment elements)
            are constrained to have pure text content, rather than
            mixed content, which makes this much simpler.

            Pass:
                control - access to the report's options, report-creation tools
                node - comment or response node found in the summary section
            """

            self.__control = control
            self.__node = node

        @property
        def audience(self):
            """Is the comment for external or internal consumption?"""

            if not hasattr(self, "_audience"):
                self._audience = self.__node.get("audience")
            return self._audience

        @property
        def cells(self):
            """Sequence of table cells contributed by this comment."""

            if self.__node.tag == Control.RESPONSE:
                color = "brown"
                label = "R"
            elif self.audience == "External":
                color = "green"
                label = "E"
            elif self.audience == "Internal":
                color = "blue"
                label = "I"
            else:
                color = None
                label = "-"
            if self.duration:
                label += self.duration[0].upper()
            if self.source:
                label += self.source[0].upper()
            text = f"[{label}] {self.text}"
            Cell = self.control.Reporter.Cell
            style = self.control.styles[1]
            if color:
                style = f"{style} color: {color};"
            cells = [Cell(text, style=style)]
            if Control.USER_AND_DATE in self.control.extra:
                value = self.user or ""
                if value and self.timestamp:
                    value = f"{value} ({self.timestamp})"
                cells.append(Cell(value, style=self.control.styles[2]))
            if Control.BLANK in self.control.extra:
                cells.append(Cell("", style=self.control.styles[3]))
            return cells

        @property
        def control(self):
            """Access to the report's options and to report-creation tools."""
            return self.__control

        @property
        def duration(self):
            """Is this an ephemeral or permanent comment?"""

            if not hasattr(self, "_duration"):
                self._duration = self.__node.get("duration")
            return self._duration

        @property
        def in_scope(self):
            """True if this comment should be included on the report."""

            if self.__node.tag == Control.RESPONSE:
                return "R" in self.control.types
            if "C" in self.control.types:
                return True
            if self.duration == "permanent" and "P" in self.control.types:
                return True
            if self.source == "advisory-board" and "A" in self.control.types:
                return True
            if self.audience == "Internal":
                if "I" in self.control.types:
                    return self.duration != "permanent"
            if self.audience == "External":
                if "E" in self.control.types:
                    return self.source != "advisory-board"
            return False

        @property
        def section_title(self):
            """Title of the section in which this comment was found."""

            if not hasattr(self, "_section_title"):
                self._section_title = None
                node = self.__node
                while not self._section_title:
                    if node.tag == "SummarySection":
                        child = node.find("Title")
                        if child is None:
                            self._section_title = self.NO_SECTION_TITLE
                        else:
                            title = Doc.get_text(child, "").strip()
                            title = title or self.NO_SECTION_TITLE
                            self._section_title = title
                    else:
                        node = node.getparent()
                        if node is None:
                            self._section_title = self.NO_SECTION_TITLE
                self.control.logger.info("title=%s", self._section_title)
            return self._section_title

        @property
        def source(self):
            """Was this from an advisory board member?"""

            if not hasattr(self, "_source"):
                self._source = self.__node.get("source")
            return self._source

        @property
        def text(self):
            """String for the body of the comment."""

            if not hasattr(self, "_text"):
                self._text = Doc.get_text(self.__node)
            return self._text

        @property
        def timestamp(self):
            """Date when the comment was entered."""

            if not hasattr(self, "_timestamp"):
                self._timestamp = self.__node.get("date")
            return self._timestamp

        @property
        def user(self):
            """Account name of the user who entered the comment."""

            if not hasattr(self, "_user"):
                self._user = self.__node.get("user")
            return self._user


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
