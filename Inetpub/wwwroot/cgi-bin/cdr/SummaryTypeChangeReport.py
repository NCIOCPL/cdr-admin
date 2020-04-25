#!/usr/bin/env python

"""Report on the types of changes recorded in selected Summaries.

BZIssue::None  (JIRA::OCECDR-3703)
OCECDR-3900: Modify the Summaries Type of Change report to display
             Spanish CAM summaries

                                           Alan Meyer, March 2014

JIRA::OCECDR-4217 - modify user interface for report
JIRA::OCECDR-4256 - fix date range filter bug
"""

from datetime import date
from cdrapi.docs import Doc
from cdrcgi import Controller
from cdr import URDATE, getSchemaEnumVals

import datetime
import cdr
import cdrcgi
from cdrapi import db


class Control(Controller):
    """
    Logic manager for report.
    """

    SUBTITLE = "Summaries Type of Change"
    INCLUDE = "include"
    EXCLUDE = "exclude"
    COMMENTS = INCLUDE, EXCLUDE
    CURRENT = "Current (most recent changes for each category of change)"
    HISTORICAL = "Historical (all changes for a given date range)"
    REPORT_TYPES = CURRENT, HISTORICAL
    BY_SUMMARY = "One table for all summaries and changes"
    BY_CHANGE_TYPE = "One table for each type of change"
    REPORT_ORGANIZATIONS = BY_SUMMARY, BY_CHANGE_TYPE

    def build_tables(self):
        """
        Overrides the base class's version of this method to assemble
        the tables to be displayed for this report. If the user
        chooses the "by summary title" method for selecting which
        summary to use for the report, and the fragment supplied
        matches more than one summary document, display the form
        a second time so the user can pick the summary.

        If we're ready to display the report, we have three options:
          1. a single table showing the latest changes in each
             category of change for each selected summary
          2. an historical report with a single table showing
             all changes falling within the specified date range
             for all selected summaries
          3. multiple tables, one for each type of change,
             showing all changes occurring withing the specified
             date range for all selected summaries
        """

        if self.selection_method == "title":
            if not self.fragment:
                cdrcgi.bail("Title fragment is required.")
            titles = self.summaries_for_title(self.fragment)
            if not self.summary_titles:
                cdrcgi.bail("No summaries match that title fragment")
            if len(titles) == 1:
                summaries = [Summary(self, titles[0].id)]
            else:
                opts = {
                    "buttons": self.buttons,
                    "action": self.script,
                    "subtitle": self.title,
                    "session": self.session
                }
                page = cdrcgi.Page(self.PAGE_TITLE, **opts)
                self.populate_form(form, titles)
                page.send()
        elif self.selection_method == "id":
            if not self.cdr_ids:
                cdrcgi.bail("At least one CDR ID is required.")
            summaries = [Summary(self, id) for id in self.cdr_ids]
        else:
            if not self.board:
                cdrcgi.bail("At least one board is required.")
            summaries = self.summaries_for_boards()

        # We have the summaries; build the report table(s).
        cols = self.get_cols()
        opts = { "banner": self.PAGE_TITLE, "subtitle": self.title }
        if self.report_type == self.CURRENT:
            opts["caption"] = "Type of Change Report (Most Recent Change)"
        elif self.report_org == self.BY_SUMMARY:
            caption = ["Type of Change Report (All Changes by Summary)"]
            caption.append(self.format_date_range())
        else:
            return self.get_change_type_tables(cols, summaries)
        rows = []
        for summary in sorted(summaries):
            rows.extend(summary.get_rows())
        return [cdrcgi.Report.Table(cols, rows, **opts)]

    def set_report_options(self, opts):
        """
        Take off the buttons and add the banners/titles.
        """

        opts["page_opts"]["buttons"] = []
        subtitle = f"Report produced {self.today}"
        opts["subtitle"] = subtitle
        if self.report_type == self.HISTORICAL:
            opts["subtitle"] += " -- %s" % self.format_date_range()
        report_type = self.report_type.split()[0]
        opts["banner"] = "Summary Type of Change Report - %s" % report_type
        return opts

    def populate_form(self, page, titles=None):
        """Put the fields on the form.

        Pass:
            page - `cdrcgi.HTMLPage` object
            titles - if not None, show the followup page for selecting
                     from multiple matches with the user's title fragment;
                     otherwise, show the report's main request form
        """

        page.form.append(page.hidden_field("debug", self.debug))
        opts = { "titles": titles, "id-label": "CDR ID(s)" }
        opts["id-tip"] = "separate multiple IDs with spaces"
        self.add_summary_selection_fields(page, **opts)
        fieldset = page.fieldset("Types of Change")
        for ct in self.all_types:
            checked = ct in self.change_types
            opts = dict(value=ct, checked=checked)
            fieldset.append(page.checkbox("change-type", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Comment Display")
        for value in self.COMMENTS:
            label = "%s Comments" % value.capitalize()
            if self.comments:
                checked = value == self.INCLUDE
            else:
                checked = value == self.EXCLUDE
            opts = dict(label=label, value=value, checked=checked)
            fieldset.append(page.radio_button("comments", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Type of Report")
        for value in self.REPORT_TYPES:
            checked = value == self.type
            opts = dict(value=value, checked=checked)
            fieldset.append(page.radio_button("type", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Date Range for Changes History")
        fieldset.set("class", "history")
        opts = dict(value=self.start, label="Start Date")
        fieldset.append(page.date_field("start", **opts))
        opts = dict(value=self.start, label="End Date")
        fieldset.append(page.date_field("end", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Report Organization")
        for organization in self.REPORT_ORGANIZATIONS:
            checked = organization == self.organization
            opts = dict(value=organization, checked=checked)
            fieldset.append(page.radio_button("organization", **opts))
        page.form.append(fieldset)
        page.add_output_options(default=self.format)
        args = "check_report_type", self.HISTORICAL, "history"
        page.add_script(self.toggle_display(*args))
        page.add_script("""\
jQuery(function() {
    check_report_type(jQuery("input[name='report-type']:checked").val());
});""")

    @property
    def all_types(self):
        """Valid type of change values parsed from the summary schema."""

        if not hasattr(self, "_all_types"):
            args = "SummarySchema.xml", "SummaryChangeType"
            self._all_types = sorted(cdr.getSchemaEnumVals(*args))
        return self._all_types

    @property
    def audience(self):
        """Selecting summaries for this audience."""

        if not hasattr(self, "_audience"):
            self._audience = self.fields.getvalue("audience")
            if self._audience:
                if self._audience not in self.AUDIENCES:
                    self.bail()
            else:
                self._audience = self.AUDIENCES[0]
        return self._audience

    @property
    def board(self):
        """PDQ board ID(s) selected by the user for the report."""

        if not hasattr(self, "_board"):
            boards = self.fields.getlist("board")
            if "all" in boards:
                self._board = ["all"]
            else:
                self._board = set()
                for id in boards:
                    try:
                        self._board.add(int(id))
                    except:
                        self.bail()
                self._board = list(self._board)
                if not self._board:
                    self._board = ["all"]
        return self._board

    @property
    def boards(self):
        """Dictionary of board names indexed by CDR Organization ID."""

        if not hasattr(self, "_boards"):
            self._boards = self.get_boards()
        return self._boards

    @property
    def cdr_ids(self):
        """Set of unique CDR ID integers."""

        if not hasattr(self, "_cdr_ids"):
            self._cdr_ids = set()
            for word in self.fields.getvalue("cdr-id", "").strip().split():
                try:
                    self._cdr_ids.add(Doc.extract_id(word))
                except:
                    self.bail("Invalid format for CDR ID")
        return self._cdr_ids

    @property
    def change_types(self):
        """Types of change selected by the user."""

        if not hasattr(self, "_change_types"):
            types = self.fields.getlist("change-type") or self.all_types
            if set(types) - set(self.all_types):
                self.bail()
            self._change_types = sorted(types)
        return self._change_types

    @property
    def comments(self):
        """True if the report should include comments."""

        if not hasattr(self, "_comments"):
            comments = self.fields.getvalue("comments")
            self._comments = comments != self.EXCLUDE
        return self._comments

    @property
    def debug(self):
        """True if we're running with increased logging."""

        if not hasattr(self, "_debug"):
            self._debug = True if self.fields.getvalue("debug") else False
        return self._debug

    @property
    def end(self):
        """End of date range for the historical version of the report."""

        if not hasattr(self, "_end"):
            end = self.fields.getvalue("end")
            self._end = self.parse_date(end) or self.today
        return self._end

    @property
    def fragment(self):
        """Title fragment for selecting a summary by title."""

        if not hasattr(self, "_fragment"):
            self._fragment = self.fields.getvalue("title")
        return self._fragment

    @property
    def language(self):
        """Selecting summaries for this language."""

        if not hasattr(self, "_language"):
            self._language = self.fields.getvalue("language")
            if self._language:
                if self._language not in self.LANGUAGES:
                    self.bail()
            else:
                self._language = self.LANGUAGES[0]
        return self._language

    @property
    def loglevel(self):
        """Override to support debug logging."""
        return "DEBUG" if self.debug else self.LOGLEVEL

    @property
    def organization(self):
        """Report organization (by summary or by change types)."""

        if not hasattr(self, "_organization"):
            organization = self.fields.getvalue("organization")
            self._organization = organization or self.BY_SUMMARY
            if self._organization not in self.REPORT_ORGANIZATIONS:
                self.bail()
        return self._organization

    @property
    def selection_method(self):
        """How are we choosing summaries?"""

        if not hasattr(self, "_selection_method"):
            self._selection_method = self.fields.getvalue("method", "board")
            if self._selection_method not in self.SUMMARY_SELECTION_METHODS:
                self.bail()
        return self._selection_method

    @property
    def start(self):
        """Start of date range for the historical version of the report."""

        if not hasattr(self, "_start"):
            start = self.fields.getvalue("start", URDATE)
            self._start = self.parse_date(start)
        return self._start

    @property
    def today(self):
        """Today's date object, used in several places."""

        if not hasattr(self, "_today"):
            self._today = date.today()
        return self._today

    @property
    def type(self):
        """Type of report (current or historical)."""

        if not hasattr(self, "_type"):
            self._type = self.fields.getvalue("type") or self.CURRENT
            if self._type not in self.REPORT_TYPES:
                self.bail()
        return self._type

    def summaries_for_boards(self):
        """
        The user has asked for a report of multiple summaries for
        one or more of the boards. Find the boards' summaries whose
        language match the request parameters, and return a list of
        Summary objects for them.
        """

        b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        t_path = "/Summary/TranslationOf/@cdr:ref"
        query = db.Query("active_doc d", "d.id")
        #query.join("pub_proc_cg c", "c.id = d.id")
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
        return [Summary(self, row[0]) for row in rows]

    def format_date_range(self):
        """
        Construct a string describing the date coverage for the report.
        """

        start_is_urdate = self.start <= cdr.URDATE
        end_is_today = self.end <= self.today
        if start_is_urdate:
            if end_is_today:
                return "Complete History"
            else:
                return "Through %s" % self.end
        elif end_is_today:
            return "From %s" % self.start
        return "%s - %s" % (self.start, self.end)

    def get_change_type_tables(self, cols, summaries):
        """
        Report each type of change in its own table.
        """

        opts = { "html_callback_pre": Control.table_spacer }
        tables = []
        title = "Type of Change Report"
        range = self.format_date_range()
        for change_type in self.change_types:
            rows = []
            for summary in summaries:
                rows.extend(summary.get_rows(change_type))
            if not rows:
                continue
            count = "%d change" % len(rows)
            if len(rows) > 1:
                count += "s"
            opts["caption"] = [title, change_type, "%s (%s)" % (range, count)]
            opts["sheet_name"] = change_type.split()[0]
            tables.append(cdrcgi.Report.Table(cols, rows, **opts))
        return tables

    @staticmethod
    def table_spacer(table, page):
        """
        Put some space before the table.
        """

        page.add_css("table { margin-top: 25px; }")

    def get_cols(self):
        """
        Create a sequence of column definitions for the output report.
        Number and types of columns depend on config parms.

        Return:
            Sequence of column definitions to add to object.
        """

        # Leftmost column is always a doc title and ID
        columns = [cdrcgi.Report.Column("Summary", width="220px")]

        # Basic reports need cols for types of change and comments
        if self.report_type == self.CURRENT:
            comment_column = cdrcgi.Report.Column("Comment", width="150px")
            for ct in sorted(self.change_types):
                columns.append(cdrcgi.Report.Column(ct, width="105px"))
                if self.comments:
                    columns.append(comment_column)

        # Historical reports
        else:
            columns.append(cdrcgi.Report.Column("Date", width="80px"))
            if self.report_org == self.BY_SUMMARY:
                col = cdrcgi.Report.Column("Type of Change", width="150px")
                columns.append(col)
            if self.comments:
                columns.append(cdrcgi.Report.Column("Comment", width="180px"))

        return columns


class Summary:
    """
    Represents one CDR Summary document.

    Attributes:
        id       -  CDR ID of summary document
        title    -  title of summary (from title column of all_docs table)
        control  -  object holding request parameters for report
        changes  -  information about changes made to the summary over time
    """

    Cell = cdrcgi.Report.Cell

    def __init__(self, control, doc_id):
        """
        Extract the title and change history from the CDR Summary document.
        """

        self.doc_id = doc_id
        self.control = control
        self.changes = []
        query = db.Query("document", "xml", "title")
        query.where(query.Condition("id", doc_id))
        xml, title = query.execute(control.cursor).fetchone()
        title = title.split(";")[0]
        root = etree.XML(xml.encode("utf-8"))
        self.title = cdr.get_text(root.find("SummaryTitle")) or title
        nodes = root.findall("TypeOfSummaryChange")
        self.changes = sorted([self.Change(control, node) for node in nodes])
        for change in self.changes:
            control.logger.debug("CDR%d %s", doc_id, change)
        self.key = (self.title.lower(), self.doc_id)
    def get_rows(self, change_type=None):
        if self.control.report_type == Control.CURRENT:
            return self.get_single_row()
        changes = self.get_changes(change_type)
        nrows = len(changes)
        if nrows < 1:
            return []
        rows = [
            [
                self.Cell(self.format_title(), rowspan=nrows),
                changes[0].date
            ]
        ]
        if not change_type:
            rows[0].append(changes[0].type)
        if self.control.comments:
            rows[0].append(" / ".join(changes[0].comments))
        for change in changes[1:]:
            row = [change.date]
            if not change_type:
                row.append(change.type)
            if self.control.comments:
                row.append(" / ".join(change.comments))
            rows.append(row)
        return rows
    def format_title(self):
        return "%s (%d)" % (self.title, self.doc_id)
    def get_single_row(self):
        change_types = dict([(ct, None) for ct in self.control.change_types])
        for change in self.changes:
            self.control.logger.debug("CDR%d: get_single_row(%s)", self.doc_id,
                                      change)
            if change.type in change_types:
                if change_types[change.type] is None:
                    change_types[change.type] = change
                elif self.control.comments:
                    latest_change = change_types[change.type]
                    if latest_change.date == change.date:
                        latest_change.comments.extend(change.comments)
        row = [self.format_title()]
        nchanges = 0
        for change_type in self.control.change_types:
            change = change_types.get(change_type)
            if change:
                nchanges += 1
            row.append(change and change.date or "")
            if self.control.comments:
                row.append(change and " / ".join(change.comments) or "")
        if nchanges > 0:
            return [row]
        return []

    def get_changes(self, change_type):
        """
        If we're building a separate table for each type of change,
        filter to get only the changes matching a single change type.
        Otherwise, return all the changes being reported for this
        summary. The `in_scope()` method also checks date range
        inclusion.
        """

        return [c for c in self.changes if c.in_scope(change_type)]

    class Change:
        """
        Information about a change event for a summary.

        Instance data:
            control - reference to the logic master object
            date - when the change was made
            comments - sequence of comments posted for the change
        """

        def __init__(self, control, node):
            self.control = control
            self.date = self.type = None
            self.comments = []
            for child in node:
                if child.tag == "TypeOfSummaryChangeValue":
                    self.type = cdr.get_text(child)
                elif child.tag == "Date":
                    self.date = cdr.get_text(child)
                elif child.tag == "Comment":
                    if control.comments:
                        comment = cdr.get_text(child)
                        if comment:
                            self.comments.append(comment)

        def in_scope(self, change_type):
            """
            Find out if this change should appear on the report.

            The determination is made by checking the change type
            and (if this is an historical report), the change's date.
            """

            if change_type and self.type != change_type:
                return False
            control = self.control
            if self.type not in control.change_types:
                return False
            if control.report_type == Control.HISTORICAL:
                if not self.date:
                    return False
                if not (control.start <= self.date <= control.end):
                    return False
            return True

        def __str__(self):
            """
            Create a debugging string for the change.
            """

            return "[%s %s]" % (self.type, self.date)

        def __lt__(self, other):
            """
            Support sorting of the change events.

            Change request 2017-01-27 to reverse the date sort.
            """

            return (other.date, self.type) < (self.date, other.type)

    def __lt__(self, other):
        """
        Support sorting the summaries by title.
        """

        return self.key < other.key

Control().run()
