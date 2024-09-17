#!/usr/bin/env python

"""Show the tables of contents for one or more Cancer Information Summaries.
"""

from collections import defaultdict
from functools import cached_property
from cdrcgi import Controller, HTMLPage, bail
from cdrapi import db
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

    def add_audience_fieldset(self, page):
        """Add the radio buttons for choosing the audience.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        fieldset = page.fieldset("Audience")
        fieldset.set("class", "board-fieldset")
        checked = True
        for audience in self.AUDIENCES:
            opts = dict(value=audience, checked=checked)
            fieldset.append(page.radio_button("audience", **opts))
            checked = False
        page.form.append(fieldset)

    def add_board_fieldset(self, page):
        """Add the checkboxes for selecting one or more PDQ boards.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        fieldset = page.fieldset("Board(s)")
        fieldset.set("class", "board-fieldset")
        opts = dict(value="all", label="All Boards", checked=True)
        fieldset.append(page.checkbox("board", **opts))
        for board in sorted(self.boards.values()):
            opts = dict(value=board.id, label=str(board))
            fieldset.append(page.checkbox("board", **opts))
        page.form.append(fieldset)

    def add_cdrid_fieldset(self, page):
        """Add the field for the summary document ID.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        fieldset = page.fieldset("Summary Document ID")
        fieldset.set("id", "cdrid-fieldset")
        fieldset.append(page.text_field("id", label="CDR ID"))
        page.form.append(fieldset)

    def add_language_fieldset(self, page):
        """Add the radio buttons for choosing between English and Spanish.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        fieldset = page.fieldset("Language")
        fieldset.set("class", "board-fieldset")
        checked = True
        for language in self.LANGUAGES:
            opts = dict(value=language, checked=checked)
            fieldset.append(page.radio_button("language", **opts))
            checked = False
        page.form.append(fieldset)

    def add_level_fieldset(self, page):
        """Add a picklist for choosing how deep the report should go.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        fieldset = page.fieldset("Table of Contents Depth")
        options = [("", "All Levels")] + [str(n) for n in range(1, 10)]
        tooltip = f"QC report uses level {self.DEFAULT_LEVEL:d}"
        default = str(self.DEFAULT_LEVEL)
        opts = dict(options=options, default=default, tooltip=tooltip)
        fieldset.append(page.select("level", **opts))
        page.form.append(fieldset)

    def add_method_fieldset(self, page):
        """Add the fields for choosing how summaries will be selected.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        fieldset = page.fieldset("Selection Method")
        checked = True
        for value, display in self.METHODS:
            opts = dict(value=value, label=display, checked=checked)
            fieldset.append(page.radio_button("method", **opts))
            checked = False
        page.form.append(fieldset)

    def add_options_fieldset(self, page):
        """Add the checkbox for choosing whether to display Summary CDR IDs.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        fieldset = page.fieldset("Options")
        opts = dict(value="include_id", label="Include CDR ID", checked=True)
        fieldset.append(page.checkbox("include_id", **opts))
        page.form.append(fieldset)

    def add_title_fieldset(self, page):
        """Add the field for entering a summary title fragment.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        fieldset = page.fieldset("Summary Title")
        fieldset.set("id", "title-fieldset")
        fieldset.append(page.text_field("title", label="Title"))
        page.form.append(fieldset)

    def build_tables(self):
        """Show the report if we have all the information we need.

        We might not, as there are at least two stages of cascading
        forms (sometimes three) to get through before we get to the
        point where we're ready to actually create the report when
        the user wants to zero in on a single summary.
        """

        if self.selection_method == "board" or self.version and self.id:
            self.report_page.send()
        elif self.id:
            self.show_version_form()
        elif self.fragment:
            self.show_title_form()
        else:
            self.show_form()

    def populate_form(self, page):
        """Assemble the main form for this report.

        Broken into helper methods, since this is a complex form.
        We add some client-side scripting to make the form easier
        to use.

        Pass:
            page - HTMLPage object to be filled with field sets.
        """

        self.add_method_fieldset(page)
        self.add_cdrid_fieldset(page)
        self.add_title_fieldset(page)
        self.add_board_fieldset(page)
        self.add_audience_fieldset(page)
        self.add_language_fieldset(page)
        self.add_level_fieldset(page)
        self.add_options_fieldset(page)
        page.add_script("""\
function check_method(value) {
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
});""")

    def show_title_form(self):
        """Let the user pick a summary from those which match her fragment."""

        if not self.fragment_matches:
            bail("No summaries match that title fragment")
        page = self.form_page
        page.form.append(page.hidden_field("method", value="id"))
        page.form.append(page.hidden_field("level", self.level))
        if self.include_id:
            page.form.append(page.hidden_field("include_id", "Y"))
        fieldset = page.fieldset("Choose Summary")
        fieldset.set("style", "width: 600px")
        for summary in self.fragment_matches:
            opts = dict(value=summary.id, label=summary.display)
            if summary.tooltip:
                opts["tooltip"] = summary.tooltip
            fieldset.append(page.radio_button("id", **opts))
        page.form.append(fieldset)
        page.send()

    def show_version_form(self):
        """We have a summary id, let the user pick a version."""

        page = self.form_page
        page.form.append(page.hidden_field("method", value="id"))
        page.form.append(page.hidden_field("id", value=self.id))
        page.form.append(page.hidden_field("level", self.level))
        if self.include_id:
            page.form.append(page.hidden_field("include_id", "Y"))
        fieldset = page.fieldset("Select Document Version")
        fieldset.set("style", "width: 600px")
        options = [(v.id, v.description) for v in self.versions]
        fieldset.append(page.select("version", options=options))
        page.form.append(fieldset)
        page.send()

    @property
    def audience(self):
        """Either patient or health_professional."""

        if not hasattr(self, "_audience"):
            self._audience = self.fields.getvalue("audience")
            if self._audience and self._audience not in self.AUDIENCES:
                bail()
        return self._audience

    @property
    def board(self):
        """Board(s) which the user has selected.

        Sequence of board IDs or ["all"] if the user wants all boards
        included.
        """

        return self.fields.getlist("board")

    @property
    def boards(self):
        """PDQ boards for the form's picklist."""

        if not hasattr(self, "_boards"):
            self._boards = Board.get_boards(cursor=self.cursor)
        return self._boards

    @property
    def fragment(self):
        """Title fragment used to find matching summaries."""

        if not hasattr(self, "_fragment"):
            self._title = (self.fields.getvalue("title") or "").strip()
        return self._title

    @cached_property
    def fragment_matches(self):
        """Information about summaries which match the title fragment."""

        if not self.fragment:
            bail("No title fragment to match")
        pattern = f"{self.fragment}%"
        query = db.Query("document d", "d.id", "d.title").order(2, 1)
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'Summary'")
        query.where(query.Condition("d.title", pattern, "LIKE"))
        fragment_matches = []

        class _Summary:
            def __init__(self, doc_id, display, tooltip=None):
                self.id = doc_id
                self.display = display
                self.tooltip = tooltip
        for doc_id, title in query.execute(self.cursor).fetchall():
            if len(title) > 60:
                short_title = title[:57] + "..."
                summary = _Summary(doc_id, short_title, title)
            else:
                summary = _Summary(doc_id, title)
            fragment_matches.append(summary)
        return fragment_matches

    @cached_property
    def id(self):
        """CDR document ID for the summary to be used for the report."""

        doc_id = self.fields.getvalue("id")
        if doc_id:
            try:
                doc = Doc(self.session, id=doc_id)
                doctype = doc.doctype.name
                if doctype != "Summary":
                    self.bail(f"CDR{doc.id} is a {doctype} document.")
            except Exception:
                self.bail(f"Document {doc_id} was not found")
            return doc.id
        if self.fragment and len(self.fragment_matches) == 1:
            return self.fragment_matches[0].id
        return None

    @cached_property
    def include_id(self):
        """Boolean indicating whether Summary CDR IDs should be displayed."""

        return True if self.fields.getvalue("include_id") else False

    @property
    def language(self):
        """Either english or spanish."""

        if not hasattr(self, "_language"):
            self._language = self.fields.getvalue("language")
            if self._language and self._language not in self.LANGUAGES:
                bail()
        return self._language

    @cached_property
    def level(self):
        """Integer indicating how deep the report should go."""

        return self.fields.getvalue("level") or "999"

    @property
    def selection_method(self):
        """One of board, id, or title."""

        return self.fields.getvalue("method")

    @cached_property
    def report_page(self):
        """Assemble the HTMLPage object for the report.

        This is a non-tabular report, so we create the page ourselves,
        instead of letting the base class take care of that for us.
        """

        self.logger.info("processing %d summaries", len(self.summaries))
        page = HTMLPage(self.title, subtitle=self.report_title)
        page.body.set("id", "summaries-toc-report")
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
                page.body.append(page.B.H4(board))
            for summary in boards[board]:
                for node in summary.nodes:
                    page.body.append(node)
        return page

    @property
    def report_title(self):
        """Create the string identifying which report this is."""

        if not hasattr(self, "_report_title"):
            if self.selection_method == "id":
                self._report_title = "Single Summary TOC Report"
            else:
                audience = self.AUDIENCES.get(self.audience) or ""
                language = self.language.title()
                self._report_title = f"PDQ {language} {audience} Summaries"
        return self._report_title

    @property
    def summaries(self):
        """PDQ summaries (`Summary` objects) to be displayed on the report."""

        if not hasattr(self, "_summaries"):
            fields = "q.doc_id", "q.value AS title"
            if self.id:
                query = db.Query("query_term q", *fields).unique()
                query.where(query.Condition("doc_id", self.id))
            else:
                audience = f"{self.AUDIENCES.get(self.audience)}s"
                language = self.language.title()
                b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
                t_path = "/Summary/TranslationOf/@cdr:ref"
                a_path = "/Summary/SummaryMetaData/SummaryAudience"
                l_path = "/Summary/SummaryMetaData/SummaryLanguage"
                query = db.Query("query_term q", *fields).unique()
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
            self._summaries = [Summary(self, row) for row in rows]
        return self._summaries

    @property
    def version(self):
        """Integer for a specific version of the selected document.

        Will be `None` if we don't yet have a version number.
        """

        if not hasattr(self, "_version"):
            self._version = self.fields.getvalue("version")
            if self._version:
                self._version = int(self._version)
            elif self.id and len(self.versions) == 1:
                self._version = self.versions[0].id
        return self._version

    @property
    def versions(self):
        """Version numbers with descriptions for the picklist."""

        if not hasattr(self, "_versions"):
            class Version:
                def __init__(self, number, description):
                    self.id = number
                    self.description = description
            self._versions = [Version(-1, "Current Working Version")]
            fields = "num", "comment", "dt"
            query = db.Query("doc_version", *fields).order("num DESC")
            query.where(query.Condition("id", self.id))
            for row in query.execute(self.cursor).fetchall():
                date = row.dt.strftime("%Y-%m-%d")
                description = f"[V{row.num} {date}] {row.comment}"
                self._versions.append(Version(row.num, description))
        return self._versions


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

        self.__control = control
        self.__row = row

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
        query = db.Query("query_term_pub b", "b.int_val").unique()
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
    def control(self):
        """Access to report parameters and database connectivity."""
        return self.__control

    @cached_property
    def html(self):
        """Filtered HTML for the report."""

        opts = dict(id=self.id, version=self.version)
        doc = Doc(self.control.session, **opts)
        result = doc.filter(*self.FILTERS, parms=self.parms)
        return str(result.result_tree).strip()

    @property
    def id(self):
        """Unique CDR ID for the summary."""
        return self.__row.doc_id

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

    @property
    def parms(self):
        """Parameters for XSL/T filtering."""
        level = str(self.control.level) or "999"
        flag = "Y" if self.control.include_id else "N"
        return dict(showLevel=level, showId=flag)

    @property
    def title(self):
        """Title for the PDQ Summary document."""
        return self.__row.title

    @property
    def version(self):
        """Which version of the document do we want to filter?"""
        if self.control.selection_method == "board":
            return None
        if not self.control.version or self.control.version < 1:
            return None
        return self.control.version

    def __lt__(self, other):
        """Support sorting a sequence of `Summary` objects."""
        return self.title.lower() < other.title.lower()


if __name__ == "__main__":
    """Don't execute the script when loaded as a module."""
    Control().run()
