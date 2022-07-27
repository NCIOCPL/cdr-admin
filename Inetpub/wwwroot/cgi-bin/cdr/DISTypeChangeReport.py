#!/usr/bin/env python

"""
    Report on the types of changes recorded in selected Drug Info Summaries.

    (adapted from SummaryTypeChangeReport.py written by BK)
"""

from datetime import date
from cdrapi.docs import Doc
from cdrcgi import Controller
from cdr import URDATE, getSchemaEnumVals


class Control(Controller):
    """
    Logic manager for report.
    """

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
        "'DIS CDR IDs for Type of Change Report' on the following page: ",
        "CDR Stored Database Queries",
        "/cgi-bin/cdr/CdrQueries.py",
        "Copy and paste the complete set of CDR IDs into the CDR ID field."
    )

    def build_tables(self):
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
            for dis in sorted(self.dis_docs):
                rows.extend(dis.get_rows())

            table_rows = []
            for row in rows:
                cells = [
                    self.Reporter.Cell(row[0],
                                       href=f"QcReport.py?DocId={row[0]}")
                ]
                cells += row[1:]
                table_rows.append(cells)

            tables = [self.Reporter.Table(table_rows, **opts)]
        self.subtitle = f"Report produced {self.today}"
        if self.type == self.HISTORICAL:
            self.subtitle += f" -- {self.date_range}"
        return tables

    def show_report(self):
        """Overriding this method allows us to add CSS to the report

           Overriding is not necessary if the standard report formatting
           is working for the clients. In that case remove this method.
        """

        elapsed = self.report.page.html.get_element_by_id("elapsed", None)
        if elapsed is not None:
            elapsed.text = str(self.elapsed)
        self.report.page.add_css("th { background-color: lightgrey; }")
        self.report.send(self.format)

    def populate_form(self, page, titles=None):
        """Put the fields on the form.

        Pass:
            page - `cdrcgi.HTMLPage` object
            titles - if not None, show the followup page for selecting
                     from multiple matches with the user's title fragment;
                     otherwise, show the report's main request form
        """

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS[0],
                        page.B.BR(),
                        page.B.A(self.INSTRUCTIONS[1],
                                 href=self.INSTRUCTIONS[2]),
                        page.B.BR(), self.INSTRUCTIONS[3]))
        page.form.append(fieldset)

        page.form.append(page.hidden_field("debug", self.debug or ""))
        opts = {"titles": titles, "id-label": "CDR ID(s)"}
        opts["id-tip"] = "separate multiple IDs with spaces"
        self.add_dis_selection_fields(page, **opts)

        fieldset = page.fieldset("Types of Change")
        for ct in self.all_dis_types:
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
        fieldset.set("class", "history")
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

        page.add_output_options(default=self.format)
        args = "check_type", self.HISTORICAL, "history"
        page.add_script(self.toggle_display(*args))
        page.add_script("""\
$(function() {
    check_type($("input[name='type']:checked").val());
});""")

    def add_dis_selection_fields(self, page, **kwopts):
        """
        Display the fields used to specify which DIS should be
        selected for a report, using one of several methods:

            * by DIS document ID
            * by DIS title

        There are two branches taken by this method. If the user has
        elected to select a drug info summary by title, and the DIS
        title fragment matches more than one document, then a follow-up
        page is presented on which the user selects one of the documents
        and re-submits the report request. Otherwise, the user is shown
        options for choosing a selection method, which in turn displays
        the fields appropriate to that method dynamically. We also add
        JavaScript functions to handle the dynamic control of field display.

        Pass:
            page     - Page object on which to show the fields
            titles   - an optional array of DISTitle objects
            id-label - optional string for the CDR ID field (defaults
                       to "CDR ID" but can be overridden, for example,
                       to say "CDR ID(s)" if multiple IDs are accepted)
            id-tip   - optional string for the CDR ID field for popup
                       help (e.g., "separate multiple IDs by spaces")

        Return:
            nothing (the form object is populated as a side effect)
        """

        # --------------------------------------------------------------
        # Show the second stage in a cascading sequence of the form if we
        # have invoked this method directly from build_tables(). Widen
        # the form to accomodate the length of the title substrings
        # we're showing.
        # --------------------------------------------------------------
        titles = kwopts.get("titles")
        if titles:
            page.form.append(page.hidden_field("selection_method", "id"))
            fieldset = page.fieldset("Choose Drug Info Summary")
            page.add_css("fieldset { width: 600px; }")
            for t in titles:
                opts = dict(label=t.display, value=t.id, tooltip=t.tooltip)
                fieldset.append(page.radio_button("cdr-id", **opts))
            page.form.append(fieldset)
            self.new_tab_on_submit(page)

        else:
            # Fields for the original form.
            fieldset = page.fieldset("Selection Method")
            methods = "CDR ID", "Drug Info Summary Title"
            checked = False
            for method in methods:
                value = method.split()[-1].lower()
                opts = dict(label=f"By {method}", value=value, checked=checked)
                fieldset.append(page.radio_button("selection_method", **opts))
                checked = True
            page.form.append(fieldset)

            fieldset = page.fieldset("Drug Info Summary ID")
            fieldset.set("class", "by-id-block")
            label = kwopts.get("id-label", "CDR ID")
            opts = dict(label=label, tooltip=kwopts.get("id-tip"))
            fieldset.append(page.text_field("cdr-id", **opts))
            page.form.append(fieldset)

            fieldset = page.fieldset("Drug Info Summary Title")
            fieldset.set("class", "by-title-block")
            tooltip = "Use wildcard (%) as appropriate."
            fieldset.append(page.text_field("title", tooltip=tooltip))
            page.form.append(fieldset)
            page.add_script(self.summary_selection_js)

    @property
    def all_dis_types(self):
        """Valid type of change values parsed from the Drug schema."""

        if not hasattr(self, "_all_dis_types"):
            args = "Drug.xml", "DISChangeType"
            self._all_dis_types = sorted(getSchemaEnumVals(*args))
        return self._all_dis_types

    @property
    def cdr_ids(self):
        """Set of unique CDR ID integers."""

        if not hasattr(self, "_cdr_ids"):
            self._cdr_ids = set()
            for word in self.fields.getvalue("cdr-id", "").strip().split():
                try:
                    self._cdr_ids.add(Doc.extract_id(word))
                except Exception:
                    self.bail("Invalid format for CDR ID")
        return self._cdr_ids

    @property
    def change_type_tables(self):
        """Report each type of change in its own table."""

        if not hasattr(self, "_change_type_tables"):
            opts = {"html_callback_pre": Control.table_spacer}
            tables = []
            title = "Type of Change Report"
            range = self.date_range
            for change_type in self.change_types:
                rows = []
                for dis in self.dis_docs:
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

                table_rows = []
                for row in rows:
                    cells = [
                        self.Reporter.Cell(row[0],
                                           href=f"QcReport.py?DocId={row[0]}")
                    ]
                    cells += row[1:]
                    table_rows.append(cells)

                tables.append(self.Reporter.Table(table_rows, **opts))
            self._change_type_tables = tables
        return self._change_type_tables

    @property
    def change_types(self):
        """Types of change selected by the user."""

        if not hasattr(self, "_change_types"):
            types = self.fields.getlist("change-type") or self.all_dis_types
            if set(types) - set(self.all_dis_types):
                self.bail()
            self._change_types = sorted(types)
        return self._change_types

    @property
    def columns(self):
        """Sequence of column definitions for the output report.

        Number and types of columns depend on config parms.
        """

        if not hasattr(self, "_columns"):

            # We'll use this a lot.
            Column = self.Reporter.Column

            # Leftmost column is always a doc title and ID.
            self._columns = [Column("CDR-ID", width="80px"),
                             Column("Title", width="220px")]

            # Basic reports need cols for types of change and comments.
            if self.type == self.CURRENT:
                if self.comments:
                    comment_column = Column("Comment", width="150px")
                for change_type in sorted(self.change_types):
                    self._columns.append(Column(change_type, width="105px"))
                    if self.comments:
                        self._columns.append(comment_column)

            # Historical reports.
            else:
                self._columns.append(Column("Date", width="80px"))
                if self.organization == self.BY_SUMMARY:
                    col = Column("Type of Change", width="150px")
                    self._columns.append(col)
                if self.comments:
                    self._columns.append(Column("Comment", width="180px"))

        return self._columns

    @property
    def comments(self):
        """True if the report should include comments."""

        if not hasattr(self, "_comments"):
            comments = self.fields.getvalue("comments")
            self._comments = comments != self.EXCLUDE
        return self._comments

    @property
    def date_range(self):
        """String describing the date coverage for the report."""

        if not hasattr(self, "_date_range"):
            start_is_urdate = str(self.start) <= URDATE
            end_is_today = self.end >= self.today
            if start_is_urdate:
                if end_is_today:
                    self._date_range = "Complete History"
                else:
                    self._date_range = f"Through {self.end}"
            elif end_is_today:
                self._date_range = f"From {self.start}"
            else:
                self._date_range = f"{self.start} - {self.end}"
        return self._date_range

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
        """Title fragment for selecting a DIS by title."""

        if not hasattr(self, "_fragment"):
            self._fragment = self.fields.getvalue("title")
        return self._fragment

    @property
    def loglevel(self):
        """Override to support debug logging."""
        return "DEBUG" if self.debug else self.LOGLEVEL

    @property
    def organization(self):
        """Report organization (by drug info summary or by change types)."""

        if not hasattr(self, "_organization"):
            organization = self.fields.getvalue("organization")
            self._organization = organization or self.BY_SUMMARY
            if self._organization not in self.REPORT_ORGANIZATIONS:
                self.bail()
        return self._organization

    @property
    def start(self):
        """Start of date range for the historical version of the report."""

        if not hasattr(self, "_start"):
            start = self.fields.getvalue("start", URDATE)
            self._start = self.parse_date(start)
        return self._start

    @property
    def subtitle(self):
        """What we display under the main banner."""

        if not hasattr(self, "_subtitle"):
            self._subtitle = self.SUBTITLE
        return self._subtitle

    @subtitle.setter
    def subtitle(self, value):
        """Allow the report page to override the subtitle."""
        self._subtitle = value

    @property
    def dis_docs(self):
        """PDQ Drug Info Summaries selected for the report.

        If the user chooses the "by drug info summary title" method for
        selecting which document to use for the report, and the
        fragment supplied matches more than one document, display the
        form a second time so the user can pick the correct document.
        """

        if not hasattr(self, "_dis_docs"):
            if self.selection_method == "title":
                if not self.fragment:
                    self.bail("Title fragment is required.")
                titles = self.dis_titles
                if not titles:
                    self.bail("No DIS match that title fragment")
                if len(titles) == 1:
                    self._dis_docs = [Summary(self, titles[0].id)]
                else:
                    self.populate_form(self.form_page, titles)
                    self.form_page.send()
            elif self.selection_method == "id":
                if not self.cdr_ids:
                    self.bail("At least one CDR ID is required.")
                self._dis_docs = [Summary(self, id) for id in self.cdr_ids]
            else:
                self.bail("Invalid selection_method")
        return self._dis_docs

    @property
    def dis_titles(self):
        """Find the DIS docs that match the user's title fragment.

        Note that the user is responsible for adding any non-trailing
        SQL wildcards to the fragment string. If the title is longer
        than 60 characters, truncate with an ellipsis, but add a
        tooltip showing the whole title. We create a local class for
        the resulting list.

        ONLY WORKS IF YOU IMPLEMENT THE `self.fragment` PROPERTY!!!
        """

        if not hasattr(self, "_dis_titles"):
            self._dis_titles = None
            if hasattr(self, "fragment") and self.fragment:
                class DISTitle:
                    def __init__(self, doc_id, display, tooltip=None):
                        self.id = doc_id
                        self.display = display
                        self.tooltip = tooltip
                fragment = f"{self.fragment}%"
                query = self.Query("active_doc d", "d.id", "d.title")
                query.join("doc_type t", "t.id = d.doc_type")
                query.where("t.name = 'DrugInformationSummary'")
                query.where(query.Condition("d.title", fragment, "LIKE"))
                query.order("d.title")
                rows = query.execute(self.cursor).fetchall()
                self._dis_titles = []
                for doc_id, title in rows:
                    if len(title) > 60:
                        short_title = title[:57] + "..."
                        dis = DISTitle(doc_id, short_title, title)
                    else:
                        dis = DISTitle(doc_id, title)
                    self._dis_titles.append(dis)
        return self._dis_titles

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

    @staticmethod
    def table_spacer(table, page):
        """
        Put some space before the table.
        """

        page.add_css("table { margin-top: 25px; }")


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

        self.__control = control
        self.__doc_id = doc_id

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
            self.id,
            self.control.Reporter.Cell(self.display_title, rowspan=nrows),
            changes[0].date,
        ]
        if not change_type:
            row.append(changes[0].type)
        if self.control.comments:
            row.append(" / ".join(changes[0].comments))
        rows = [tuple(row)]
        for change in changes[1:]:
            # First element is the CDR-ID which is suppressed for all but the
            # first row.
            row = ["", change.date]
            if not change_type:
                row.append(change.type)
            if self.control.comments:
                row.append(" / ".join(change.comments))
            rows.append(tuple(row))
        return rows

    @property
    def control(self):
        """Access to the database and the report options."""
        return self.__control

    @property
    def doc(self):
        """`Doc` object for the summary's CDR document."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.control.session, id=self.id)
        return self._doc

    @property
    def changes(self):
        """Record of modifications made throughout the life of the summary."""

        if not hasattr(self, "_changes"):
            changes = []
            for node in self.doc.root.findall("TypeOfDISChange"):
                change = self.Change(self.control, node)
                self.control.logger.debug("CDR%d %s", self.id, change)
                changes.append(change)
            self._changes = sorted(changes)
        return self._changes

    @property
    def display_title(self):
        return f"{self.title}"

    @property
    def cdr_id_link(self):
        return f"{self.id:d}"

    @property
    def id(self):
        """Integer for the PDQ summary's unique CDR document ID."""
        return self.__doc_id

    @property
    def key(self):
        """Control how the summaries are sorted."""

        if not hasattr(self, "_key"):
            self._key = self.title.lower(), self.id
        return self._key

    @property
    def title(self):
        """Official title of the PDQ summary."""

        if not hasattr(self, "_title"):
            self._title = Doc.get_text(self.doc.root.find("Title"))
            if not self._title:
                self._title = self.doc.title.split(";")[0]
        return self._title

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
