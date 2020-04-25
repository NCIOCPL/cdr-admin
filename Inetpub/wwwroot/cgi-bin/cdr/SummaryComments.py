#!/usr/bin/env python

#----------------------------------------------------------------------
# Report listing summaries containing specified markup.
#
# BZIssue::4756 - Summary Comments Report
# BZIssue::4908 - Editing Summary Comments Report in MS Word
# BZIssue::4968 - Modification to Summaries Comments Report to
#                 Show/Hide Certain Comments
# BZIssue::5273 - Identifying Modules in Summary Reports
# JIRA::OCECDR-3893 - Fix board display
#----------------------------------------------------------------------
import cdr
import cdrcgi
import datetime
import lxml.etree as etree
from cdrapi import db

class Control(cdrcgi.Control):
    """
    Override class to generate specific report.
    """

    AUDIENCES = ("Health Professional", "Patient")
    LANGUAGES = ("English", "Spanish")
    RESPONSE = "ResponseToComment"
    BLANK = "blank"
    USER_AND_DATE = "user-and-date"
    BOARD_NAME = "/Organization/OrganizationNameInformation/OfficialName/Name"
    TYPES = {
        "C": "All Comments",
        "I": "Internal Comments (excluding permanent comments)",
        "P": "Permanent Comments (internal & external)",
        "E": "External Comments (excluding advisory comments)",
        "A": "Advisory Board Comments (internal & external)",
        "R": "Responses to Comments"
    }
    TYPE_KEYS = "CIPEAR"

    def __init__(self):
        """
        Collect and validate the form's parameters.
        """

        cdrcgi.Control.__init__(self, "Summary Comments Report")
        self.boards = self.get_boards()
        self.selection_method = self.fields.getvalue("method", "board")
        self.audience = self.fields.getvalue("audience", "Health Professional")
        self.language = self.fields.getvalue("language", "English")
        self.board = self.fields.getvalue("board")
        self.cdr_id = self.fields.getvalue("cdr-id")
        self.fragment = self.fields.getvalue("title")
        self.comment_types = set(self.fields.getlist("comments")) or set("ER")
        self.comment_tags = self.get_comment_tags()
        self.extra = self.fields.getlist("extra")
        self.widths = self.get_widths()
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

        #--------------------------------------------------------------
        # Show the second stage in a cascading sequence of the form if we
        # have invoked this method directly from build_tables(). Widen
        # the form to accomodate the length of the title substrings
        # we're showing.
        #--------------------------------------------------------------
        if titles:
            form.add_css("fieldset { width: 600px; }")
            form.add_hidden_field("method", "id")
            form.add("<fieldset>")
            form.add(form.B.LEGEND("Choose Summary"))
            for t in titles:
                form.add_radio("cdr-id", t.display, t.id, tooltip=t.tooltip)
            form.add("</fieldset>")
            self.new_tab_on_submit(form)
        else:
            if not self.extra:
                self.extra = ["blank"]
            form.add("<fieldset>")
            form.add(form.B.LEGEND("Selection Method"))
            form.add_radio("method", "By PDQ Board", "board", checked=True)
            form.add_radio("method", "By CDR ID", "id")
            form.add_radio("method", "By Summary Title", "title")
            form.add("</fieldset>")
            form.add("<fieldset class='by-board-block'>")
            form.add(form.B.LEGEND("Board"))
            for board_id in sorted(self.boards, key=self.boards.get):
                form.add_radio("board", self.boards.get(board_id), board_id)
            form.add("</fieldset>")
            form.add("<fieldset class='by-board-block'>")
            form.add(form.B.LEGEND("Audience"))
            form.add_radio("audience", "Health Professional",
                           "Health Professional", checked=True)
            form.add_radio("audience", "Patient", "Patient")
            form.add("</fieldset>")
            form.add("<fieldset class='by-board-block'>")
            form.add(form.B.LEGEND("Language"))
            form.add_radio("language", "English", "English", checked=True)
            form.add_radio("language", "Spanish", "Spanish")
            form.add("</fieldset>")
            form.add("<fieldset class='by-id-block'>")
            form.add(form.B.LEGEND("Summary Document ID"))
            form.add_text_field("cdr-id", "CDR ID")
            form.add("</fieldset>")
            form.add("<fieldset class='by-title-block'>")
            form.add(form.B.LEGEND("Summary Title"))
            form.add_text_field("title", "Title",
                                tooltip="Use wildcard (%) as appropriate.")
            form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Comment Types"))
        for key in self.TYPE_KEYS:
            widget_class = ""
            if key not in "CR":
                widget_class = "specific-comment-types"
            checked = key in self.comment_types
            form.add_checkbox("comments", self.TYPES[key], key,
                              checked=checked, widget_classes=[widget_class])
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Extra Columns"))
        for label, value in (
            ("User ID and Date", Control.USER_AND_DATE),
            ("Blank Column", Control.BLANK)
        ):
            checked = value in self.extra
            form.add_checkbox("extra", label, value, checked=checked)
        form.add("</fieldset>")

        #--------------------------------------------------------------
        # Dynamic management of sections of the form using local script.
        #--------------------------------------------------------------
        form.add_script("""\
function check_comments(type) {
    switch (type) {
        case 'C':
            jQuery('.specific-comment-types').prop('checked', false);
            break;
        case 'R':
            break;
        default:
            jQuery('#comments-c').prop('checked', false);
            break;
    }
}
function check_method(method) {
    switch (method) {
        case 'id':
            jQuery('.by-board-block').hide();
            jQuery('.by-id-block').show();
            jQuery('.by-title-block').hide();
            break;
        case 'board':
            jQuery('.by-board-block').show();
            jQuery('.by-id-block').hide();
            jQuery('.by-title-block').hide();
            break;
        case 'title':
            jQuery('.by-board-block').hide();
            jQuery('.by-id-block').hide();
            jQuery('.by-title-block').show();
            break;
    }
}
jQuery(function() {
    check_method(jQuery("input[name='method']:checked").val());
});""")

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
                cdrcgi.bail("Board is required.")
            summaries = self.summaries_for_board()

        #--------------------------------------------------------------
        # While we have the Summary objects available, prepare the
        # report title which we'll use in the set_report_options()
        # method below, depending on whether comments for a single
        # summary are being shown, or comments for all of the selected
        # board's active summaries.
        #--------------------------------------------------------------
        if len(summaries) > 1:
            board_name = self.boards.get(self.board)
            self.title = "Comments for %s %s %s Summaries" % (self.language,
                                                              self.audience,
                                                              board_name)
        else:
            self.title = "Comments for %s" % summaries[0].title

        #--------------------------------------------------------------
        # Invoke the Summary objects' make_table() method to do the
        # heavy lifting.
        #--------------------------------------------------------------
        return [summary.make_table() for summary in summaries]

    def set_report_options(self, opts):
        """
        Callback to adjust the report's options:
           * Plug in the title we created above in build_tables().
           * Add subtitle showing the date the report is run.
           * Override the report's default style sheet, to work around
             some of the anomalies we run into when the users paste the
             HTML report into Microsoft Word.
        """

        return {
            "banner": self.title,
            "subtitle": str(datetime.date.today()),
            "page_opts": { "stylesheets": ["/stylesheets/html-for-word.css"] }
        }

    def get_widths(self):
        """
        Calculate the column widths we'll use based on which of the
        optional extra columns have been selected by the user.
        """

        widths = [250, 500, 175, 150]
        if self.USER_AND_DATE not in self.extra:
            widths[1] += widths[2]
        if self.BLANK not in self.extra:
            widths[1] += widths[2]
        return widths

    def get_boards(self):
        """
        Assemble a dictionary of the PDQ board names, indexed by
        CDR Organization document ID. Trim the names to their
        short forms, pruning away the "PDQ" prefix and the
        "Editorial Board" suffix.
        """

        query = db.Query("query_term n", "n.doc_id", "n.value")
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

        query = db.Query("document d", "d.id", "d.title")
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

    def summaries_for_board(self):
        """
        The user has asked for a report of multiple summaries for
        one of the boards. Find the board's summaries whose language
        and audience match the request parameters, and return a
        list of Summary objects for them.
        Use Query class to simplify SQL creation for different logic paths.
        """

        b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        t_path = "/Summary/TranslationOf/@cdr:ref"
        query = db.Query("query_term a", "a.doc_id")
        query.where("a.path = '/Summary/SummaryMetaData/SummaryAudience'")
        query.where(query.Condition("a.value", self.audience + "s"))
        if self.language == "English":
            query.join("query_term b", "b.doc_id = a.doc_id")
        else:
            query.join("query_term t", "t.doc_id = a.doc_id")
            query.where(query.Condition("t.path", t_path))
            query.join("query_term b", "b.doc_id = t.int_val")
        query.where(query.Condition("b.path", b_path))
        query.where(query.Condition("b.int_val", self.board))
        query.join("active_doc d", "d.id = a.doc_id")
        query.join("doc_version v", "v.id = d.id")
        query.where("v.publishable = 'Y'")
        rows = query.unique().execute(self.cursor).fetchall()
        return sorted([Summary(row[0], self) for row in rows])

    def get_comment_tags(self):
        """
        Figure out which comment element tags we should look for,
        based on the user's choices.
        """

        tags = []
        if "R" in self.comment_types:
            tags = [Control.RESPONSE]
        if self.comment_types - set("R"):
            tags.append("Comment")
        return tags

    def validate(self):
        """
        Separate validation method, to make sure the CGI request's
        parameters haven't been tampered with by an intruder.
        """

        if self.audience not in self.AUDIENCES:
            cdrcgi.bail(cdrcgi.TAMPERING)
        if self.language not in self.LANGUAGES:
            cdrcgi.bail(cdrcgi.TAMPERING)
        if self.board:
            try:
                self.board = int(self.board)
            except:
                cdrcgi.bail(cdrcgi.TAMPERING)
            if self.board not in self.boards:
                cdrcgi.bail(cdrcgi.TAMPERING)
        if self.cdr_id:
            try:
                self.cdr_id = cdr.exNormalize(self.cdr_id)[1]
            except:
                cdrcgi.bail("Invalid format for CDR ID")
        if set(self.extra) - set([self.BLANK, self.USER_AND_DATE]):
            cdrcgi.bail(cdrcgi.TAMPERING)

class Cell(cdrcgi.Report.Cell):
    """
    Custom Cell class. We need more control over the table's report
    cells, because they will need to work around anomalies we run
    into when the HTML for the report is pasted into Microsoft Word.
    """

    def __init__(self, value, width, color=None, **options):
        """
        Invoke the base class's method, and then capture the
        custom attributes we need.
        """

        cdrcgi.Report.Cell.__init__(self, value, **options)
        self.width = width
        self.color = color

    def to_td(self):
        """
        Overriding this method is our incentive for deriving a custom
        Cell class, so that we can set the style attribute directly
        on the TD element.
        """
        td = cdrcgi.Page.B.TD(self._value)
        style = "width: %s;" % self.width
        if self.color:
            style += " color: %s;" % self.color
        td.set("style", style)
        if self._rowspan:
            td.set("rowspan", str(self._rowspan))
        return td

class Summary:
    """
    One of these for each summary on the report.
    """

    def __init__(self, doc_id, control):
        """
        Fetch the summary's document title and all of the comments which
        match the user's criteria for comment types. Collect the comments
        in Section objects so we only have to show the section title once
        for all of the section's comments.
        """

        self.id = doc_id
        self.control = control
        self.sections = []
        query = db.Query("document", "title", "xml")
        query.where(query.Condition("id", doc_id))
        self.title, xml = query.execute(control.cursor).fetchone()
        root = etree.XML(xml.encode("utf-8"))
        for node in root.findall("SummaryTitle"):
            self.title = node.text
        last_section_title = current_section = None
        for node in root.iter(*control.comment_tags):
            comment = Summary.Comment(node, control)
            if comment.in_scope():
                if comment.section_title != last_section_title:
                    last_section_title = comment.section_title
                    current_section = Summary.Section(comment.section_title)
                    self.sections.append(current_section)
                current_section.comments.append(comment)

    def __lt__(self, other):
        "Make the Summary list sortable"
        return self.title < other.title

    def make_table(self):
        """
        Generate the table for the report showing the selected comments
        for this summary.
        """

        styles = ["width: %dpx" % width for width in self.control.widths]
        columns = [
            cdrcgi.Report.Column("Summary Section Title", style=styles[0]),
            cdrcgi.Report.Column("Comments", style=styles[1])
        ]
        if Control.USER_AND_DATE in self.control.extra:
            columns.append(cdrcgi.Report.Column("User ID (Date)",
                                                style=styles[2]))
        if Control.BLANK in self.control.extra:
            columns.append(cdrcgi.Report.Column("Blank", style=styles[3]))
        rows = []
        for section in self.sections:
            rows += section.make_rows(self.control)
        return cdrcgi.Report.Table(columns, rows, caption=self.title,
                                   stripe=False)

    class Section:
        """
        Use this object to collect all of the comments in a summary
        section to be displayed on the report, so we only have to
        show the section's title once.
        """

        def __init__(self, title):
            "Capture the title and start with an empty comment list."
            self.title = title
            self.comments = []

        def make_rows(self, control):
            """
            Generate a list of rows for the summary section, one for
            each comment displayed in the report, with a rowspan
            attribute applied to the first column of the first row
            if there is more than one comments displayed for the
            section.
            """

            if not self.comments:
                return []
            opts = {}
            if len(self.comments) > 1:
                opts = { "rowspan": len(self.comments) }
            cell = Cell(self.title, control.widths[0], **opts)
            rows = [[cell] + self.comments[0].make_cells()]
            for comment in self.comments[1:]:
                rows.append(comment.make_cells())
            return rows

    class Comment:
        """
        One of these is created for each comment found in the summary,
        whether it will be displayed or not.
        """

        NO_SECTION_TITLE = "No Section Title" # In case we don't find one.

        def __init__(self, node, control):
            """
            Parse out all of the information we need from the comment's
            document node. Comment elements (as well as ResponseToComment
            elements) are constrained to have pure text content, rather
            than mixed content, which makes this much simpler.
            """

            self.control = control
            self.tag = node.tag
            self.text = node.text
            self.audience = node.get("audience")
            self.duration = node.get("duration")
            self.source = node.get("source")
            self.user = node.get("user")
            self.timestamp = node.get("date")
            self.section_title = self.get_section_title(node.getparent())

        def make_cells(self):
            """
            Create a list of our custom Cell objects for this comment,
            capturing the color and width to be used for the cell.
            Prefix the text for the comment with a bracketed set of
            single-character flags identifying the type of comment
            this is (audience, duration, and source).
            """

            if self.tag == Control.RESPONSE:
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
            text = "[%s] %s" % (label, self.text)
            cells = [Cell(text, self.control.widths[1], color)]
            if Control.USER_AND_DATE in self.control.extra:
                value = ""
                if self.user:
                    value = self.user
                    if self.timestamp:
                        value += " (%s)" % self.timestamp
                cells.append(Cell(value, self.control.widths[2]))
            if Control.BLANK in self.control.extra:
                cells.append(Cell("", self.control.widths[3]))
            return cells

        def get_section_title(self, node):
            """
            Recursively crawl up the tree until we hit the first
            SummarySection ancestor, and pull out the Title for
            that section. If the comment isn't in a summary
            section, or the section doesn't have a title, use
            a dummy title.
            """

            if node is None:
                return self.NO_SECTION_TITLE
            if node.tag == "SummarySection":
                for child in node.findall("Title"):
                    if child.text is None:
                        return self.NO_SECTION_TITLE
                    title = child.text.strip()
                    return title or self.NO_SECTION_TITLE
                return self.NO_SECTION_TITLE
            else:
                return self.get_section_title(node.getparent())

        def in_scope(self):
            """
            Return a Boolean indicating whether we should display this
            comment, based on the choices the user made on the report's
            request form.
            """

            wanted = self.control.comment_types
            if self.tag == Control.RESPONSE:
                return "R" in wanted
            if "C" in wanted:
                return True
            if self.duration == "permanent" and "P" in wanted:
                return True
            if self.source == "advisory-board" and "A" in wanted:
                return True
            if self.audience == "Internal":
                if "I" in wanted:
                    return self.duration != "permanent"
            if self.audience == "External":
                if "E" in wanted:
                    return self.source != "advisory-board"

#----------------------------------------------------------------------
# Instantiate our custom Control class and invoke the base class's
# run method. Wrap this in a test which let's use parse the script
# without performing any actual processing.
#----------------------------------------------------------------------
if __name__ == "__main__":
    Control().run()
