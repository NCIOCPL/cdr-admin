#----------------------------------------------------------------------
# Report on the types of changes recorded in selected Summaries.
#
# BZIssue::None  (JIRA::OCECDR-3703)
# OCECDR-3900: Modify the Summaries Type of Change report to display
#              Spanish CAM summaries
#
#                                           Alan Meyer, March 2014
#
# JIRA::OCECDR-4217 - modify user interface for report
# JIRA::OCECDR-4256 - fix date range filter bug
#----------------------------------------------------------------------
import datetime
import lxml.etree as etree
import cdr
import cdrcgi
import cdrdb

class Control(cdrcgi.Control):
    """
    Logic manager for report.
    """

    INCLUDE = "include"
    EXCLUDE = "exclude"
    COMMENTS = (INCLUDE, EXCLUDE)
    CURRENT = "Current (most recent changes for each category of change)"
    HISTORICAL = "Historical (all changes for a given date range)"
    REPORT_TYPES = (CURRENT, HISTORICAL)
    BY_SUMMARY = "One table for all summaries and changes"
    BY_CHANGE_TYPE = "One table for each type of change"
    REPORT_ORGANIZATIONS = (BY_SUMMARY, BY_CHANGE_TYPE)

    def __init__(self):
        """
        Collect and validate the report's request parameters.
        """

        cdrcgi.Control.__init__(self, "Summaries Type of Change")
        self.debug = self.fields.getvalue("debug") and True or False
        if self.debug:
            self.logger.level = cdr.Logging.LEVELS["debug"]
        self.today = str(datetime.date.today())
        self.boards = self.get_boards()
        self.all_types = self.get_change_types()
        self.change_types = self.fields.getlist("change-type") or self.all_types
        self.change_types = sorted(self.change_types)
        self.report_type = self.fields.getvalue("report-type") or self.CURRENT
        self.report_org = self.fields.getvalue("report-org") or self.BY_SUMMARY
        self.comments = self.fields.getvalue("comments") != self.EXCLUDE
        self.start = self.fields.getvalue("start") or cdr.URDATE
        self.end = self.fields.getvalue("end") or self.today
        self.selection_method = self.fields.getvalue("method", "board")
        self.audience = self.fields.getvalue("audience", "Health Professional")
        self.language = self.fields.getvalue("language", "English")
        self.board = self.fields.getlist("board") or ["all"]
        self.cdr_ids = self.fields.getvalue("cdr-id") or ""
        self.fragment = self.fields.getvalue("title")
        self.validate()

    def populate_form(self, form, titles=None):
        """
        Put the fields on the form.

        Pass:
            form - cdrcgi.Page object
            titles - if not None, show the followup page for selecting
                     from multiple matches with the user's title fragment;
                     otherwise, show the report's main request form
        """

        form.add_hidden_field("debug", self.debug)
        fieldset = '<fieldset class="history">'
        opts = { "titles": titles, "id-label": "CDR ID(s)" }
        opts["id-tip"] = "separate multiple IDs with spaces"
        self.add_summary_selection_fields(form, **opts)
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Types of Change"))
        for ct in self.all_types:
            checked = ct in self.change_types
            form.add_checkbox("change-type", ct, ct, checked=checked)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Comment Display"))
        for value in self.COMMENTS:
            label = "%s Comments" % value.capitalize()
            if self.comments:
                checked = value == self.INCLUDE
            else:
                checked = value == self.EXCLUDE
            form.add_radio("comments", label, value, checked=checked)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Type of Report"))
        for value in self.REPORT_TYPES:
            checked = value == self.report_type
            form.add_radio("report-type", value, value, checked=checked)
        form.add("</fieldset>")
        form.add(fieldset)
        form.add(form.B.LEGEND("Date Range for Changes History"))
        form.add_date_field("start", "Start Date", value=self.start)
        form.add_date_field("end", "End Date", value=self.end)
        form.add("</fieldset>")
        form.add(fieldset)
        form.add(form.B.LEGEND("Report Organization"))
        for org in self.REPORT_ORGANIZATIONS:
            checked = org == self.report_org
            form.add_radio("report-org", org, org, checked=checked)
        form.add("</fieldset>")
        form.add_output_options(default=self.format)
        script = self.toggle_display("check_report_type", self.HISTORICAL,
                                     "history")
        form.add_script(script)
        form.add_script("""\
jQuery(function() {
    check_report_type(jQuery("input[name='report-type']:checked").val());
});""")
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
            if not titles:
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
                form = cdrcgi.Page(self.PAGE_TITLE, **opts)
                self.populate_form(form, titles)
                form.send()
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
        today = datetime.datetime.today()
        subtitle = today.strftime("Report produced: %A %B %d, %Y %I:%M %p")
        subtitle = "Report produced %s" % str(datetime.datetime.now())[:19]
        subtitle = "Report produced %s" % datetime.date.today()
        opts["subtitle"] = subtitle
        if self.report_type == self.HISTORICAL:
            opts["subtitle"] += " -- %s" % self.format_date_range()
        report_type = self.report_type.split()[0]
        opts["banner"] = "Summary Type of Change Report - %s" % report_type
        return opts

    def summaries_for_boards(self):
        """
        The user has asked for a report of multiple summaries for
        one or more of the boards. Find the boards' summaries whose
        language match the request parameters, and return a list of
        Summary objects for them.
        """

        b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        t_path = "/Summary/TranslationOf/@cdr:ref"
        query = cdrdb.Query("active_doc d", "d.id")
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

    def get_change_types(self):
        """
        Parse the summary schema to get the valid values for type of change.
        """

        schema_doc, element_tag = "SummarySchema.xml", "SummaryChangeType"
        return sorted (cdr.getSchemaEnumVals(schema_doc, element_tag))

    def validate(self):
        """
        Separate validation method, to make sure the CGI request's
        parameters haven't been tampered with by an intruder.
        """

        msg = cdrcgi.TAMPERING
        if self.audience not in self.AUDIENCES:
            cdrcgi.bail(msg)
        if self.language not in self.LANGUAGES:
            cdrcgi.bail(msg)
        if self.selection_method not in self.SUMMARY_SELECTION_METHODS:
            cdrcgi.bail(msg)
        if self.format not in self.FORMATS:
            cdrcgi.bail(msg)
        boards = []
        for board in self.board:
            if board == "all":
                boards.append("all")
            else:
                try:
                    board = int(board)
                except:
                    cdrcgi.bail(msg)
                if board not in self.boards:
                    cdrcgi.bail(msg)
                boards.append(board)
        self.board = boards
        cdr_ids = set()
        for word in self.cdr_ids.strip().split():
            try:
                cdr_ids.add(cdr.exNormalize(word)[1])
            except:
                cdrcgi.bail("Invalid format for CDR ID")
        self.cdr_ids = cdr_ids
        cdrcgi.valParmDate(self.start, msg=msg)
        cdrcgi.valParmDate(self.end, msg=msg)
        valid_value_checks = (
            (self.change_types, self.all_types),
            (self.report_type, self.REPORT_TYPES),
            (self.report_org, self.REPORT_ORGANIZATIONS)
        )
        for user_values, valid_values in valid_value_checks:
            cdrcgi.valParmVal(user_values, valList=valid_values, msg=msg)

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
        query = cdrdb.Query("document", "xml", "title")
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
            rows[0].append(u" / ".join(changes[0].comments))
        for change in changes[1:]:
            row = [change.date]
            if not change_type:
                row.append(change.type)
            if self.control.comments:
                row.append(u" / ".join(change.comments))
            rows.append(row)
        return rows
    def format_title(self):
        return u"%s (%d)" % (self.title, self.doc_id)
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
                row.append(change and u" / ".join(change.comments) or "")
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

        def __cmp__(self, other):
            """
            Support sorting of the change events.

            Change request 2017-01-27 to reverse the date sort.
            """

            diff = cmp(other.date, self.date)
            if diff:
                return diff
            return cmp(self.type, other.type)

    def __cmp__(self, other):
        """
        Support sorting the summaries by title.
        """

        return cmp(self.key, other.key)

Control().run()
