#!/usr/bin/env python

"""Report on the types of changes recorded in selected Summaries.
"""

from datetime import date
from functools import cached_property
from cdrapi.docs import Doc
from cdrcgi import Controller, BasicWebPage
from cdr import URDATE, getSchemaEnumVals


class Control(Controller):
    """
    Logic manager for report.
    """

    SUBTITLE = "Summaries Type of Change"
    LOGNAME = "SummaryTypeChangeReport"
    INCLUDE = "include"
    EXCLUDE = "exclude"
    COMMENTS = INCLUDE, EXCLUDE
    CURRENT = "Current (most recent changes for each category of change)"
    HISTORICAL = "Historical (all changes for a given date range)"
    REPORT_TYPES = CURRENT, HISTORICAL
    BY_SUMMARY = "One table for all summaries and changes"
    BY_CHANGE_TYPE = "One table for each type of change"
    REPORT_ORGANIZATIONS = BY_SUMMARY, BY_CHANGE_TYPE
    MODULES = (
        ("both", "Summaries and Modules"),
        ("summaries", "Summaries Only"),
        ("modules", "Modules Only"),
    )

    def build_tables(self):
        """Callback which the Excel version of the report will need."""
        return self.tables

    def show_report(self):
        """Report tables are too wide for the standard HTML layout."""

        if not self.ready:
            return self.show_form()
        if self.format == "excel":
            return self.report.send("excel")
        title = "Summary Changes"
        if self.type == self.HISTORICAL:
            title = f"Summary Changes -- {self.date_range}"
        else:
            title = "Current Summary Changes"
        report = BasicWebPage()
        report.wrapper.append(report.B.H1(title))
        for table in self.tables:
            report.wrapper.append(table.node)
        report.wrapper.append(self.footer)
        report.head.append(report.B.STYLE("table { margin-bottom: 3rem; }"))
        report.send()

    def populate_form(self, page):
        """Put the fields on the form.

        Pass:
            page - `cdrcgi.HTMLPage` object
        """

        page.form.append(page.hidden_field("debug", self.debug or ""))
        opts = {"titles": self.summary_titles, "id-label": "CDR ID(s)"}
        opts["id-tip"] = "separate multiple IDs with spaces"
        self.add_summary_selection_fields(page, **opts)
        fieldset = page.fieldset("Include")
        fieldset.set("class", "by-board-block usa-fieldset")
        for value, label in self.MODULES:
            checked = value == self.modules
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("modules", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Types of Change")
        for ct in self.all_types:
            checked = ct in self.change_types
            opts = dict(value=ct, checked=checked)
            fieldset.append(page.checkbox("change-type", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Comment Display")
        for value in self.COMMENTS:
            label = f"{value.capitalize()} Comments"
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
        fieldset.set("class", "history usa-fieldset")
        opts = dict(value=self.start, label="Start Date")
        fieldset.append(page.date_field("start", **opts))
        opts = dict(value=self.end, label="End Date")
        fieldset.append(page.date_field("end", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Report Organization", id="rep-org")
        fieldset.set("class", "history usa-fieldset")
        for organization in self.REPORT_ORGANIZATIONS:
            checked = organization == self.organization
            opts = dict(value=organization, checked=checked)
            fieldset.append(page.radio_button("organization", **opts))
        page.form.append(fieldset)
        page.add_output_options(default=self.format)
        args = "check_type", self.HISTORICAL, "history"
        page.add_script(self.toggle_display(*args))
        page.add_script("""\
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("input[name='type']").forEach(button => {
    button.addEventListener("click", () => check_type(button.value));
  });
  const type = document.querySelector("input[name='type']:checked");
  check_type(type.value ?? "");
});
""")

    @cached_property
    def all_types(self):
        """Valid type of change values parsed from the summary schema."""

        args = "SummarySchema.xml", "SummaryChangeType"
        return sorted(getSchemaEnumVals(*args))

    @cached_property
    def audience(self):
        """Selecting summaries for this audience."""

        audience = self.fields.getvalue("audience")
        if not audience:
            return self.AUDIENCES[0]
        if audience not in self.AUDIENCES:
            self.bail()
        return audience

    @cached_property
    def board(self):
        """PDQ board ID(s) selected by the user for the report."""

        values = self.fields.getlist("board")
        if not values or "all" in values:
            return ["all"]
        boards = set()
        for value in values:
            try:
                boards.add(int(value))
            except Exception:
                self.bail()
        return list(boards)

    @cached_property
    def boards(self):
        """Dictionary of board names indexed by CDR Organization ID."""
        return self.get_boards()

    @cached_property
    def board_summaries(self):
        """`Summary` objects for the selected board(s), etc."""

        a_path = "/Summary/SummaryMetaData/SummaryAudience"
        b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        l_path = "/Summary/SummaryMetaData/SummaryLanguage"
        t_path = "/Summary/TranslationOf/@cdr:ref"
        m_path = "/Summary/@AvailableAsModule"
        query = self.Query("active_doc d", "d.id")
        query.join("query_term_pub a", "a.doc_id = d.id")
        query.where(query.Condition("a.path", a_path))
        query.where(query.Condition("a.value", self.audience + "s"))
        query.join("query_term_pub l", "l.doc_id = d.id")
        query.where(query.Condition("l.path", l_path))
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
        if self.modules == "modules":
            query.join("query_term_pub m", "m.doc_id = d.id")
            query.where(query.Condition("m.path", m_path))
        elif self.modules == "summaries":
            query.outer("query_term_pub m", "m.doc_id = d.id",
                        f"m.path = '{m_path}'")
            query.where("m.doc_id IS NULL")
        rows = query.unique().execute(self.cursor).fetchall()
        return [Summary(self, row.id) for row in rows]

    @cached_property
    def cdr_id(self):
        """String entered by the user for selection by CDR ID."""
        return self.fields.getvalue("cdr-id")

    @cached_property
    def cdr_ids(self):
        """Integers for the selected documents, populated by `ready()`."""
        return set()

    @cached_property
    def change_type_tables(self):
        """Report each type of change in its own table."""

        tables = []
        title = "Type of Change Report"
        range = self.date_range
        for change_type in self.change_types:
            rows = []
            for summary in self.summaries:
                rows.extend(summary.get_rows(change_type))
            if not rows:
                continue
            count = f"{len(rows):d} change"
            if len(rows) > 1:
                count += "s"
            opts = dict(
                caption=(title, change_type, f"{range} ({count})"),
                sheet_name=change_type.split()[0],
                columns=self.columns,
                classes="change_type_table",
            )
            tables.append(self.Reporter.Table(rows, **opts))
        return tables

    @cached_property
    def change_types(self):
        """Types of change selected by the user."""

        types = self.fields.getlist("change-type") or self.all_types
        if set(types) - set(self.all_types):
            self.bail()
        return sorted(types)

    @cached_property
    def columns(self):
        """Sequence of column definitions for the output report.

        Number and types of columns depend on config parms.
        """

        # We'll use this a lot.
        Column = self.Reporter.Column

        # Leftmost column is always a doc title and ID.
        columns = [Column("Summary", width="220px")]

        # Basic reports need cols for types of change and comments.
        if self.type == self.CURRENT:
            if self.comments:
                comment_column = Column("Comment", width="150px")
            for change_type in sorted(self.change_types):
                columns.append(Column(change_type, width="105px"))
                if self.comments:
                    columns.append(comment_column)

        # Historical reports.
        else:
            columns.append(Column("Date", width="80px"))
            if self.organization == self.BY_SUMMARY:
                col = Column("Type of Change", width="150px")
                columns.append(col)
            if self.comments:
                columns.append(Column("Comment", width="180px"))

        # Don't specify widths for the HTML version of the report.
        if self.format == "html":
            return [column.name for column in columns]

        return columns

    @cached_property
    def comments(self):
        """True if the report should include comments."""
        return self.fields.getvalue("comments") != self.EXCLUDE

    @cached_property
    def date_range(self):
        """String describing the date coverage for the report."""

        start_is_urdate = str(self.start) <= URDATE
        end_is_today = self.end >= self.today
        if start_is_urdate:
            if end_is_today:
                return "Complete History"
            else:
                return f"Through {self.end}"
        elif end_is_today:
            return f"From {self.start}"
        else:
            return f"{self.start} - {self.end}"

    @cached_property
    def debug(self):
        """True if we're running with increased logging."""
        return True if self.fields.getvalue("debug") else False

    @cached_property
    def end(self):
        """End of date range for the historical version of the report."""
        return self.parse_date(self.fields.getvalue("end")) or self.today

    @cached_property
    def fragment(self):
        """Title fragment for selecting a summary by title."""
        return self.fields.getvalue("title")

    @cached_property
    def language(self):
        """Selecting summaries for this language."""

        language = self.fields.getvalue("language") or self.LANGUAGES[0]
        if language not in self.LANGUAGES:
            self.bail()
        return language

    @cached_property
    def loglevel(self):
        """Override to support debug logging."""
        return "DEBUG" if self.debug else self.LOGLEVEL

    @cached_property
    def modules(self):
        """How to handle modules in summary selection."""

        modules = self.fields.getvalue("modules", "both")
        if modules not in [m[0] for m in self.MODULES]:
            self.bail()
        return modules

    @cached_property
    def organization(self):
        """Report organization (by summary or by change types)."""

        organization = self.fields.getvalue("organization") or self.BY_SUMMARY
        if organization not in self.REPORT_ORGANIZATIONS:
            self.bail()
        return organization

    @cached_property
    def ready(self):
        """True if we have what is needed for the report."""

        # If we're just getting started, we can't be ready.
        if not self.request:
            return False

        # Check conditions specific to the selection method chosen.
        match self.selection_method:
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
            case "board":
                if not self.board:
                    message = "At least one board is required."
                    self.alerts.append(dict(message=message, type="error"))
                if not self.board_summaries:
                    target = f"{self.language} {self.audience} summaries"
                    action = "to report on"
                    message = f"No {target} {action} for selected board(s)."
                    self.alerts.append(dict(message=message, type="warning"))
            case _:
                # Shouldn't happen, unless a hacker is at work.
                self.bail()

        # We're ready if no alerts have been queued.
        return False if self.alerts else True

    @cached_property
    def start(self):
        """Start of date range for the historical version of the report."""
        return self.parse_date(self.fields.getvalue("start", URDATE))

    @cached_property
    def summaries(self):
        """PDQ summaries selected for the report.

        If the user chooses the "by summary title" method for
        selecting which summary to use for the report, and the
        fragment supplied matches more than one summary document,
        display the form a second time so the user can pick the
        summary.
        """

        match self.selection_method:
            case "board":
                return sorted(self.board_summaries)
            case "id":
                return [Summary(self, id) for id in self.cdr_ids]
            case "title":
                return [Summary(self, self.titles[0].id)]
            case _:
                self.bail()

    @cached_property
    def tables(self):
        """Assemble the table(s) for the report.

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

        tables = None
        if self.type == self.CURRENT:
            caption = "Type of Change Report (Most Recent Change)"
        elif self.organization == self.BY_SUMMARY:
            caption = "Type of Change Report (All Changes by Summary)"
            caption = caption, self.date_range
        else:
            tables = self.change_type_tables
        if tables is None:
            opts = dict(caption=caption, columns=self.columns)
            rows = []
            for summary in self.summaries:
                rows.extend(summary.get_rows())
            tables = [self.Reporter.Table(rows, **opts)]
        return tables

    @cached_property
    def today(self):
        """Today's date object, used in several places."""
        return date.today()

    @cached_property
    def type(self):
        """Type of report (current or historical)."""

        type = self.fields.getvalue("type") or self.CURRENT
        if type not in self.REPORT_TYPES:
            self.bail()
        return type


class Summary:
    """
    Represents one CDR Summary document.

    Attributes:
        id       -  CDR ID of summary document
        title    -  title of summary (from title column of all_docs table)
        control  -  object holding request parameters for report
        changes  -  information about changes made to the summary over time
    """

    def __init__(self, control, doc_id):
        """Remember the caller's values.

        Pass:
            control - access to the database and the report options
            doc_id - integer for the PDQ summary's unique CDR document ID
        """

        self.control = control
        self.id = doc_id

    def __lt__(self, other):
        """Support sorting the summaries by title."""
        return self.key < other.key

    def get_rows(self, change_type=None):
        """Get all or a subset of the report rows for the summary's changes.

        Pass:
            change_type - optional string identifying a subset of the changes

        Return:
            A sequence of report rows tuples
        """

        if self.control.type == Control.CURRENT:
            return self.__get_single_row()
        changes = self.__get_changes(change_type)
        nrows = len(changes)
        if nrows < 1:
            return []
        row = [
            self.control.Reporter.Cell(self.display_title, rowspan=nrows),
            changes[0].date,
        ]
        if not change_type:
            row.append(changes[0].type)
        if self.control.comments:
            row.append(" / ".join(changes[0].comments))
        rows = [tuple(row)]
        for change in changes[1:]:
            row = [self.control.Reporter.Cell(change.date, classes="nowrap")]
            if not change_type:
                row.append(change.type)
            if self.control.comments:
                row.append(" / ".join(change.comments))
            rows.append(tuple(row))
        return rows

    @cached_property
    def doc(self):
        """`Doc` object for the summary's CDR document."""
        return Doc(self.control.session, id=self.id)

    @cached_property
    def changes(self):
        """Record of modifications made throughout the life of the summary."""

        changes = []
        for node in self.doc.root.findall("TypeOfSummaryChange"):
            change = self.Change(self.control, node)
            self.control.logger.debug("CDR%d %s", self.id, change)
            changes.append(change)
        return sorted(changes)

    @cached_property
    def display_title(self):

        display_title = f"{self.title} ({self.id:d})"
        if self.doc.root.get("AvailableAsModule") == "Yes":
            display_title += " [Module]"
        return display_title

    @cached_property
    def key(self):
        """Control how the summaries are sorted."""
        return self.title.lower(), self.id

    @cached_property
    def title(self):
        """Official title of the PDQ summary."""

        title = Doc.get_text(self.doc.root.find("SummaryTitle"))
        return title or self.doc.title.split(";")[0]

    def __get_changes(self, change_type):
        """
        If we're building a separate table for each type of change,
        filter to get only the changes matching a single change type.
        Otherwise, return all the changes being reported for this
        summary. The `in_scope()` method also checks date range
        inclusion.
        """

        return [c for c in self.changes if c.in_scope(change_type)]

    def __get_single_row(self):
        """For the "current" report, put the latest changes in one row."""

        change_types = dict([(ct, None) for ct in self.control.change_types])
        for change in self.changes:
            args = self.id, change
            self.control.logger.debug("CDR%d: get_single_row(%s)", *args)
            if change.type in change_types:
                if change_types[change.type] is None:
                    change_types[change.type] = change
                elif self.control.comments:
                    latest_change = change_types[change.type]
                    if latest_change.date == change.date:
                        latest_change.comments.extend(change.comments)
        row = [self.display_title]
        nchanges = 0
        Cell = self.control.Reporter.Cell
        for change_type in self.control.change_types:
            change = change_types.get(change_type)
            if change:
                nchanges += 1
            row.append(Cell(change and change.date or "", classes="nowrap"))
            if self.control.comments:
                row.append(change and " / ".join(change.comments) or "")
        if nchanges > 0:
            return [tuple(row)]
        return []

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
                    self.type = Doc.get_text(child)
                elif child.tag == "Date":
                    self.date = Doc.get_text(child)
                elif child.tag == "Comment":
                    if control.comments:
                        comment = Doc.get_text(child)
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
            if control.type == Control.HISTORICAL:
                if not self.date:
                    return False
                if not (str(control.start) <= self.date <= str(control.end)):
                    return False
            return True

        def __str__(self):
            """
            Create a debugging string for the change.
            """

            return f"[{self.type} {self.date}]"

        def __lt__(self, other):
            """
            Support sorting of the change events.

            Change request 2017-01-27 to reverse the date sort.
            """

            return (other.date, self.type) < (self.date, other.type)


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
