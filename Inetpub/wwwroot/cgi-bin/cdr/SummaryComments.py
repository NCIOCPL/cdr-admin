#!/usr/bin/env python

"""Report on comments in summaries.
"""

from functools import cached_property
from collections import OrderedDict
from cdrcgi import Controller, BasicWebPage
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
        ("board", "By PDQ Board"),
        ("id", "By CDR ID"),
        ("title", "By Summary Title"),
    )
    BLANK = "blank"
    USER_AND_DATE = "user-and-date"
    EXTRAS = (
        (USER_AND_DATE, "User ID and Date"),
        (BLANK, "Blank Column"),
    )
    SCRIPT = "../../js/SummaryComments.js"
    CSS = "../../stylesheets/html-for-word.css"

    def populate_form(self, page):
        """Decide which form we're using and populate it.

        Pass:
            page - HTMLPage object which implements the form page
        """

        if self.ready:
            self.show_report()
        default_extras = self.extra
        if self.titles:
            page.form.append(page.hidden_field("selection_method", "id"))
            fieldset = page.fieldset("Choose Summary")
            for t in self.titles:
                opts = dict(value=t.id, label=t.display, tooltip=t.tooltip)
                fieldset.append(page.radio_button("id", **opts))
            page.form.append(fieldset)
            page.add_css("fieldset { width: 600px; }")
            self.same_window = []
        else:
            if not default_extras:
                default_extras = [self.BLANK]
            fieldset = page.fieldset("Selection Method")
            for value, label in self.SELECTION_METHODS:
                checked = value == self.selection_method
                opts = dict(value=value, label=label, checked=checked)
                fieldset.append(page.radio_button("selection_method", **opts))
            page.form.append(fieldset)
            fieldset = page.fieldset("Board")
            fieldset.set("class", "by-board-block usa-fieldset")
            for id, name in self.boards.items():
                checked = id == self.board
                opts = dict(value=id, label=name, checked=checked)
                fieldset.append(page.radio_button("board", **opts))
            page.form.append(fieldset)
            self.add_audience_fieldset(page)
            self.add_language_fieldset(page)
            fieldset = page.fieldset("Summary Document ID")
            fieldset.set("class", "by-id-block usa-fieldset")
            opts = dict(label="CDR ID", value=self.id)
            fieldset.append(page.text_field("id", **opts))
            page.form.append(fieldset)
            fieldset = page.fieldset("Summary Title")
            fieldset.set("class", "by-title-block usa-fieldset")
            tooltip = "Use wildcard (%) as appropriate."
            opts = dict(tooltip=tooltip, value=self.fragment)
            fieldset.append(page.text_field("title", **opts))
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
        """Overridden because the table is too wide for the standard layout."""

        if not self.ready:
            self.show_form()
        report = BasicWebPage()
        report.wrapper.append(report.B.H1(self.subtitle))
        for table in self.tables:
            report.wrapper.append(table.node)
        report.wrapper.append(self.footer)
        report.page.head.append(report.B.LINK(href=self.CSS, rel="stylesheet"))
        report.page.head.append(report.B.STYLE(
            "table { width: 100%; margin: 1rem 0 2rem; }\n"
            "header h1 {font-size:32px;}\n"
            "td {word-break:break-word;}\n"
        ))
        report.send()

    @cached_property
    def audience(self):
        """Patient or Health professional."""

        default = self.AUDIENCES[0]
        audience = self.fields.getvalue("audience", default)
        if audience not in self.AUDIENCES:
            self.bail()
        return audience

    @cached_property
    def board(self):
        """Integer ID of the PDQ Board selected for the report."""

        board = self.fields.getvalue("board")
        if board:
            try:
                board = int(board)
            except Exception:
                self.bail()
            if board not in self.boards:
                self.bail()
        return board

    @cached_property
    def boards(self):
        """Ordered dictionary of short PDQ board names, indexed by board ID."""
        return self.get_boards()

    @cached_property
    def columns(self):
        """Column headers for the report tables."""

        Column = self.Reporter.Column
        styles = self.styles
        columns = [
            Column("Summary Section Title", style=styles[0]),
            Column("Comments", style=styles[1])
        ]
        if Control.USER_AND_DATE in self.extra:
            columns.append(Column("User ID (Date)", style=styles[2]))
        if Control.BLANK in self.extra:
            columns.append(Column("Blank", style=styles[3]))
        return columns

    @cached_property
    def extra(self):
        """Which additional columns has the user requested?"""
        return set(self.fields.getlist("extra"))

    @cached_property
    def fragment(self):
        """String used to match summary titles."""
        return self.fields.getvalue("title")

    @cached_property
    def id(self):
        """Integer ID of the PDQ summary selected for the report."""

        id = self.fields.getvalue("id")
        if id:
            try:
                id = Doc.extract_id(id)
            except Exception:
                self.bail("Invalid document ID")
        return id

    @cached_property
    def language(self):
        """English or Spanish."""

        default = self.LANGUAGES[0]
        language = self.fields.getvalue("language", default)
        if language not in self.LANGUAGES:
            self.bail()
        return language

    @cached_property
    def ready(self):
        """True if we have all the information we need to create the report."""

        if not self.request:
            return False
        match self.selection_method:
            case "title":
                if self.titles and len(self.titles) == 1:
                    return True
                if not self.fragment:
                    message = "Title fragment is required."
                    self.alerts.append(dict(message=message, type="error"))
                elif not self.titles:
                    message = f"No matching summaries for {self.fragment!r}."
                    self.alerts.append(dict(message=message, type="warning"))
                return False
            case "id":
                if not self.id:
                    message = "CDR ID is required."
                    self.alerts.append(dict(message=message, type="error"))
                doc = Doc(self.session, id=self.id)
                try:
                    if doc.doctype.name == "Summary":
                        return True
                    message = f"Document {doc.id} is a {doc.doctype} document."
                    self.alerts.append(dict(message=message, type="warning"))
                except Exception:
                    message = f"Document {self.id} not found."
                    self.logger.exception(message)
                    self.alerts.append(dict(message=message, type="warning"))
                return False
            case "board":
                if self.board:
                    return True
                message = "Board selection is required."
                self.alerts.append(dict(message=message, type="error"))
                return False
            case _:
                self.bail()

    @cached_property
    def same_window(self):
        """Reduce proliferation of new browser tabs."""
        return [self.SUBMIT] if self.request else []

    @cached_property
    def selection_method(self):
        """How the user wants to select summaries."""

        method = self.fields.getvalue("selection_method", "board")
        if method not in [m[0] for m in self.SELECTION_METHODS]:
            self.bail()
        return method

    @cached_property
    def styles(self):
        """Sequence of strings for the columns' CSS width style rules."""
        return [f"width: {width:d}px;" for width in self.widths]

    @cached_property
    def subtitle(self):
        """What we display at the top of the report."""

        if self.request == self.SUBMIT and self.summaries:
            if len(self.summaries) > 1:
                board_name = self.boards[self.board]
                args = self.language, self.audience, board_name
                template = "Comments for {} {} {} Summaries"
                subtitle = template.format(*args)
            else:
                subtitle = f"Comments for {self.summaries[0].title}"
            today = self.started.strftime("%Y-%m-%d")
            return f"{subtitle} \N{EN DASH} {today}"
        else:
            return self.SUBTITLE

    @cached_property
    def summaries(self):
        """Collect the summaries using the user's selected method."""

        if not self.ready:
            return []
        match self.selection_method:
            case "title":
                return [Summary(self, self.titles[0].id)]
            case "id":
                return [Summary(self, self.id)]
            case "board":
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
                return sorted([Summary(self, row.doc_id) for row in rows])

    @cached_property
    def tables(self):
        """Assemble the report's tables, one for each selected summary."""
        return [summary.table for summary in self.summaries]

    @cached_property
    def tags(self):
        """Which comment elements should we search for by tag?"""

        tags = []
        if "R" in self.types:
            tags = [self.RESPONSE]
        if self.types - {"R"}:
            tags.append("Comment")
        return tags

    @cached_property
    def titles(self):
        """Summary titles matching the user's fragment string."""

        if self.request == self.SUBMIT and self.selection_method == "title":
            return self.summary_titles
        return None

    @cached_property
    def types(self):
        """Which types of comments has the user requested for the report?"""
        return set(self.fields.getlist("types")) or set("ER")

    @cached_property
    def widths(self):
        """Adjust column widths based on requested extra columns."""

        widths = [250, 500, 175, 150]
        if self.USER_AND_DATE not in self.extra:
            widths[1] += widths[2]
        if self.BLANK not in self.extra:
            widths[1] += widths[2]
        return widths


class Summary:
    """A PDQ summary selected for the report."""

    def __init__(self, control, doc_id):
        """Remember the caller's values.

        Pass:
            control - access to the database and report-creation tools
            doc_id - integer for the summary document's CDR ID
        """

        self.id = doc_id
        self.control = control

    def __lt__(self, other):
        """Make the Summary list sortable."""
        return self.sort_key < other.sort_key

    @cached_property
    def comments(self):
        """Comments found in the summary and matching the report's options."""

        comments = []
        for node in self.doc.root.iter(*self.control.tags):
            comment = self.Comment(self.control, node)
            if comment.in_scope:
                comments.append(comment)
        return comments

    @cached_property
    def doc(self):
        """`Doc` object for the PDQ summary."""
        return Doc(self.control.session, id=self.id)

    @cached_property
    def rows(self):
        """Assemble this summary's table rows for the report."""

        rows = []
        for section in self.sections:
            rows += section.rows
        return rows

    @cached_property
    def sections(self):
        """Sequence of sections of the summary with comments."""

        sections = []
        title = None
        comments = []
        for comment in self.comments:
            if comment.section_title != title and comments:
                sections.append(self.Section(self, title, comments))
                comments = []
            title = comment.section_title
            comments.append(comment)
        if comments:
            sections.append(self.Section(self, title, comments))
        return sections

    @cached_property
    def sort_key(self):
        """Normalized title plus document ID used to order the summaries."""
        return self.title.lower() if self.title else "", self.doc.id

    @cached_property
    def table(self):
        """Assemble the table for the comments in this summary."""

        opts = dict(caption=self.title, columns=self.control.columns)
        return self.control.Reporter.Table(self.rows, **opts)

    @cached_property
    def title(self):
        """String for the summary's title."""

        title = Doc.get_text(self.doc.root.find("SummaryTitle"))
        return title or self.doc.title

    class Section:
        """PDQ summary section with comments."""

        def __init__(self, summary, title, comments):
            """Capture the caller's values.

            Pass:
                summary - access to the report controller
                title - string for the secion't title
                comments - sequence of `Comment` objects
            """

            self.summary = summary
            self.title = title
            self.comments = comments

        @cached_property
        def rows(self):
            """One row for each comment in this summary section."""

            Cell = self.summary.control.Reporter.Cell
            opts = dict(width=self.summary.control.widths[0])
            if len(self.comments) > 1:
                opts["rowspan"] = len(self.comments)
            rows = [[Cell(self.title, **opts)] + self.comments[0].cells]
            for comment in self.comments[1:]:
                rows.append(comment.cells)
            return rows

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

            self.control = control
            self.node = node

        @cached_property
        def audience(self):
            """Is the comment for external or internal consumption?"""
            return self.node.get("audience")

        @cached_property
        def cells(self):
            """Sequence of table cells contributed by this comment."""

            if self.node.tag == Control.RESPONSE:
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

        @cached_property
        def duration(self):
            """Is this an ephemeral or permanent comment?"""
            return self.node.get("duration")

        @cached_property
        def in_scope(self):
            """True if this comment should be included on the report."""

            if self.node.tag == Control.RESPONSE:
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

        @cached_property
        def section_title(self):
            """Title of the section in which this comment was found."""

            node = self.node
            section_title = None
            while not section_title:
                if node.tag == "SummarySection":
                    child = node.find("Title")
                    if child is None:
                        section_title = self.NO_SECTION_TITLE
                    else:
                        title = Doc.get_text(child, "").strip()
                        title = title or self.NO_SECTION_TITLE
                        section_title = title
                else:
                    node = node.getparent()
                    if node is None:
                        section_title = self.NO_SECTION_TITLE
            self.control.logger.info("section title=%s", section_title)
            return section_title

        @cached_property
        def source(self):
            """Was this from an advisory board member?"""
            return self.node.get("source")

        @cached_property
        def text(self):
            """String for the body of the comment."""
            return Doc.get_text(self.node)

        @cached_property
        def timestamp(self):
            """Date when the comment was entered."""
            return self.node.get("date")

        @cached_property
        def user(self):
            """Account name of the user who entered the comment."""
            return self.node.get("user")


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
