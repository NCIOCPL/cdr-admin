#!/usr/bin/env python

"""Report on the types of changes recorded in selected Drug Info Summaries.

   (adapted from SummaryTypeChangeReport.py written by BK)
"""

from functools import cached_property
from datetime import date
from cdrapi.docs import Doc
from cdrcgi import Controller, BasicWebPage
from cdr import URDATE, getSchemaEnumVals


class Control(Controller):
    """Logic manager for report."""

    SUBTITLE = "DIS Type of Change"
    LOGNAME = "DISTypeChangeReport"
    INCLUDE = "include"
    EXCLUDE = "exclude"
    COMMENTS = INCLUDE, EXCLUDE
    CURRENT = "Current (most recent changes for each category of change)"
    HISTORICAL = "Historical (all changes for a given date range)"
    REPORT_TYPES = CURRENT, HISTORICAL
    BY_SUMMARY = "One table for all drug info summaries and changes"
    BY_CHANGE_TYPE = "One table for each type of change"
    REPORT_ORGANIZATIONS = BY_SUMMARY, BY_CHANGE_TYPE
    INSTRUCTIONS = (
        "To run this report for multiple drug information summaries, select "
        "'By CDR ID' and enter multiple CDR IDs separated by a comma. "
        "To run the report for all "
        "drug information summaries, refer to the ad-hoc query "
        "'DIS CDR IDs for Type of Change Report' on the ",
        "CDR Stored Database Queries",
        "/cgi-bin/cdr/CdrQueries.py?query=DIS CDR IDs for "
        "Type of Change Report",
        " page. Copy and paste the complete set of CDR IDs into the "
        "CDR ID field."
    )

    def build_tables(self):
        """Pass on the tables property."""
        return self.tables

    def show_report(self):
        """Overridden to widen single report table with many columns."""

        if not self.ready:
            self.show_form()
        if self.format == "excel":
            return self.report.send("excel")
        report = BasicWebPage()
        report.wrapper.append(report.B.H1(self.subtitle))
        for table in self.tables:
            report.wrapper.append(table.node)
        report.wrapper.append(self.footer)
        if len(self.tables) > 1:
            report.head.append(report.B.STYLE("h1 { text-align: center; }"))
            report.head.append(report.B.STYLE("table {margin: 2rem auto; }"))
        return report.send()

    def populate_form(self, page):
        """Put the fields on the form.

        Pass:
            page - `cdrcgi.HTMLPage` object
        """

        # Don't bother if we already have what we need.
        if self.ready:
            self.show_report()

        # Explain how the report works.
        fieldset = page.fieldset("Instructions")
        instructions = page.B.P(
            self.INSTRUCTIONS[0],
            page.B.A(
                self.INSTRUCTIONS[1],
                target="_blank",
                href=self.INSTRUCTIONS[2]
            ),
            self.INSTRUCTIONS[3]
        )
        fieldset.append(instructions)
        page.form.append(fieldset)

        # Add the fields for selecting documents for the report.
        # --------------------------------------------------------------
        # Show the second stage in a cascading sequence of the form if we
        # have invoked this method directly from build_tables(). Widen
        # the form to accomodate the length of the title substrings
        # we're showing.
        # --------------------------------------------------------------
        if self.titles:
            page.form.append(page.hidden_field("selection_method", "id"))
            fieldset = page.fieldset("Choose Drug Info Summary")
            for t in self.titles:
                opts = dict(label=t.display, value=t.id, tooltip=t.tooltip)
                fieldset.append(page.radio_button("cdr-id", **opts))
            page.form.append(fieldset)

        else:

            # Fields for the original form.
            fieldset = page.fieldset("Selection Method")
            default = self.selection_method
            if default not in ("id", "title"):
                default = "title"
            methods = "CDR ID", "Drug Info Summary Title"
            for method in methods:
                value = method.split()[-1].lower()
                checked = value == default
                opts = dict(label=f"By {method}", value=value, checked=checked)
                fieldset.append(page.radio_button("selection_method", **opts))
            page.form.append(fieldset)

            fieldset = page.fieldset("Drug Info Summary ID(s)")
            fieldset.set("class", "by-id-block usa-fieldset")
            tooltip = "separate multiple IDs with spaces"
            opts = dict(label="CDR ID(s)", tooltip=tooltip, value=self.cdr_ids)
            fieldset.append(page.text_field("cdr-id", **opts))
            page.form.append(fieldset)

            fieldset = page.fieldset("Drug Info Summary Title")
            fieldset.set("class", "by-title-block usa-fieldset")
            tooltip = "Use wildcard (%) as appropriate."
            fieldset.append(page.text_field("title", tooltip=tooltip))
            page.form.append(fieldset)
            page.add_script(self.summary_selection_js)

        # Add the remaining report filtering and display options.
        fieldset = page.fieldset("Types of Change")
        for ct in self.all_dis_types:
            checked = ct in self.change_types
            opts = dict(label=ct, value=ct, checked=checked)
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
        fieldset = page.fieldset("Report Organization")
        for organization in self.REPORT_ORGANIZATIONS:
            checked = organization == self.organization
            opts = dict(value=organization, checked=checked)
            fieldset.append(page.radio_button("organization", **opts))
        page.form.append(fieldset)

        # Let the user choose the report format and add the final bits.
        page.add_output_options(default=self.format)
        page.form.append(page.hidden_field("debug", self.debug or ""))
        args = "check_type", self.HISTORICAL, "history"
        page.add_script(self.toggle_display(*args))
        page.add_script("""\
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("input[name='type']").forEach(button => {
    button.addEventListener("click", () => check_type(button.value));
  });
  document.querySelectorAll("input[name='selection_method']").forEach(button => {
    button.addEventListener("click", () => check_selection_method(button.value));
  });
  const type = document.querySelector("input[name='type']:checked");
  check_type(type.value ?? "");
});
""")

    @cached_property
    def all_dis_types(self):
        """Valid type of change values parsed from the Drug schema."""
        return sorted(getSchemaEnumVals("Drug.xml", "DISChangeType"))

    @cached_property
    def cdr_ids(self):
        """IDs entered by the user."""
        return self.fields.getvalue("cdr-id", "").strip()

    @cached_property
    def change_type_tables(self):
        """Report each type of change in its own table."""

        tables = []
        title = "Type of Change Report"
        range = self.date_range
        for change_type in self.change_types:
            rows = []
            for dis in self.documents:
                rows.extend(dis.get_rows(change_type))
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

        types = self.fields.getlist("change-type") or self.all_dis_types
        if set(types) - set(self.all_dis_types):
            self.bail()
        return sorted(types)

    @cached_property
    def columns(self):
        """Sequence of column definitions for the output report.

        Number and types of columns depend on config parms.
        """

        # We'll use this a lot.
        Column = self.Reporter.Column

        # Leftmost columns are always a doc title and ID.
        columns = [
            Column("CDR-ID", width="80px"),
            Column("Title", width="220px"),
        ]

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
                columns.append(Column("Type of Change", width="150px"))
            if self.comments:
                columns.append(Column("Comment", width="180px"))

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
        return f"{self.start} - {self.end}"

    @cached_property
    def debug(self):
        """True if we're running with increased logging."""
        return True if self.fields.getvalue("debug") else False

    @cached_property
    def documents(self):
        """PDQ Drug Info Summaries selected for the report.

        If the user chooses the "by drug info summary title" method for
        selecting which document to use for the report, and the
        fragment supplied matches more than one document, display the
        form a second time so the user can pick the correct document.
        """

        match self.selection_method:
            case "title":
                return [Summary(self, self.titles[0].id)]
            case "id":
                return [Summary(self, id) for id in self.cdr_ids]

    @cached_property
    def end(self):
        """End of date range for the historical version of the report."""
        return self.parse_date(self.fields.getvalue("end")) or self.today

    @cached_property
    def fragment(self):
        """Title fragment for selecting a DIS by title."""
        return self.fields.getvalue("title")

    @cached_property
    def loglevel(self):
        """Override to support debug logging."""
        return "DEBUG" if self.debug else self.LOGLEVEL

    @cached_property
    def organization(self):
        """Report organization (by drug info summary or by change types)."""

        organization = self.fields.getvalue("organization") or self.BY_SUMMARY
        if organization not in self.REPORT_ORGANIZATIONS:
            self.bail()
        return organization

    @cached_property
    def ready(self):
        """True if we have what we need for the report."""

        # If the request didn't come from the form, we can't be ready.
        if not self.request:
            return False

        # Make the determination based on the selection type chosen.
        match self.selection_method:
            case "id":
                if not self.cdr_ids:
                    message = "At least one CDR ID is required."
                    self.alerts.append(dict(message=message, type="error"))
                    return False
                ids = []
                for id in self.cdr_ids.split():
                    try:
                        id = Doc.extract_id(id)
                    except Exception:
                        self.logger.exception(id)
                        message = f"{id} is not a well-formed CDR ID."
                        self.alerts.append(dict(message=message, type="error"))
                        continue
                    try:
                        doc = Doc(self.session, id=id)
                        doctype = doc.doctype.name
                        if doctype != "DrugInformationSummary":
                            message = f"CDR{id} is a {doctype} document."
                            alert = dict(message=message, type="error")
                            self.alerts.append(alert)
                        else:
                            ids.append(id)
                    except Exception:
                        message = f"Document {id} not found."
                        self.logger.exception(message)
                        self.alerts.append(dict(message=message, type="error"))
                if self.alerts:
                    return False
                self.cdr_ids = ids
                return True
            case "title":
                if not self.fragment:
                    message = "Title fragment is required."
                    self.alerts.append(dict(message=message, type="error"))
                elif not self.titles:
                    message = f"No DIS documents match {self.fragment!r}."
                    self.alerts.append(dict(message=message, type="warning"))
                elif len(self.titles) > 1:
                    message = f"Multiple matches for {self.fragment!r}."
                    self.alerts.append(dict(message=message, type="info"))
                return True if not self.alerts else False
            case _:
                self.bail()

    @cached_property
    def start(self):
        """Start of date range for the historical version of the report."""
        return self.parse_date(self.fields.getvalue("start", URDATE))

    @cached_property
    def same_window(self):
        """By default, only one new browser tab."""
        return [self.SUBMIT] if self.request else []

    @cached_property
    def tables(self):
        """Assemble the table(s) for the report.

        If we're ready to display the report, we have three options:
          1. a single table showing the latest changes in each
             category of change for each selected drug info summary
          2. an historical report with a single table showing
             all changes falling within the specified date range
             for all selected drug info summaries
          3. multiple tables, one for each type of change,
             showing all changes occurring withing the specified
             date range for all selected drug info summaries
        """

        tables = None
        if self.type == self.CURRENT:
            caption = "Type of Change Report (Most Recent Change)"
        elif self.organization == self.BY_SUMMARY:
            first = "Type of Change Report (All Changes by Drug Info Summary)"
            caption = first, self.date_range
        else:
            tables = self.change_type_tables
        if tables is None:
            opts = dict(caption=caption, columns=self.columns)
            rows = []
            for dis in sorted(self.documents):
                rows.extend(dis.get_rows())
            tables = [self.Reporter.Table(rows, **opts)]
        self.subtitle = f"DIS Type of Change Report ({self.today})"
        if self.type == self.HISTORICAL:
            self.subtitle += f" -- {self.date_range}"
        return tables

    @cached_property
    def titles(self):
        """Find the DIS docs that match the user's title fragment.

        Note that the user is responsible for adding any non-trailing
        SQL wildcards to the fragment string. If the title is longer
        than 60 characters, truncate with an ellipsis, but add a
        tooltip showing the whole title. We create a local class for
        the resulting list.
        """

        if self.selection_method != "title" or not self.fragment:
            return None

        class DISTitle:
            def __init__(self, doc_id, display, tooltip=None):
                self.id = doc_id
                self.display = display
                self.tooltip = tooltip

        query = self.Query("active_doc d", "d.id", "d.title")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'DrugInformationSummary'")
        query.where(query.Condition("d.title", f"{self.fragment}%", "LIKE"))
        query.order("d.title")
        rows = query.execute(self.cursor).fetchall()
        titles = []
        for doc_id, title in rows:
            if len(title) > 60:
                short_title = title[:57] + "..."
                dis = DISTitle(doc_id, short_title, title)
            else:
                dis = DISTitle(doc_id, title)
            titles.append(dis)
        return titles

    @cached_property
    def today(self):
        """Today's date object, used in several places."""
        return date.today()

    @cached_property
    def type(self):
        """Type of report (current or historical)."""

        report_type = self.fields.getvalue("type") or self.CURRENT
        if report_type not in self.REPORT_TYPES:
            self.bail()
        return report_type


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
        href = f"QcReport.py?DocId={self.id}"
        row = [
            self.control.Reporter.Cell(self.id, href=href, rowspan=nrows),
            self.control.Reporter.Cell(self.display_title, rowspan=nrows),
            changes[0].date,
        ]
        if not change_type:
            row.append(changes[0].type)
        if self.control.comments:
            row.append(" / ".join(changes[0].comments))
        rows = [tuple(row)]
        for change in changes[1:]:
            row = [change.date]
            if not change_type:
                row.append(change.type)
            if self.control.comments:
                row.append(" / ".join(change.comments))
            rows.append(tuple(row))
        return rows

    @property
    def cdr_id_link(self):
        return f"{self.id:d}"

    @cached_property
    def doc(self):
        """`Doc` object for the summary's CDR document."""
        return Doc(self.control.session, id=self.id)

    @cached_property
    def changes(self):
        """Record of modifications made throughout the life of the summary."""

        changes = []
        for node in self.doc.root.findall("TypeOfDISChange"):
            change = self.Change(self.control, node)
            self.control.logger.debug("CDR%d %s", self.id, change)
            changes.append(change)
        return sorted(changes)

    @cached_property
    def display_title(self):
        return f"{self.title}"

    @cached_property
    def key(self):
        """Control how the summaries are sorted."""
        return self.title.lower(), self.id

    @cached_property
    def title(self):
        """Official title of the PDQ summary."""

        title = Doc.get_text(self.doc.root.find("Title"))
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
        """Pack all of the change types into a single report table row."""

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
        row = [self.cdr_id_link, self.display_title]
        nchanges = 0
        for change_type in self.control.change_types:
            change = change_types.get(change_type)
            if change:
                nchanges += 1
            row.append(change and change.date or "")
            if self.control.comments:
                row.append(change and " / ".join(change.comments) or "")
        if nchanges > 0:
            return [tuple(row)]
        return []

    class Change:
        """
        Information about a change event for a DIS document.

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
                if child.tag == "TypeOfDISChangeValue":
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
            """Create a debugging string for the change."""
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
