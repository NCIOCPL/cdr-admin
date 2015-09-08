#----------------------------------------------------------------------
#
# $Id$
#
# Request form for generating PDQ Editorial Board Members Mailing.
#
# BZIssue::1664
# BZIssue::3132
# BZIssue::OCECDR-3640: Unable to run Advisory Board Summary Mailers
# Rewritten Summer 2015 as part of security sweep.
#
#----------------------------------------------------------------------
import cdr
import cdrcgi
import cdrdb
import cdrmailcommon
import cgi
import sys

class Control(cdrcgi.Control):
    """
    Controls script processing, presenting the user with request options,
    collection the user's choices, and creating a job to generate the
    requested mailers.
    """

    SUBMENU = "Mailer Menu"
    TITLE = "CDR Administration"
    BUTTONS = ("Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out")

    def __init__(self):
        """
        Collect and verify the CGI parameters.
        """

        cdrcgi.Control.__init__(self)
        self.board_type = bt = self.fields.getvalue("BoardType") or "Editorial"
        self.boards = self.collect_boards()
        self.board = self.get_board()
        self.email = self.fields.getvalue("email")
        self.max_docs = self.fields.getvalue("max_docs") or "No limit"
        self.members = self.fields.getlist("members") or ["all"]
        self.summaries = self.fields.getlist("summaries") or ["all"]
        self.pairs = self.fields.getlist("pairs")
        self.method = self.fields.getvalue("method") or "all"
        self.section = "PDQ %s Board Members Mailer Request Form" % bt
        self.sanitize()

    def run(self):
        "Top-level processing driver"

        if self.request == cdrcgi.MAINMENU:
            cdrcgi.navigateTo("Admin.py", self.session)
        elif self.request == Control.SUBMENU:
            cdrcgi.navigateTo("Mailers.py", self.session)
        elif self.request == "Log Out":
            cdrcgi.logout(self.session)
        elif not self.board:
            self.show_form()
        elif self.method == "all" or self.pairs:
            self.submit_mailer_request()
        else:
            self.show_candidates()

    def submit_mailer_request(self):
        """
        Queue up the mailer job, possibly with instructions about
        who gets mailers for which summaries.
        """

        recipients = {}
        if self.method == "all":
            docs = []
            for doc_id in sorted(self.board.summaries):
                if len(docs) >= self.max_docs:
                    break
                summary = MailerRecipient.Summary(self.cursor, doc_id)
                docs.append((summary.id, summary.version))
        else:
            for pair in self.pairs:
                ids = pair.split("-")
                if self.method == "summary":
                    ids.reverse()
                recip_id = int(ids[0])
                summary_id = int(ids[1])
                recip = recipients.get(recip_id)
                if not recip:
                    recip = recipients[recip_id] = MailerRecipient(recip_id)
                summary = MailerRecipient.Summary(self.cursor, summary_id)
                recip.summaries.append(summary)
            versions = MailerRecipient.Summary.versions
            docs = [(id, versions[id]) for id in sorted(versions)]
        if not docs:
            cdrcgi.bail("No documents found")
        docs = ["%s/%d" % (cdr.normalize(id), ver) for id, ver in docs]
        subset = "Summary-PDQ %s Board" % self.board_type
        parms = (
            ("Board", cdr.normalize(self.board.id)),
            ("Person", "".join([str(r) for r in recipients.values()]))
        )
        result = cdr.publish(self.session, "Mailers", subset, parms, docs,
                             self.email, allowNonPub="Y")
        job_id, errors = result
        if not job_id:
            cdrcgi.bail("Unable to initiate publishing job: %s" % errors)
        msgs = ["Started directory mailer job - id = %s" % job_id,
                "                      Mailer type = %s" % subset,
                "          Number of docs selected = %d" % len(docs),
                "                        First doc = %s" % docs[0]]
        if len(docs) > 1:
            msgs.append("                       Second doc = %s" % docs[1])
        cdr.logwrite(msgs, cdrmailcommon.LOGFILE)
        page = cdrcgi.Page(Control.TITLE, subtitle=subset)
        page.add(page.B.H3("Job Number %s Submitted" % job_id))
        label = "Check the status of the mailer job"
        url = "PubStatus.py?id=%s" % job_id
        page.add(page.B.A(label, href=url))
        page.send()

    def show_form(self):
        "Put up the request form for PDQ summary mailer generation."

        opts = {
            "subtitle": self.section,
            "action": self.script,
            "buttons": self.BUTTONS,
            "session": self.session
        }
        page = cdrcgi.Page(Control.TITLE, **opts)
        page.add_hidden_field("BoardType", self.board_type)
        self.add_instructions(page)
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Common Options"))
        page.add_text_field("email", "Email",
                            value=cdr.getEmail(self.session) or "")
        page.add_text_field("max_docs", "Max Docs", value="No limit",
                            tooltip="Don't send more than this many documents")
        page.add_select("board", "Board", self.make_board_list(),
                        onchange="board_change()")
        page.add("</fieldset>")
        page.add('<fieldset id="method-block" class="hidden">')
        page.add(page.B.LEGEND("Selection Method"))
        page.add_radio("method", "Send All Summaries to all Board Members",
                       "all", checked=True)
        page.add_radio("method", "Select by Summary", "summary")
        page.add_radio("method", "Select by Board Member", "member")
        page.add("</fieldset>")
        page.add('<fieldset id="members-block" class="hidden">')
        page.add(page.B.LEGEND("Choose Member(s)"))
        page.add_select("members", "Members", (), onchange="memchg()",
                        multiple=True, tooltip="Hold down the control (Ctrl) "
                        "key while left-clicking to select multiple board "
                        "members", classes="taller")
        page.add("</fieldset>")
        page.add('<fieldset id="summaries-block" class="hidden">')
        page.add(page.B.LEGEND("Choose One Or More Summaries"))
        page.add_select("summaries", "Summaries", (), onchange="sumchg()",
                        multiple=True, tooltip="Hold down the control (Ctrl) "
                        "key while left-clicking to select multiple summaries",
                        classes="taller")
        page.add("</fieldset>")
        self.add_script(page)
        page.add_css("select.taller { height: 150px; }")
        page.send()

    def show_candidates(self):
        """
        Show the user the candidate recipient-summary pairs based
        on the initial selection of board member recipients or
        summary documents for the chosen board, and let the user
        refine the selections by pruning away some of the candidate
        pairs.
        """
        opts = {
            "buttons": self.BUTTONS,
            "subtitle": "Board Mailer Request Form",
            "action": self.script,
            "session": self.session
        }
        form = cdrcgi.Page(self.TITLE, **opts)
        form.add_hidden_field("BoardType", self.board_type)
        form.add_hidden_field("method", self.method)
        form.add_hidden_field("board", self.board.id)
        form.add_hidden_field("email", self.email)
        form.add("<fieldset>")
        form.add(form.B.LEGEND(self.board.name))
        form.add('<div id="extra-buttons">')
        form.add(form.B.BUTTON("Check All", type="button",
                               onclick="check_all()"))
        form.add(form.B.BUTTON("Clear All", type="button",
                               onclick="clear_all()"))
        form.add("</div>")
        self.board.show_choices(form)
        form.add("</fieldset>")
        form.add_script("""\
function check_all() {
    jQuery(".outer-cb input").prop("checked", true);
    jQuery(".inner-cb input").prop("checked", true);
}
function clear_all() {
    jQuery(".outer-cb input").prop("checked", false);
    jQuery(".inner-cb input").prop("checked", false);
}
function inner_clicked(id) {
    if (jQuery(".inner-" + id + ":checked").length > 0)
        jQuery("#outer-" + id).prop("checked", true);
    else
        jQuery("#outer-" + id).prop("checked", false);
}
function outer_clicked(id) {
    if (jQuery("#outer-" + id + ":checked").length > 0)
        jQuery(".inner-" + id).prop("checked", true);
    else
        jQuery(".inner-" + id).prop("checked", false);
}""")

        form.add_css("""\
fieldset { width: 750px; padding-bottom: 25px; }
.outer-cb { margin-top: 15px; }
.inner-cb { margin-left: 15px; }
#extra-buttons { xtext-align: center; margin: 15px 0 5px 25px; }""")
        form.send()

    def add_instructions(self, page):
        "Explain (in a collabsible box) how to use the form."

        tooltip = "Click [More] to see more complete instructions."
        page.add('<fieldset id="instructions" title="%s">' % tooltip)
        page.add(page.B.LEGEND("Instructions [More]", onclick="toggle_help()"))
        page.add_css("#instructions legend { cursor: pointer }")
        page.add(page.B.P("To generate mailers for an %s board, first "
                          "select the board's name from the picklist "
                          "below." % self.board_type))
        page.add(page.B.P("If you check 'Send All Summaries to all Board "
                          "Members', all summaries will be sent to all "
                          "appropriate board members.",
                          page.B.CLASS("more hidden")))
        page.add(page.B.P("If you want to select specific summaries to send "
                          "to specific board members check one of the other "
                          "two radio buttons.", page.B.CLASS("more hidden")))
        page.add(page.B.P("If you check 'Select by Summary', you can select "
                          "from the list below the radio buttons, the "
                          "specific summaries you want to include in the "
                          "mailer. You will be sent to a new page that "
                          "contains the members who can receive the mailer, "
                          "grouped by summary.", page.B.CLASS("more hidden")))
        page.add(page.B.P("If you check 'Select by Board Member', you can "
                          "select from the list below the radio buttons, "
                          "the specific members you want to include in the "
                          "mailer. You will be sent to a new page that "
                          "contains the summaries that can be sent, grouped "
                          "by Board Member.", page.B.CLASS("more hidden")))
        page.add(page.B.P("It may take a minute to select documents to be "
                          "included in the mailing. Please be patient. If "
                          "you want to, you can limit the number of summary "
                          "documents for which mailers will be generated "
                          "in a given job, by entering a maximum number.",
                          page.B.CLASS("more hidden")))
        page.add(page.B.P("To receive email notification when the job is "
                          "completed, enter your email address.",
                          page.B.CLASS("more hidden")))
        page.add(page.B.P("Click Submit to start the mailer job.",
                          page.B.CLASS("more hidden")))
        page.add("</fieldset>")

    def add_script(self, page):
        "Add the Javascript needed to make the form responsive."
        page.add_script(self.make_board_objects())
        page.add_script("""\
function toggle_help() {
    var tooltip = 'Click [More] to see more complete instructions.';
    switch (jQuery('#instructions legend').text()) {
        case 'Instructions [More]':
            tooltip = 'Click [Less] to collapse instructions box.';
            jQuery('.more').show();
            jQuery('#instructions legend').text('Instructions [Less]');
            jQuery('#instructions').attr('title', tooltip);
            break;
        default:
            jQuery('.more').hide();
            jQuery('#instructions legend').text('Instructions [More]');
            jQuery('#instructions').attr('title', tooltip);
            break;
    }
}
function check_method(method) {
    switch (method) {
        case 'all':
            jQuery('#members-block').hide();
            jQuery('#summaries-block').hide();
            break;
        case 'summary':
            jQuery('#members-block').hide();
            jQuery('#summaries-block').show();
            break;
        case 'member':
            jQuery('#members-block').show();
            jQuery('#summaries-block').hide();
            break;
    }
}
function check_all(which) {
    var specific = false;
    jQuery('#' + which + ' .individual:selected').each(function() {
        if (jQuery(this).val() != 'all')
            specific = true;
    });
    if (specific)
        jQuery('#' + which + " .all").removeAttr('selected');
    else
        jQuery('#' + which + " .individual").removeAttr('selected');
}
function memchg() { check_all('members'); }
function sumchg() { check_all('summaries'); }
function board_change() {
    var board_id = jQuery('#board option:selected').val();
    if (!board_id) {
        jQuery('#method-block').hide();
        jQuery('#members-block').hide();
        jQuery('#summaries-block').hide();
        return;
    }
    jQuery('#method-block').show();
    check_method(jQuery('input[name=method]:checked').val());
    var board = boards[board_id];
    var members = jQuery('#members');
    var summaries = jQuery('#summaries');
    members.empty();
    summaries.empty();
    var tag = '<option value="all" class="all" selected>';
    members.append(jQuery(tag + 'All Members of Board</option>'));
    summaries.append(jQuery(tag + 'All Summaries for Board</option>'));
    var option = '<option class="individual"></option>';
    jQuery.each(board.members, function(id, m) {
        members.append(jQuery(option).val(m.value).html(m.label));
    });
    jQuery.each(board.summaries, function(id, s) {
        summaries.append(jQuery(option).val(s.value).html(s.label));
    });
}
jQuery(document).ready(function() { board_change(); });""")

    def make_board_list(self):
        "Generate a picklist for the PDQ Editorial Boards"
        boards = sorted(self.boards.values())
        return [("", "Choose One")] + [(b.id, b.name) for b in boards]

    def sanitize(self):
        "Make sure the CGI parameters haven't been tampered with."
        msg = cdrcgi.TAMPERING
        if not self.session or not cdr.canDo(self.session, "SUMMARY MAILERS"):
            cdrcgi.bail("User not authorized to create Summary mailers")
        cdrcgi.valParmVal(self.request, val_list=self.BUTTONS, empty_ok=True,
                          msg=msg)
        cdrcgi.valParmEmail(self.email, empty_ok=True,
                            msg="Invalid email address")
        cdrcgi.valParmVal(self.board_type, val_list=("Editorial", "Advisory"),
                          msg=msg)
        cdrcgi.valParmVal(self.method, val_list=("all", "summary", "member"),
                          msg=msg)
        self.all_or_digits(self.members)
        self.all_or_digits(self.summaries)
        if self.max_docs == "No limit":
            self.max_docs = sys.maxint
        else:
            if not self.max_docs.isdigit():
                cdrcgi.bail("Invalid value for max docs")
            self.max_docs = int(self.max_docs)
        if self.max_docs < 1:
            cdrcgi.bail("Invalid value for max docs")
        for pair in self.pairs:
            ids = pair.split("-")
            if len(ids) != 2 or not ids[0].isdigit() or not ids[1].isdigit():
                cdrcgi.bail()

    def collect_boards(self):
        """
        Find out which boards have which summaries and which board members.
        Board members have two documents: a PDQBoardMemberInfo document
        and a Person document. We get the member's name from the first
        doc and the ID from the second (because that's the ID the mailer
        generation software expects).
        """

        boards = {}
        p_path = "/PDQBoardMemberInfo/BoardMemberName/@cdr:ref"
        c_path = "/PDQBoardMemberInfo/BoardMembershipDetails/CurrentMember"
        b_path = "/PDQBoardMemberInfo/BoardMembershipDetails/BoardName/@cdr:ref"
        t_path = "/Organization/OrganizationType"
        board_type = "PDQ %s Board" % self.board_type
        query = cdrdb.Query("active_doc d", "p.int_val", "b.int_val", "d.title")
        query.join("doc_version v", "v.id = d.id")
        query.join("query_term c", "c.doc_id = d.id")
        query.join("query_term b", "b.doc_id = c.doc_id "
                   "AND LEFT(b.node_loc, 4) = LEFT(c.node_loc, 4)")
        query.join("active_doc active_board", "active_board.id = b.int_val")
        query.join("query_term p", "p.doc_id = d.id")
        query.join("query_term t", "t.doc_id = b.int_val")
        query.where(query.Condition("v.val_status", "V"))
        query.where(query.Condition("c.path", c_path))
        query.where(query.Condition("b.path", b_path))
        query.where(query.Condition("t.path", t_path))
        query.where(query.Condition("p.path", p_path))
        query.where(query.Condition("c.value", "Yes"))
        query.where(query.Condition("t.value", board_type))
        query.unique()
        rows = query.execute(self.cursor, timeout=300).fetchall()
        for member_id, board_id, doc_title in rows:
            board = boards.get(board_id)
            if not board:
                board = boards[board_id] = Board(self, board_id)
            board.members[member_id] = BoardMember(board, member_id, doc_title)

        # Can't use placeholders in queries with subqueries because
        # of a Microsoft bug. OK because we control all of the
        # string values being tested.
        b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        a_path = "/Summary/SummaryMetaData/SummaryAudience"
        subquery = cdrdb.Query("document d", "d.id").unique()
        subquery.join("query_term t", "t.doc_id = d.id")
        subquery.where("t.path = '%s'" % t_path)
        subquery.where("t.value = '%s'" % board_type)
        query = cdrdb.Query("active_doc d", "d.id", "MAX(v.num)",
                            "b.int_val", "d.title")
        query.join("doc_version v", "v.id = d.id")
        query.join("query_term b", "b.doc_id = d.id")
        query.join("active_doc active_board", "active_board.id = b.int_val")
        query.join("query_term a", "a.doc_id = d.id")
        query.where("v.publishable = 'Y'")
        query.where(query.Condition("b.int_val", subquery, "IN"))
        query.where("b.path = '%s'" % b_path)
        query.where("a.path = '%s'" % a_path)
        query.where("a.value = 'Health professionals'")
        query.group("d.id", "d.title", "b.int_val")
        rows = query.execute(self.cursor, timeout=300).fetchall()
        for doc_id, doc_version, board_id, doc_title in rows:
            board = boards.get(board_id)
            if not board:
                board = boards[board_id] = Board(self, board_id)
            board.summaries[doc_id] = BoardSummary(board, doc_id, doc_title)
        return boards

    def get_board(self):
        "Load selected board, if any."
        board_id = self.fields.getvalue("board")
        if not board_id:
            return None
        if not board_id.isdigit():
            cdrcgi.bail()
        board = self.boards.get(int(board_id))
        if not board:
            cdrcgi.bail()
        return board

    def make_board_objects(self):
        """
        Create JavaScript for a list of Board objects.
        """
        return """\
function Board(id, boardType, members, summaries) {
    this.id        = id;
    this.boardType = boardType;
    this.members   = members;
    this.summaries = summaries;
}
function Choice(label, value) {
    this.label = label;
    this.value = value;
}
var boards = {
%s
};""" % ",\n".join([self.boards[key].to_script() for key in self.boards])

    @staticmethod
    def all_or_digits(values):
        "Make sure every value in the list is a number or the string 'all'"
        for value in values:
            if value != "all" and not value.isdigit():
                cdrcgi.bail()

class Board:
    "Holds information about a PDQ board with its summaries and board members"

    M_PATH = "/Summary/SummaryMetaData/PDQBoard/BoardMember/@cdr:ref"
    B_PATH = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"

    def __init__(self, control, doc_id):
        """
        Store the basic information about the board. The board's
        summaries and board members will be populated by code outside
        this class (see Control.collect_boards()).
        """
        self.control = control
        self.id = doc_id
        self.members = {}
        self.summaries = {}
        path = "/Organization/OrganizationNameInformation/OfficialName/Name"
        query = cdrdb.Query("query_term", "value")
        query.where(query.Condition("path", path))
        query.where(query.Condition("doc_id", doc_id))
        rows = query.execute(control.cursor, timeout=300).fetchall()
        if not rows:
            cdrcgi.bail("No name found for board document CDR%d" % id)
        self.name = rows[0][0]
        org_types = ("PDQ Editorial Board", "PDQ Advisory Board")
        query = cdrdb.Query("query_term", "value")
        query.where(query.Condition("path", "/Organization/OrganizationType"))
        query.where(query.Condition("value", org_types))
        query.where(query.Condition("doc_id", doc_id))
        if not rows:
            cdrcgi.bail("Can't find board type for %s" % repr(self.name))
        if len(rows) > 1:
            cdrcgi.bail("Multiple board types found for %s" % repr(self.name))
        if rows[0][0].upper() == 'PDQ EDITORIAL BOARD':
            self.type = 'editorial'
        else:
            self.type = 'advisory'

    def show_choices(self, form):
        """
        Show checkboxes the user can use to review the proposed
        combinations of summaries and board member recipients, and
        optionally refine that list by removing some of the combinations.
        This method is somewhat tricky, as it must handle two different
        layouts for the checkboxes, one nesting summaries under each
        board member receiving the mailers, and the other nesting the
        board members under their summaries. The "inner" and "outer"
        properties in the code below are used to keep track of which
        sets are nested and which are nesting.
        """
        count = 0
        if self.control.method == "member":
            selected = self.control.members
            self.outer, self.inner = self.members, self.summaries
        else:
            selected = self.control.summaries
            self.outer, self.inner = self.summaries, self.members
        if "all" in selected:
            outer = self.outer.values()
        else:
            outer = []
            for id in selected:
                o = self.outer.get(int(id))
                if not o:
                    cdrcgi.bail()
                outer.append(o)
        for o in sorted(outer):
            inner = []
            for doc_id in o.get_checkbox_ids():
                i = self.inner.get(doc_id)
                if i:
                    inner.append(i)
            if not inner:
                continue
            count += 1
            form.add_checkbox("outer", o.name, str(o.id),
                              onclick="outer_clicked(%d)" % o.id,
                              wrapper_classes="outer-cb", checked=True)
            for i in sorted(inner):
                combo = "%d-%d" % (o.id, i.id)
                form.add_checkbox("pairs", i.name, combo,
                                  widget_classes="inner-%d" % o.id,
                                  wrapper_classes="inner-cb", checked=True,
                                  onclick="inner_clicked(%d)" % o.id)
        if not count:
            if inner_name == "members":
                inner_name = "board members"
            else:
                outer_name = "board members"
            cdrcgi.bail("None of the selected %s have any %s" %
                        (outer_name, inner_name))

    def to_script(self):
        """
        Create the Javascript objects which are used at runtime to
        adjust the composition of the summary and board member picklists.
        """
        glue = ",\n        "
        members = self.members.values()
        summaries = self.summaries.values()
        if members:
            members = glue.join([m.to_script() for m in sorted(members)])
            members = "\n        %s" % members
        if summaries:
            summaries = glue.join([s.to_script() for s in sorted(summaries)])
            summaries = "\n        %s" % summaries
        return """\
    '%s': new Board('%s', '%s', [%s
    ], [%s
    ])""" % (self.id, self.id, self.type, members, summaries)

    def __cmp__(self, other):
        "Support sorting the boards alphabetically by name."
        return cmp(self.name, other.name)

class Choice:
    """
    Base class for picklist option that knows how to serialize itself
    as a Javascript object, supports sorting, and supports tricky
    checkbox pages with nested options for which gets which mailer.
    """
    def __init__(self, board, id, doc_title):
        self.board = board
        self.id = id
        self.name = doc_title.split(";")[0].strip()
    def __cmp__(self, other):
        return cmp(self.name, other.name)
    def to_script(self):
        name = cdrcgi.unicodeToJavaScriptCompatible(self.name)
        return "new Choice('%s', '%s')" % (name.replace("'", "\\'"), self.id)
    def get_checkbox_ids(self):
        cdrcgi.bail("Internal error: "
                    "get_checkbox_ids method must be overridden.")

class BoardMember(Choice):
    """
    Option for picklist of members of a PDQ board. We do some additional
    trimming of the name to eliminate the '(board membership information)'
    suffix.
    """
    def __init__(self, board, doc_id, doc_title):
        Choice.__init__(self, board, doc_id, doc_title)
        self.name = self.name.split("(")[0].strip()

    def get_checkbox_ids(self):
        """
        Find the document IDs of the summaries for which this board
        member is responsible in the context of her membership on
        this board. Used by the Board class to build a set of boxes
        the user can check or clear to customize the set of mailers
        which will be generated (see Board.show_choices() above).
        """
        query = cdrdb.Query("query_term m", "m.doc_id").unique()
        query.join("query_term b", "b.doc_id = m.doc_id",
                   "LEFT(b.node_loc, 8) = LEFT(m.node_loc, 8)")
        query.where(query.Condition("m.path", Board.M_PATH))
        query.where(query.Condition("b.path", Board.B_PATH))
        query.where(query.Condition("m.int_val", self.id))
        query.where(query.Condition("b.int_val", self.board.id))
        rows = query.execute(self.board.control.cursor).fetchall()
        return [row[0] for row in rows]

class BoardSummary(Choice):
    "Option for picklist of PDQ summaries for a single board"
    def __init__(self, board, doc_id, doc_title):
        Choice.__init__(self, board, doc_id, doc_title)

    def get_checkbox_ids(self):
        """
        Find the document IDs of the members of this board who are
        responsible for reviewing this summary. Used by the Board
        class to build a set of boxes the user can check or clear
        to customize the set of mailers which will be generated
        (see Board.show_choices() above).
        """
        query = cdrdb.Query("query_term m", "m.int_val").unique()
        query.join("query_term b", "b.doc_id = m.doc_id",
                   "LEFT(b.node_loc, 8) = LEFT(m.node_loc, 8)")
        query.where(query.Condition("m.path", Board.M_PATH))
        query.where(query.Condition("b.path", Board.B_PATH))
        query.where(query.Condition("m.doc_id", self.id))
        query.where(query.Condition("b.int_val", self.board.id))
        rows = query.execute(self.board.control.cursor).fetchall()
        return [row[0] for row in rows]

class MailerRecipient:
    """
    Used to collect mailer recipients when we're creating the mailer
    job, and the user is cherry-picking who gets which summary.
    """
    def __init__(self, id):
        self.id = id
        self.summaries = []

    def __str__(self):
        """
        Serialize this recipient and the summaries for which she is
        to receive mailers.
        """
        return "%d [%s]" % (self.id, " ".join([str(s) for s in self.summaries]))

    class Summary:
        """
        Summary for which mailers are about to be requested. We
        cache the latest publishable versions so we don't have to
        look them up repeatedly for each summary.
        """

        versions = {}

        def __init__(self, cursor, id):
            """
            Store the document ID and latest publishable version for the
            summary. Use the cached version number if we've already
            looked it up.
            """
            self.id = id
            self.version = self.versions.get(id)
            if not self.version:
                query = cdrdb.Query("doc_version", "MAX(num)")
                query.where("publishable = 'Y'")
                query.where(query.Condition("id", id))
                rows = query.execute(cursor).fetchall()
                if not rows:
                    cdrcgi.bail("No publishable version found for CDR%d" % id)
                self.versions[id] = self.version = rows[0][0]

        def __str__(self):
            "Serialize this summary's ID/version for the mailer job request."
            return "%d/%d" % (self.id, self.version)

if __name__ == "__main__":
    Control().run()
