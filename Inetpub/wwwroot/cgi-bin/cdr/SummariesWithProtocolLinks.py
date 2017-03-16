#----------------------------------------------------------------------
#
# Report on lists of summaries.
#
# BZIssue::4744 - Modify Summaries with Protocol Links/Refs report
# BZIssue::4865 - Summaries with Protocol Links/Refs report bug
# BZIssue::5120 - Missing Text from protocol ref report
# JIRA::OCECDR-4063 - make generation of board picklist dynamic
#
#----------------------------------------------------------------------
import datetime
import lxml.etree as etree
import cdr
import cdrcgi
import cdrdb

class Control(cdrcgi.Control):
    """
    Override class to generate specific report.
    """

    REPORT_NAME = "Summaries with Protocol Links/Refs Report"
    LANGUAGES = ("English", "Spanish")
    BOARD_NAME = "/Organization/OrganizationNameInformation/OfficialName/Name"
    STATUS_PATHS = (
        "/CTGovProtocol/OverallStatus",
        "/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus"
    )
    STATUS_PATH_TEST = " OR ".join(["path = '%s'" % s for s in STATUS_PATHS])
    METHODS = ("id", "title", "board")
    DATE_METHODS = ("include", "exclude")

    def __init__(self):
        """
        Collect and validate the form's parameters.
        """

        cdrcgi.Control.__init__(self, self.REPORT_NAME)
        self.boards = self.get_boards()
        self.statuses = self.get_statuses()
        self.selection_method = self.fields.getvalue("method", "board")
        self.language = self.fields.getvalue("language", "English")
        self.board = self.fields.getlist("board") or ["all"]
        self.cdr_id = self.fields.getvalue("cdr-id")
        self.fragment = self.fields.getvalue("title")
        self.start = self.fields.getvalue("start") or ""
        self.end = self.fields.getvalue("end") or ""
        self.date_method = self.fields.getvalue("date-method")
        self.status = self.fields.getlist("status") or ["all"]
        self.changed_only = self.fields.getvalue("changed-only") == "yes"
        self.format = self.fields.getvalue("format", "html")
        self.validate()

    def populate_form(self, form, titles=None):
        """
        Overridden version of the method to fill in the fields for
        the CGI request's form. In addition to being invoked by the
        base class's run() method when the page is first requested,
        this method is invoked by our build_tables() method below,
        when the user has selected the "by summary title" method
        of choosing a summary, with a title fragment which matches
        more than one summary, so that we can put the form up again,
        letting the user pick which of the matching summaries should
        be used for the report.
        """

        self.add_summary_selection_fields(form, titles=titles, audience=False)
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Filtering By Link Review Date"))
        for value in self.DATE_METHODS:
            capped = value.capitalize()
            label = "%s all links reviewed in specified date range." % value
            checked = self.date_method == value
            form.add_radio("date-method", label, value, checked=checked)
        form.add("</fieldset>")
        form.add("<fieldset id='date-range'>")
        form.add(form.B.LEGEND("Date Range for Filtering"))
        form.add_date_field("start", "Starting Date", value=self.start)
        form.add_date_field("end", "Ending Date", value=self.end)
        form.add("</fieldset>")
        form.add("<fieldset id='status-set'>")
        form.add(form.B.LEGEND("Trial Status Selection"))
        checked = "all" in self.status
        form.add_checkbox("status", "Any status value", "all", checked=checked)
        for status in sorted(self.statuses):
            checked = status in self.status
            form.add_checkbox("status", status, status, widget_classes="ind",
                              checked=checked)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Include Only Trials With Changed Statuses"))
        value_string = self.changed_only and "yes" or "no"
        for value in ("yes", "no"):
            label = value.capitalize()
            checked = value == value_string
            form.add_radio("changed-only", label, value, checked=checked)
        form.add("</fieldset>")
        form.add_output_options(default=self.format)
        form.add_script(self.get_script())

    def build_tables(self):
        """
        Overrides the base class's version of this method to assemble
        the tables to be displayed for this report. If the user
        chooses the "by summary title" method for selecting which
        summary to use for the report, and the fragment supplied
        matches more than one summary document, display the form
        a second time so the user can pick the summary.
        """

        if self.selection_method == "title":
            if not self.fragment:
                cdrcgi.bail("Title fragment is required.")
            titles = self.summaries_for_title(self.fragment)
            if not titles:
                cdrcgi.bail("No summaries match that title fragment")
            if len(titles) == 1:
                summaries = [Summary(titles[0].id, self)]
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
            if not self.cdr_id:
                cdrcgi.bail("CDR ID is required.")
            summaries = [Summary(self.cdr_id, self)]
        else:
            if not self.board:
                cdrcgi.bail("At least one board is required.")
            summaries = self.summaries_for_boards()

        # We have the summaries; build the report table.
        title = "Summaries With Protocol Links/Refs Report"
        cols = self.get_cols()
        rows = self.get_rows(summaries)
        return [cdrcgi.Report.Table(cols, rows, caption=title)]

    def set_report_options(self, opts):
        """
        Callback to adjust the report's options:
           * Plug in the title we created above in build_tables().
           * Add subtitle showing the date the report is run.
           * Override CSS for links.
        """

        return {
            "banner": self.title,
            "subtitle": str(datetime.date.today()),
            "css": "a { color: red; text-decoration: none; }"
        }

    def get_cols(self):
        "Specify the column headers, with width for each."
        return (
            cdrcgi.Report.Column("CDR ID", width="50px"),
            cdrcgi.Report.Column("Summary Title", width="125px"),
            cdrcgi.Report.Column("Summary Sec Title", width="125px"),
            cdrcgi.Report.Column("Protocol Link/Ref", width="400px"),
            cdrcgi.Report.Column("CDR ID", width="50px"),
            cdrcgi.Report.Column("Current Protocol Status", width="80px"),
            cdrcgi.Report.Column("Comment", width="125px"),
            cdrcgi.Report.Column("Last Reviewed Date", width="80px"),
            cdrcgi.Report.Column("Last Reviewed Status", width="80px")
        )

    def get_rows(self, summaries):
        "Create rows for all the in-scope links in all the summaries."
        rows = []
        for summary in summaries:
            rows += [link.make_row() for link in summary.links]
        return rows

    def get_statuses(self):
        "Get the unique protocol status values."
        query = cdrdb.Query("query_term", "value")
        query.where("(%s)" % self.STATUS_PATH_TEST)
        rows = query.unique().execute(self.cursor).fetchall()
        return set([row[0] for row in rows if row[0] and row[0]])

    def get_boards(self):
        """
        Assemble a dictionary of the PDQ board names, indexed by
        CDR Organization document ID. Trim the names to their
        short forms, pruning away the "PDQ" prefix and the
        "Editorial Board" suffix.
        """

        query = cdrdb.Query("query_term n", "n.doc_id", "n.value")
        query.join("query_term t", "t.doc_id = n.doc_id")
        query.join("active_doc a", "a.id = n.doc_id")
        query.where("t.path = '/Organization/OrganizationType'")
        query.where("n.path = '%s'" % self.BOARD_NAME)
        query.where("t.value = 'PDQ Editorial Board'")
        rows = query.execute(self.cursor).fetchall()
        boards = {}
        prefix, suffix = "PDQ ", " Editorial Board"
        for org_id, name in rows:
            if name.startswith(prefix):
                name = name[len(prefix):]
            if name.endswith(suffix):
                name = name[:-len(suffix)]
            boards[org_id] = name
        return boards

    def summaries_for_title(self, fragment):
        """
        Find the summaries that match the user's title fragment. Note
        that the user is responsible for adding any non-trailing SQL
        wildcards to the fragment string. If the title is longer than
        60 characters, truncate with an ellipsis, but add a tooltip
        showing the whole title. We create a local class for the
        resulting list.
        """

        class SummaryTitle:
            def __init__(self, doc_id, display, tooltip=None):
                self.id = doc_id
                self.display = display
                self.tooltip = tooltip

        query = cdrdb.Query("document d", "d.id", "d.title")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'Summary'")
        query.where(query.Condition("d.title", fragment + "%", "LIKE"))
        query.order("d.title")
        rows = query.execute(self.cursor).fetchall()
        summaries = []
        for doc_id, title in rows:
            if len(title) > 60:
                short_title = title[:57] + "..."
                summary = SummaryTitle(doc_id, short_title, title)
            else:
                summary = SummaryTitle(doc_id, title)
            summaries.append(summary)
        return summaries

    def summaries_for_boards(self):
        """
        The user has asked for a report of multiple summaries for
        one or more of the boards. Find the boards' summaries whose
        language match the request parameters, and contain links to
        protocol documents with the requested statuses, and return
        a list of Summary objects for them.
        """

        b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        t_path = "/Summary/TranslationOf/@cdr:ref"
        query = cdrdb.Query("query_term p", "p.doc_id")
        query.where("p.path LIKE '/Summary/%ProtocolRef/@cdr:href'")
        query.join("active_doc d", "d.id = p.doc_id")
        query.join("doc_version v", "v.id = d.id")
        query.where("v.publishable = 'Y'")
        query.join("query_term l", "l.doc_id = p.doc_id")
        query.where("l.path = '/Summary/SummaryMetaData/SummaryLanguage'")
        query.where(query.Condition("l.value", self.language))
        if "all" not in self.board:
            if self.language == "English":
                query.join("query_term b", "b.doc_id = p.doc_id")
            else:
                query.join("query_term t", "t.doc_id = p.doc_id")
                query.where(query.Condition("t.path", t_path))
                query.join("query_term b", "b.doc_id = t.int_val")
            query.where(query.Condition("b.path", b_path))
            query.where(query.Condition("b.int_val", self.board, "IN"))
        if "all" not in self.status:
            query.join("query_term s", "s.doc_id = p.int_val")
            query.where(query.Condition("s.value", self.status, "IN"))
        rows = query.unique().execute(self.cursor).fetchall()
        return sorted([Summary(row[0], self) for row in rows])

    def validate(self):
        """
        Separate validation method, to make sure the CGI request's
        parameters haven't been tampered with by an intruder.
        """

        msg = cdrcgi.TAMPERING
        if self.language not in self.LANGUAGES:
            cdrcgi.bail(msg)
        if self.selection_method not in self.METHODS:
            cdrcgi.bail(msg)
        if self.date_method and self.date_method not in self.DATE_METHODS:
            cdrcgi.bail(msg)
        if self.format not in self.FORMATS:
            cdrcgi.bail(msg)
        for status in self.status:
            if status != "all" and status not in self.statuses:
                cdrcgi.bail(msg)
        cdrcgi.valParmDate(self.start, empty_ok=True, msg=msg)
        cdrcgi.valParmDate(self.end, empty_ok=True, msg=msg)
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
        if self.cdr_id:
            try:
                self.cdr_id = cdr.exNormalize(self.cdr_id)[1]
            except:
                cdrcgi.bail("Invalid format for CDR ID")

    def get_script(self):
        """
        Show the date range fields when a date filtering method is
        selected. Dynamically adjusted the status checkboxes when
        one is clicked. Builds on Javascript inserted by the call
        to the add_summary_selection_fields() method above (see
        cdrcgi.py).
        """
        return """\
function check_date_method(whatever) { jQuery("#date-range").show() }
function check_status(status) { check_set("status", status); }
jQuery(function() {
    if (jQuery("input[name='date-method']:checked").val())
        jQuery("#date-range").show();
    else
        jQuery("#date-range").hide();
});"""

class Summary:
    """
    One of these for each summary on the report. All of its protocol
    links which are in scope for this report are collected in a central
    place, no matter how deeply nested in subsections they may be.
    """

    protocols = {}
    "Cache for protocol info (e.g., PMID, status)."

    FILTER = "name:Revision Markup Filter"
    "We need to resolve Insertion and Deletion elements."

    def __init__(self, doc_id, control):
        """
        Fetch the summary's document title and all of the protocol links
        which match the user's criteria.
        """

        self.id = doc_id
        self.control = control
        self.links = []
        xml, errors = cdr.filterDoc(control.session, [self.FILTER],
                                    docId=doc_id)
        if not xml:
            cdrcgi.bail("filter %s: %s" % (doc_id, errors))
        root = etree.XML(xml)
        for node in root.findall("SummaryTitle"):
            self.title = node.text
        nodes = root.findall("SummarySection")
        self.sections = [Summary.Section(node, self) for node in nodes]

    def __cmp__(self, other):
        "Make the Summary list sortable"
        return cmp(self.title, other.title)

    @classmethod
    def Protocol(cls, link):
        """
        Looks like a constructor to the caller, but it's actually
        a factory method so we can avoid looking up the information
        for the same protocol document twice.
        """

        if link.href not in cls.protocols:
            try:
                cls.protocols[link.href] = cls._Protocol(link)
            except Exception, e:
                cls.protocols[link.href] = None
        return cls.protocols[link.href]

    class _Protocol:
        "Target of a link for the report."

        def __init__(self, link):
            "Save the document ID and find the protocol's current status."
            self.cdr_id = link.href
            self.id = cdr.exNormalize(self.cdr_id)[1]
            query = cdrdb.Query("query_term", "value")
            query.where("(%s)" % link.control.STATUS_PATH_TEST)
            query.where(query.Condition("doc_id", self.id))
            rows = query.execute(link.control.cursor).fetchall()
            self.status = rows and rows[0][0] or None

    @staticmethod
    def get_text(node):
        "Recursively assemble the text content from a node."
        chunks = []
        if node.text is not None:
            chunks.append(node.text)
        for child in node:
            chunks.append(Summary.get_text(child))
        if node.tail is not None:
            chunks.append(node.tail)
        return u"".join(chunks)

    class Section:
        "Section (possibly nested in a summary)."

        def __init__(self, node, summary):
            "Capture the title and find the protocol links and subsections."
            self.summary = summary
            self.control = summary.control
            self.title = None
            self.subsections = []
            for child in node:
                if child.tag == "Title":
                    self.title = Summary.get_text(child)
                elif child.tag == "SummarySection":
                    self.subsections.append(Summary.Section(child, summary))
                else:
                    for link_node in child.iter("ProtocolRef"):
                        link = Summary.Section.Link(link_node, self)
                        if link.in_scope():
                            summary.links.append(link)

        class Link:
            "Represents a link from a summary to a protocol document."

            def __init__(self, node, section):
                """
                Collect the setting for the link, as well as the text
                in which it was found.
                """

                self.node = node
                self.section = section
                self.control = section.control
                self.href = node.get("{cips.nci.nih.gov/cdr}href")
                self.comment = node.get("comment")
                self.reviewed = node.get("LastReviewedDate")
                self.status = node.get("LastReviewedStatus")
                self.protocol = Summary.Protocol(self)
                self.prefix_text = []
                self.suffix_text = []
                self.link_text = None
                self.get_text(node.getparent())

            def in_scope(self):
                "See if this link should be included on the report."
                if self.control.date_method == "include":
                    if not self.in_date_range():
                        return False
                elif self.control.date_method == "exclude":
                    if self.in_date_range():
                        return False
                if self.control.changed_only:
                    if self.status == self.protocol.status:
                        return False
                if self.control.status and "all" not in self.control.status:
                    if self.protocol.status not in self.control.status:
                        return False
                return True

            def in_date_range(self):
                """
                Determine whether the latest review of this link happened
                within the range of dates specified by the user. If an
                endpoing (either start of end) is missing, don't test
                for it.
                """

                if not self.reviewed:
                    return False
                if self.control.start:
                    if self.reviewed < self.control.start:
                        return False
                if self.control.end:
                    if self.reviewed > self.control.end:
                        return False
                return True

            def get_text(self, node):
                "Recursively collect the text in which the link was found."
                self.add_text(node.text)
                for child in node:
                    if child is self.node:
                        if child.text is None or not child.text.strip():
                            self.link_text = "Protocol Ref"
                        else:
                            self.link_text = child.text
                        self.add_text(child.tail)
                    else:
                        self.get_text(child)
                self.add_text(node.tail)

            def add_text(self, text):
                "Add a chunk of text to the appropriate sequence."
                if text is not None and text:
                    if self.link_text is None:
                        self.prefix_text.append(text)
                    else:
                        self.suffix_text.append(text)

            def to_td(self, cell, format):
                """
                Create a custom table cell with a link to the Procotol
                QC report for this REF. If we have no protocol, let
                the base class method show the text without the link.
                """

                if not self.protocol:
                    return None
                url = "QcReport.py?DocId=%s&%s=%s" % (self.protocol.cdr_id,
                                                      cdrcgi.SESSION,
                                                      self.control.session)
                a = cdrcgi.Page.B.A(self.link_text, target="_blank", href=url)
                a.tail = self.suffix
                td = cdrcgi.Page.B.TD(self.prefix, a)
                #td.append(a)
                return td

            def make_row(self):
                "Assemble the report table row for this protocol link."
                self.prefix = u"".join(self.prefix_text)
                self.suffix = u"".join(self.suffix_text)
                if len(self.prefix) > 200:
                    self.prefix = u"... %s" % self.prefix[-200:]
                if len(self.suffix) > 200:
                    self.suffix = u"%s ..." % self.suffix[:200]
                text = u"".join([self.prefix, self.link_text, self.suffix])
                return [
                    self.section.summary.id or "---",
                    self.section.summary.title or "---",
                    self.section.title or "",
                    cdrcgi.Report.Cell(text, callback=self.to_td),
                    self.protocol and self.protocol.id or "---",
                    self.protocol and self.protocol.status or "---",
                    self.comment or "",
                    self.reviewed or "",
                    self.status or ""
                ]

#----------------------------------------------------------------------
# Instantiate our custom Control class and invoke the base class's
# run method. Wrap this in a test which lets us parse the script
# without performing any actual processing.
#----------------------------------------------------------------------
if __name__ == "__main__":
    Control().run()
