#!/usr/bin/env python

"""Show the tables of contents for one or more Cancer Information Summaries.
"""

from collections import defaultdict
from functools import cached_property
from cdrcgi import Controller, BasicWebPage
from cdrapi.docs import Doc
from cdr import Board


class Control(Controller):
    """Top-level logic for the report.

    There are basically two paths this report script can take. With the
    first, the user selects one or more boards, a language, and an
    audience, and we find all the publishable summaries which match.
    On the other path, the user asks for a report on a single summary,
    either by supplying the summary's document ID directly, or by
    entering a title fragment which we use to present a list of
    matching summaries from which the user selects one. On this
    second path, the user also selects a version. When we're reporting
    on the summaries selected by board, we use the current working
    document.
    """

    SUBTITLE = "Summary TOC Lists"
    LOGNAME = "summary_toc_lists"
    METHODS = (
        ("board", "By PDQ Board"),
        ("id", "By CDR ID"),
        ("title", "By Summary Title"),
    )
    AUDIENCES = dict(
        health_professional="Health Professional",
        patient="Patient",
    )
    LANGUAGES = "english", "spanish"
    DEFAULT_LEVEL = 3
    CSS = """\
h5 { font-size: 1.17em; }
li { line-height: 1.3; }
hr { margin-top: 2rem; }
"""
    SCRIPT = """\
function check_method(value) {
    console.log("check_method(" + value + ")");
    if (value == "id") {
        jQuery("fieldset.board-fieldset").hide();
        jQuery("fieldset#title-fieldset").hide();
        jQuery("fieldset#cdrid-fieldset").show();
    }
    else if (value == "title") {
        jQuery("fieldset.board-fieldset").hide();
        jQuery("fieldset#title-fieldset").show();
        jQuery("fieldset#cdrid-fieldset").hide();
    }
    else {
        jQuery("fieldset.board-fieldset").show();
        jQuery("fieldset#title-fieldset").hide();
        jQuery("fieldset#cdrid-fieldset").hide();
    }
}
function check_board(val) {
    if (val == "all") {
        jQuery("input[name='board']").prop("checked", false);
        jQuery("#board-all").prop("checked", true);
    }
    else if (jQuery("input[name='board']:checked").length > 0)
        jQuery("#board-all").prop("checked", false);
    else
        jQuery("#board-all").prop("checked", true);
}
jQuery(function() {
    var value = jQuery("input[name='method']:checked").val();
    check_method(value);
});
"""

    def add_audience_fieldset(self, page):
        """Add the radio buttons for choosing the audience.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        fieldset = page.fieldset("Audience")
        fieldset.set("class", "board-fieldset usa-fieldset")
        default = self.audience or "health_professional"
        for audience in self.AUDIENCES:
            checked = audience == default
            opts = dict(value=audience, checked=checked)
            fieldset.append(page.radio_button("audience", **opts))
        page.form.append(fieldset)

    def add_board_fieldset(self, page):
        """Add the checkboxes for selecting one or more PDQ boards.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        fieldset = page.fieldset("Board(s)")
        fieldset.set("class", "board-fieldset usa-fieldset")
        checked = not self.board or "all" in self.board
        opts = dict(value="all", label="All Boards", checked=checked)
        fieldset.append(page.checkbox("board", **opts))
        for board in sorted(self.boards.values()):
            checked = str(board.id) in self.board
            opts = dict(value=board.id, label=str(board), checked=checked)
            fieldset.append(page.checkbox("board", **opts))
        page.form.append(fieldset)

    def add_cdrid_fieldset(self, page):
        """Add the field for the summary document ID.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        fieldset = page.fieldset("Summary Document ID")
        fieldset.set("id", "cdrid-fieldset")
        fieldset.append(page.text_field("id", label="CDR ID", value=self.id))
        page.form.append(fieldset)

    def add_language_fieldset(self, page):
        """Add the radio buttons for choosing between English and Spanish.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        fieldset = page.fieldset("Language")
        fieldset.set("class", "board-fieldset usa-fieldset")
        default = self.language or self.LANGUAGES[0]
        for language in self.LANGUAGES:
            checked = language == default
            opts = dict(value=language, checked=checked)
            fieldset.append(page.radio_button("language", **opts))
        page.form.append(fieldset)

    def add_level_fieldset(self, page):
        """Add a picklist for choosing how deep the report should go.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        fieldset = page.fieldset("Table of Contents Depth")
        options = [("", "All Levels")] + [str(n) for n in range(1, 10)]
        tooltip = f"QC report uses level {self.DEFAULT_LEVEL:d}"
        default = self.fields.getvalue("level") or str(self.DEFAULT_LEVEL)
        opts = dict(options=options, default=default, tooltip=tooltip)
        fieldset.append(page.select("level", **opts))
        page.form.append(fieldset)

    def add_method_fieldset(self, page):
        """Add the fields for choosing how summaries will be selected.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        fieldset = page.fieldset("Selection Method")
        default = self.selection_method or self.METHODS[0][0]
        self.logger.info("default selection method is %s", default)
        for value, display in self.METHODS:
            checked = value == default
            opts = dict(value=value, label=display, checked=checked)
            fieldset.append(page.radio_button("method", **opts))
        page.form.append(fieldset)

    def add_options_fieldset(self, page):
        """Add the checkbox for choosing whether to display Summary CDR IDs.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        fieldset = page.fieldset("Options")
        checked = self.include_id if self.request else True
        opts = dict(
            value="include_id",
            label="Include CDR ID",
            checked=checked,
        )
        fieldset.append(page.checkbox("include_id", **opts))
        page.form.append(fieldset)

    def add_title_fieldset(self, page):
        """Add the field for entering a summary title fragment.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        fieldset = page.fieldset("Summary Title")
        fieldset.set("id", "title-fieldset")
        fieldset.append(page.text_field("title", value=self.fragment))
        page.form.append(fieldset)

    def populate_form(self, page):
        """Assemble the main form for this report.

        Broken into helper methods, since this is a complex form.
        We add some client-side scripting to make the form easier
        to use.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        # If the URL has the required values already show the report.
        if self.ready:
            return self.report.send()

        # Show the version selection form if a document has been selected.
        if self.id:
            self.logger.info("selecting version for CDR%s", self.id)
            page.form.append(page.hidden_field("method", value="id"))
            page.form.append(page.hidden_field("id", value=self.id))
            fieldset = page.fieldset("Select Document Version")
            options = [(v.id, v.description) for v in self.versions]
            fieldset.append(page.select("version", options=options))
            page.form.append(fieldset)

        # Let the user select from a list of matching summaries.
        elif self.titles:
            self.logger.info("selecting document mathing %r", self.fragment)
            page.form.append(page.hidden_field("method", value="id"))
            page.form.append(page.hidden_field("title", self.fragment))
            fieldset = page.fieldset("Choose Summary")
            for summary in self.titles:
                opts = dict(value=summary.id, label=summary.display)
                if summary.tooltip:
                    opts["tooltip"] = summary.tooltip
                fieldset.append(page.radio_button("id", **opts))
            page.form.append(fieldset)

        # If we have no ID or titles, show the initial form.
        else:
            self.logger.info("showing initial form")
            self.add_method_fieldset(page)
            self.add_cdrid_fieldset(page)
            self.add_title_fieldset(page)
            self.add_board_fieldset(page)
            self.add_audience_fieldset(page)
            self.add_language_fieldset(page)
            page.add_script(self.SCRIPT)

        # Carry these fields forward for all the steps.
        self.add_level_fieldset(page)
        self.add_options_fieldset(page)

    def show_report(self):
        """Show the report if we have all the information we need.

        We might not, as there are at least two stages of cascading
        forms (sometimes three) to get through before we get to the
        point where we're ready to actually create the report when
        the user wants to zero in on a single summary.
        """

        try:
            return self.report.send() if self.ready else self.show_form()
        except Exception as e:
            self.logger.exception("failure")
            self.bail(e)

    @cached_property
    def audience(self):
        """Either patient or health_professional."""

        audience = self.fields.getvalue("audience")
        if audience and audience not in self.AUDIENCES:
            self.bail()
        return audience

    @cached_property
    def board(self):
        """Board(s) which the user has selected.

        Sequence of board IDs or ["all"] if the user wants all boards
        included.
        """

        return self.fields.getlist("board")

    @cached_property
    def boards(self):
        """PDQ boards for the form's picklist."""
        return Board.get_boards(cursor=self.cursor)

    @cached_property
    def fragment(self):
        """Title fragment used to find matching summaries."""
        return self.fields.getvalue("title", "").strip()

    @cached_property
    def id(self):
        """CDR document ID for the summary to be used for the report."""

        match self.selection_method:
            case "id":
                return self.fields.getvalue("id", "").strip()
            case "title":
                if self.fragment and len(self.titles) == 1:
                    return self.titles[0].id
                return None
        return None

    @cached_property
    def include_id(self):
        """Boolean indicating whether Summary CDR IDs should be displayed."""
        return True if self.fields.getvalue("include_id") else False

    @cached_property
    def language(self):
        """Either english or spanish."""

        language = self.fields.getvalue("language")
        if language and language not in self.LANGUAGES:
            self.bail()
        return language

    @cached_property
    def level(self):
        """Integer indicating how deep the report should go."""
        return self.fields.getvalue("level") or "999"

    @cached_property
    def ready(self):
        """True if we have what we need for the report."""

        if not self.request:
            return False
        match self.selection_method:
            case "board":
                return True
            case "title":
                if not self.fragment:
                    message = "No title fragment provided."
                    self.alerts.append(dict(message=message, type="error"))
                elif not self.titles:
                    message = f"No summaries match {self.fragment!r}."
                    self.logger.error("ready check: %s", message)
                    self.alerts.append(dict(message=message, type="warning"))
                return False
            case "id":
                if not self.id:
                    message = "No document ID provided."
                    if self.fragment:
                        message = "No summary selected."
                    self.logger.error("ready check: %s", message)
                    self.alerts.append(dict(message=message, type="error"))
                    return False
                try:
                    doc = Doc(self.session, id=self.id)
                    if doc.doctype.name != "Summary":
                        message = f"CDR{self.id} is a {doc.doctype} document."
                        self.logger.error("ready check: %s", message)
                        self.alerts.append(dict(message=message, type="error"))
                        self.id = None
                        return False
                    self.id = doc.id
                except Exception:
                    message = f"Document {self.id} was not found."
                    self.logger.exception("ready check: %s", message)
                    self.alerts.append(dict(message=message, type="error"))
                    self.id = None
                    return False
                return True if self.version else False
            case _:
                self.bail()

    @cached_property
    def report(self):
        """Assemble the HTMLPage object for the report.

        This is a non-tabular report, so we create the page ourselves,
        instead of letting the base class take care of that for us.
        """

        self.logger.info("processing %d summaries", len(self.summaries))
        report = BasicWebPage()
        report.wrapper.append(report.B.H1(self.report_title))
        boards = defaultdict(list)
        for summary in sorted(self.summaries):
            self.logger.debug("processing %s", summary.title)
            if self.selection_method != "board" or not summary.boards:
                boards[""].append(summary)
            else:
                for board in summary.boards:
                    boards[board].append(summary)
        for board in sorted(boards):
            if board:
                report.wrapper.append(report.B.H2(board))
            for summary in boards[board]:
                for node in summary.nodes:
                    report.wrapper.append(node)
        report.wrapper.append(self.footer)
        report.page.head.append(report.B.STYLE(self.CSS))
        return report

    @cached_property
    def report_title(self):
        """Create the string identifying which report this is."""

        if self.selection_method == "id":
            return "Single Summary TOC Report"
        audience = self.AUDIENCES.get(self.audience) or ""
        language = self.language.title()
        return f"PDQ {language} {audience} Summaries"

    @cached_property
    def same_window(self):
        """Reduce the number of new browser tabs created."""
        return [self.SUBMIT] if self.request else []

    @cached_property
    def selection_method(self):
        """One of board, id, or title."""
        return self.fields.getvalue("method", "").strip()

    @cached_property
    def summaries(self):
        """PDQ summaries (`Summary` objects) to be displayed on the report."""

        fields = "q.doc_id", "q.value AS title"
        if self.id:
            query = self.Query("query_term q", *fields).unique()
            query.where(query.Condition("doc_id", self.id))
        else:
            audience = f"{self.AUDIENCES.get(self.audience)}s"
            language = self.language.title()
            b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
            t_path = "/Summary/TranslationOf/@cdr:ref"
            a_path = "/Summary/SummaryMetaData/SummaryAudience"
            l_path = "/Summary/SummaryMetaData/SummaryLanguage"
            query = self.Query("query_term q", *fields).unique()
            query.join("active_doc d", "d.id = q.doc_id")
            query.join("doc_version v", "v.id = d.id")
            query.where("v.publishable = 'Y'")
            query.join("query_term a", "a.doc_id = d.id")
            query.where(query.Condition("a.path", a_path))
            query.where(query.Condition("a.value", audience))
            query.join("query_term l", "l.doc_id = d.id")
            query.where(query.Condition("l.path", l_path))
            query.where(query.Condition("l.value", language))
            if "all" not in self.board:
                if language == "English":
                    query.join("query_term_pub b", "b.doc_id = d.id")
                else:
                    query.join("query_term_pub t", "t.doc_id = d.id")
                    query.where(query.Condition("t.path", t_path))
                    query.join("query_term b", "b.doc_id = t.int_val")
                query.where(query.Condition("b.path", b_path))
                query.where(query.Condition("b.int_val", self.board, "IN"))
        query.where("q.path = '/Summary/SummaryTitle'")
        self.logger.debug("query=\n%s", query)
        self.logger.debug("self.board = %s", self.board)
        query.log()
        rows = query.execute(self.cursor).fetchall()
        return [Summary(self, row) for row in rows]

    @cached_property
    def titles(self):
        """Information about summaries which match the title fragment."""

        if self.selection_method != "title" or not self.fragment:
            return []
        pattern = f"{self.fragment}%"
        query = self.Query("document d", "d.id", "d.title").order(2, 1)
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'Summary'")
        query.where(query.Condition("d.title", pattern, "LIKE"))
        matches = []

        class Summary:
            def __init__(self, doc_id, display, tooltip=None):
                self.id = doc_id
                self.display = display
                self.tooltip = tooltip
        for doc_id, title in query.execute(self.cursor).fetchall():
            if len(title) > 60:
                short_title = title[:57] + "..."
                summary = Summary(doc_id, short_title, title)
            else:
                summary = Summary(doc_id, title)
            matches.append(summary)
        return matches

    @cached_property
    def version(self):
        """Integer for a specific version of the selected document.

        Will be `None` if we don't yet have a version number.
        """

        version = self.fields.getvalue("version")
        if version:
            return int(version)
        if self.id and len(self.versions) == 1:
            return self.versions[0].id
        return None

    @cached_property
    def versions(self):
        """Version numbers with descriptions for the picklist."""

        class Version:
            def __init__(self, number, description):
                self.id = number
                self.description = description
        versions = [Version(-1, "Current Working Version")]
        fields = "num", "comment", "dt"
        query = self.Query("doc_version", *fields).order("num DESC")
        query.where(query.Condition("id", self.id))
        for row in query.execute(self.cursor).fetchall():
            date = row.dt.strftime("%Y-%m-%d")
            description = f"[V{row.num} {date}] {row.comment}"
            versions.append(Version(row.num, description))
        return versions


class Summary:
    """Table of content (and auxilliary) information for one PDQ summary."""

    from lxml import html as H
    FILTERS = (
        "name:Denormalization Filter: Summary Module",
        "name:Wrap nodes with Insertion or Deletion",
        "name:Clean up Insertion and Deletion",
        "name:Summaries TOC Report",
    )

    def __init__(self, control, row):
        """Remember the caller's information. Let properties do the real work.
        """

        self.control = control
        self.row = row

    def __lt__(self, other):
        """Support sorting a sequence of `Summary` objects."""
        return self.title.lower() < other.title.lower()

    @cached_property
    def boards(self):
        """String for the summary's PDQ Editorial board.

        A summary typically has multiple board links. Only one will
        match the controller's list of editorial boards shown on the
        picklist. For a Spanish summary, we have to find the English
        summary of which it is a translation, as that is the document
        which will have the link to the editorial board we need.

        2023-11-29: Requirements have changed, and now a summary can
        have more than one PDQ editorial board. Only include the ones
        which match the user's selection(s). See OCECDR-5298.
        """

        b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        t_path = "/Summary/TranslationOf/@cdr:ref"
        query = self.control.Query("query_term_pub b", "b.int_val").unique()
        if self.control.language == "english":
            query.where(query.Condition("b.path", b_path))
            query.where(query.Condition("b.doc_id", self.id))
        else:
            query.join("query_term_pub t", "t.int_val = b.doc_id")
            query.where(query.Condition("t.path", t_path))
            query.where(query.Condition("t.doc_id", self.id))
        if self.control.board and "all" not in self.control.board:
            query.where(query.Condition("b.int_val", self.control.board, "IN"))
        boards = []
        for row in query.execute(self.control.cursor).fetchall():
            board = self.control.boards.get(row.int_val)
            if board:
                boards.append(str(board))
        return boards

    @cached_property
    def html(self):
        """Filtered HTML for the report."""

        opts = dict(id=self.id, version=self.version)
        doc = Doc(self.control.session, **opts)
        result = doc.filter(*self.FILTERS, parms=self.parms)
        return str(result.result_tree).strip()

    @cached_property
    def id(self):
        """Unique CDR ID for the summary."""
        return self.row.doc_id

    @property
    def nodes(self):
        """Sequence of HTML elements to be added to the report.

        We use XSL/T filtering to generate the HTML fragments
        for the report for this summary, which we then parse
        so they can be added to the page object.

        Don't cache these, as they might need to appear in more
        than one place in the report. We do cache the filtered
        HTML string, though.
        """

        return self.H.fragments_fromstring(self.html)

    @cached_property
    def parms(self):
        """Parameters for XSL/T filtering."""

        level = str(self.control.level) or "999"
        flag = "Y" if self.control.include_id else "N"
        return dict(showLevel=level, showId=flag)

    @cached_property
    def title(self):
        """Title for the PDQ Summary document."""
        return self.row.title

    @cached_property
    def version(self):
        """Which version of the document do we want to filter?"""

        if self.control.selection_method == "board":
            return None
        if not self.control.version or self.control.version < 1:
            return None
        return self.control.version


if __name__ == "__main__":
    """Don't execute the script when loaded as a module."""
    Control().run()
