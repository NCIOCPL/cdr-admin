#!/usr/bin/env python

"""Request PDQ Advisory Board Members Summary Mailers.
"""

from datetime import datetime
from functools import cached_property
from json import dumps
from operator import attrgetter
from lxml import etree
from cdrapi.docs import Doc
from cdrcgi import Controller


class Control(Controller):
    """Top-level control for the mailer request script.

    Controls script processing, presenting the user with request options,
    collection the user's choices, and creating a job to generate the
    requested tracking documents.
    """

    SUBTITLE = "PDQ Advisory Board Members Tracking Request Form"
    LOGNAME = "advisory-board-trackers"
    INSTRUCTIONS = (
        "To generate tracking documents for an Advisory board, first select "
        "the board's name from the picklist below.",
        "If you check 'Create Trackers for All Summaries and All Board "
        "Members', tracking documents will be created immediately.",
        "If you want to select specific summaries and/or specific board "
        "members, check one of the other two radio buttons.",
        "If you check 'Select by Summary', you can select from the list "
        "below the radio buttons the specific summaries for which you want "
        "tracking documents created. You will be sent to a new page which "
        "lets you select the members for which the tracking documents "
        "should be created for each of the selected summaries.",
        "If you check 'Select by Board Member', you can select from the "
        "list below the radio buttons the specific members for which you "
        "want tracking documents to be created. You will be taken to a "
        "second page which will let you select the summaries for which "
        "the tracking documents should be created for each of the selected "
        "members.",
        "Click Submit when your selections are ready.",
    )
    PAGE1JS = "../../js/SummaryMailerReqFormPage1.js"
    PAGE2JS = "../../js/SummaryMailerReqFormPage2.js"

    def run(self):
        """Override for custom routing."""

        if not self.session.can_do("SUMMARY MAILERS"):
            self.bail("User not authorized to create Summary mailers")
        elif self.request == self.SUBMIT:
            if self.selection_method == "all" or self.pairs:
                return self.show_report()
            else:
                return self.show_candidates()
        return Controller.run(self)

    def build_tables(self):
        """
        Create the tracking documents and show them
        """

        trackers = []
        attrs = "reviewer.title", "summary.title"
        labels = "Tracker", "Reviewer", "Summary"
        if self.selection_method == "summary":
            attrs = "summary.title", "reviewer.title"
            labels = "Tracker", "Summary", "Reviewer"
        if self.selection_method == "all":
            for summary in list(self.board.summaries.values()):
                for recip_id in summary.checkbox_ids:
                    tracker = Tracker(self.session, summary.id, recip_id)
                    trackers.append(tracker)
        else:
            for pair in self.pairs:
                ids = [int(string) for string in pair.split("-")]
                if self.selection_method == "member":
                    ids.reverse()
                trackers.append(Tracker(self.session, *ids))
        msg = "queued %d tracker documents for creation"
        self.logger.info(msg, len(trackers))
        rows = []
        opts = dict(target="_blank")
        for tracker in sorted(trackers, key=attrgetter(*attrs)):
            try:
                id = tracker.save()
                url = f"ShowCdrDocument.py?doc-id={id:d}"
                cdr_id = Doc.normalize_id(id)
                tracker_link = self.Reporter.Cell(cdr_id, href=url, **opts)
            except Exception as e:
                tracker_link = str(e)
            title = tracker.reviewer.title
            url = f"QcReport.py?DocId={tracker.reviewer.id:d}"
            reviewer_link = self.Reporter.Cell(title, href=url, **opts)
            title = tracker.summary.title
            url = f"QcReport.py?DocId={tracker.summary.id:d}"
            summary_link = self.Reporter.Cell(title, href=url, **opts)
            if self.selection_method == "summary":
                rows.append((tracker_link, summary_link, reviewer_link))
            else:
                rows.append((tracker_link, reviewer_link, summary_link))
        cols = [self.Reporter.Column(label) for label in labels]
        opts = dict(columns=cols, caption="Trackers")
        return self.Reporter.Table(rows, **opts)

    def populate_form(self, page):
        """Put up the request form for PDQ summary mailer generation.

        Pass:
            page - HTMLPage object on which the form is drawn
        """

        self.add_instructions(page)
        fieldset = page.fieldset("Common Options")
        opts = dict(onchange="board_change()", options=self.board_list)
        fieldset.append(page.select("board", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Selection Method", id="method-block")
        fieldset.set("class", "hidden usa-fieldset")
        all = "Send All Summaries to all Board Members"
        opts = dict(label=all, value="all", checked=True)
        fieldset.append(page.radio_button("selection_method", **opts))
        opts = dict(label="Select by Summary", value="summary")
        fieldset.append(page.radio_button("selection_method", **opts))
        opts = dict(label="Select by Board Member", value="member")
        fieldset.append(page.radio_button("selection_method", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Choose Member(s)", id="members-block")
        fieldset.set("class", "hidden usa-fieldset")
        opts = dict(tooltip="Hold down the control (Ctrl) key while "
                    "left-clicking to select multiple board members",
                    multiple=True, classes="taller", onchange="memchg()")
        fieldset.append(page.select("members", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Choose One Or More Summaries(s)")
        fieldset.set("id", "summaries-block")
        fieldset.set("class", "hidden usa-fieldset")
        opts = dict(tooltip="Hold down the control (Ctrl) key while "
                    "left-clicking to select multiple summaries",
                    multiple=True, classes="taller", onchange="sumchg()")
        fieldset.append(page.select("summaries", **opts))
        page.form.append(fieldset)
        self.add_script(page)
        page.add_css("select.taller { height: 150px; }")

    def show_candidates(self):
        """Put up a cascading second form.

        Show the user the candidate recipient-summary pairs based
        on the initial selection of board member recipients or
        summary documents for the chosen board, and let the user
        refine the selections by pruning away some of the candidate
        pairs.
        """

        if not self.board:
            return self.show_form()
        page = self.form_page
        args = "selection_method", self.selection_method
        page.form.append(page.hidden_field(*args))
        page.form.append(page.hidden_field("board", self.board.id))
        fieldset = page.fieldset(self.board.name)
        div = page.B.DIV(page.B.CLASS("margin-bottom-3"), id="extra-buttons")
        div.append(page.button("Submit"))
        classes = "button usa-button margin-right-1"
        opts = dict(type="button", onclick="check_all();")
        div.append(page.B.BUTTON("Check All", page.B.CLASS(classes), **opts))
        opts["onclick"] = "clear_all();"
        div.append(page.B.BUTTON("Clear All", page.B.CLASS(classes), **opts))
        fieldset.append(div)
        self.board.show_choices(page, fieldset)
        page.form.append(fieldset)
        page.head.append(page.B.SCRIPT(src=self.PAGE2JS))
        page.add_css(
            ".outer-cb { margin-top: 2rem; }\n"
            ".inner-cb { margin-left: 1rem; }\n"
        )
        page.send()

    def add_instructions(self, page):
        """Explain (in a collabsible box) how to use the form.

        Pass:
            page - HTMLPage object for the form
        """

        tooltip = "Click [More] to see more complete instructions."
        opts = dict(title=tooltip, id="instructions")
        fieldset = page.fieldset("Instructions [More]", **opts)
        legend = fieldset.find("legend")
        legend.set("onclick", "toggle_help()")
        page.add_css("#instructions legend { cursor: pointer }")
        classes = []
        for paragraph in self.INSTRUCTIONS:
            p = page.B.P(paragraph)
            if classes:
                p.set("class", " ".join(classes))
            fieldset.append(p)
            classes = "more", "hidden"
        page.form.append(fieldset)

    def add_script(self, page):
        """Add the Javascript needed to make the form responsive.

        Pass:
            page - HTMLPage object to which we attach the script
        """

        page.add_script(self.board_objects)
        page.head.append(page.B.SCRIPT(src=self.PAGE1JS))

    @cached_property
    def board(self):
        "Load selected board, if any."

        board_id = self.fields.getvalue("board")
        if not board_id:
            return None
        if not board_id.isdigit():
            self.bail()
        board = self.boards.get(int(board_id))
        if not board:
            self.bail()
        return board

    @cached_property
    def board_list(self):
        "Generate a picklist for the PDQ Advisory Boards"

        boards = sorted(self.boards.values())
        return [("", "Choose One")] + [(b.id, b.name) for b in boards]

    @cached_property
    def board_objects(self):
        """Create JavaScript for a list of Board objects."""

        objects = ",\n".join([self.boards[key].script for key in self.boards])
        return f"""\
function Board(id, boardType, members, summaries) {{
    this.id        = id;
    this.boardType = boardType;
    this.members   = members;
    this.summaries = summaries;
}}
function Choice(label, value) {{
    this.label = label;
    this.value = value;
}}
var boards = {{
{objects}
}};"""

    @cached_property
    def boards(self):
        """
        Find out which boards have which summaries and which board members.
        Board members have two documents: a PDQBoardMemberInfo document
        and a Person document. We get the member's name from the first
        doc and the ID from the second (because that's the ID the mailer
        generation software expects).
        """

        boards = {}
        i_path = "/PDQBoardMemberInfo"
        p_path = f"{i_path}/BoardMemberName/@cdr:ref"
        c_path = f"{i_path}/BoardMembershipDetails/CurrentMember"
        b_path = f"{i_path}/BoardMembershipDetails/BoardName/@cdr:ref"
        t_path = "/Organization/OrganizationType"
        fields = "p.int_val", "b.int_val", "d.title"
        query = self.Query("active_doc d", *fields)
        query.join("doc_version v", "v.id = d.id")
        query.join("query_term c", "c.doc_id = d.id")
        query.join("query_term b", "b.doc_id = c.doc_id "
                   "AND LEFT(b.node_loc, 4) = LEFT(c.node_loc, 4)")
        query.join("active_doc active_board",
                   "active_board.id = b.int_val")
        query.join("query_term p", "p.doc_id = d.id")
        query.join("query_term t", "t.doc_id = b.int_val")
        query.where(query.Condition("v.val_status", "V"))
        query.where(query.Condition("c.path", c_path))
        query.where(query.Condition("b.path", b_path))
        query.where(query.Condition("t.path", t_path))
        query.where(query.Condition("p.path", p_path))
        query.where(query.Condition("c.value", "Yes"))
        query.where("t.value = 'PDQ Advisory Board'")
        query.unique()
        rows = query.execute(self.cursor).fetchall()
        for member_id, board_id, doc_title in rows:
            board = boards.get(board_id)
            if not board:
                board = boards[board_id] = Board(self, board_id)
            args = self, board, member_id, doc_title
            board.members[member_id] = BoardMember(*args)

        # Can't use placeholders in queries with subqueries because
        # of a Microsoft bug. OK because we control all of the
        # string values being tested.
        b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        a_path = "/Summary/SummaryMetaData/SummaryAudience"
        subquery = self.Query("document d", "d.id").unique()
        subquery.join("query_term t", "t.doc_id = d.id")
        subquery.where("t.path = '%s'" % t_path)
        subquery.where("t.value = 'PDQ Advisory Board'")
        cols = "d.id", "MAX(v.num)", "b.int_val", "d.title"
        query = self.Query("active_doc d", *cols)
        query.join("doc_version v", "v.id = d.id")
        query.join("query_term b", "b.doc_id = d.id")
        query.join("active_doc active_board",
                   "active_board.id = b.int_val")
        query.join("query_term a", "a.doc_id = d.id")
        query.where("v.publishable = 'Y'")
        query.where(query.Condition("b.int_val", subquery, "IN"))
        query.where("b.path = '%s'" % b_path)
        query.where("a.path = '%s'" % a_path)
        query.where("a.value = 'Health professionals'")
        query.group("d.id", "d.title", "b.int_val")
        rows = query.execute(self.cursor).fetchall()
        for doc_id, _, board_id, doc_title in rows:
            board = boards.get(board_id)
            if not board:
                board = boards[board_id] = Board(self, board_id)
            args = self, board, doc_id, doc_title
            board.summaries[doc_id] = BoardSummary(*args)
        return boards

    @cached_property
    def members(self):
        """Board members selected by the user."""

        members = self.fields.getlist("members") or ["all"]
        for value in members:
            if value != "all" and not value.isdigit():
                self.bail()
        return members

    @cached_property
    def pairs(self):
        """Summary/board member ID pairs selected by the user.

        This selection is produced by the refining step of the second
        (cascading) form.
        """

        pairs = self.fields.getlist("pairs")
        for pair in pairs:
            ids = pair.split("-")
            if len(ids) != 2:
                self.bail()
            for id in ids:
                if not id.isdigit():
                    self.bail()
        return pairs

    @cached_property
    def selection_method(self):
        """How the user wants to make the initial summary/member selection."""

        method = self.fields.getvalue("selection_method") or "all"
        if method not in {"all", "summary", "member"}:
            self.bail()
        return method

    @cached_property
    def subtitle(self):
        """Figure out what to display under the main banner."""

        if self.request == self.SUBMIT:
            if self.selection_method == "all" or self.pairs:
                return "Tracker Documents Generated"
        return self.SUBTITLE

    @cached_property
    def summaries(self):
        """Summaries selected by the user."""

        summaries = self.fields.getlist("summaries") or ["all"]
        for value in summaries:
            if value != "all" and not value.isdigit():
                self.bail()
        return summaries


class Board:
    "Holds information about a PDQ board with its summaries and board members"

    M_PATH = "/Summary/SummaryMetaData/PDQBoard/BoardMember/@cdr:ref"
    B_PATH = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
    N_PATH = "/Organization/OrganizationNameInformation/OfficialName/Name"
    O_PATH = "/Organization/OrganizationType"

    def __init__(self, control, doc_id):
        """Store the basic information about the board.

        The board's summaries and board members will be populated by
        code outside this class (see Control.collect_boards()).

        Pass:
            control - access to the database and the user's selections
            doc_id - integer for the board's unique CDR document ID
        """

        self.control = control
        self.id = doc_id

    def __lt__(self, other):
        "Support sorting the boards alphabetically by name."
        return self.name < other.name

    def show_choices(self, page, fieldset):
        """Populate the cascading form with selections the user can refine.

        Show checkboxes the user can use to review the proposed
        combinations of summaries and board member recipients, and
        optionally refine that list by removing some of the combinations.
        This method is somewhat tricky, as it must handle two different
        layouts for the checkboxes, one nesting summaries under each
        board member receiving the mailers, and the other nesting the
        board members under their summaries. The "inner" and "outer"
        properties in the code below are used to keep track of which
        sets are nested and which are nesting.

        Pass:
            page - HTMLPage on which the choices are placed
            fieldset - HTML element in which the checkboxes go
        """

        count = 0
        if self.control.selection_method == "member":
            selected = self.control.members
            self.outer, self.inner = self.members, self.summaries
        else:
            selected = self.control.summaries
            self.outer, self.inner = self.summaries, self.members
        if "all" in selected:
            outer = list(self.outer.values())
        else:
            outer = []
            for id in selected:
                o = self.outer.get(int(id))
                if not o:
                    self.control.bail()
                outer.append(o)
        for o in sorted(outer):
            inner = []
            for doc_id in o.checkbox_ids:
                i = self.inner.get(doc_id)
                if i:
                    inner.append(i)
            if not inner:
                continue
            count += 1
            opts = dict(
                label=o.name,
                value=o.id,
                onclick=f"outer_clicked({o.id:d})",
                checked=True,
                wrapper_classes="outer-cb",
            )
            fieldset.append(page.checkbox("outer", **opts))
            for i in sorted(inner):
                opts = dict(
                    label=i.name,
                    value=f"{o.id:d}-{i.id:d}",
                    classes=f"inner-{o.id:d}",
                    wrapper_classes="inner-cb",
                    checked=True,
                    onclick=f"inner_clicked({o.id:d})",
                )
                fieldset.append(page.checkbox("pairs", **opts))
        if not count:
            if self.control.selection_method == "member":
                msg = "None of the selected board members have any summaries"
            else:
                msg = "None of the selected summaries have any board members"
            self.control.bail(msg)

    @cached_property
    def members(self):
        """Dictionary of members of this board."""
        return {}

    @cached_property
    def name(self):
        """String for the board's name."""

        query = self.control.Query("query_term", "value")
        query.where(query.Condition("path", self.N_PATH))
        query.where(query.Condition("doc_id", self.id))
        rows = query.execute(self.control.cursor).fetchall()
        if not rows:
            message = f"No name found for board document CDR{self.id:d}"
            self.control.bail(message)
        return rows[0][0]

    @cached_property
    def summaries(self):
        """Dictionary of summaries managed by this board."""
        return {}

    @cached_property
    def type(self):
        """String for board's type (editorial or advisory)."""

        org_types = ("PDQ Editorial Board", "PDQ Advisory Board")
        query = self.control.Query("query_term", "value")
        query.where(query.Condition("path", self.O_PATH))
        query.where(query.Condition("value", org_types, "IN"))
        query.where(query.Condition("doc_id", self.id))
        rows = query.execute(self.control.cursor).fetchall()
        if not rows:
            self.control.bail(f"Can't find board type for {self.name!r}")
        if len(rows) > 1:
            message = f"Multiple board types found for {self.name!r}"
            self.control.bail(message)
        if rows[0][0].upper() == 'PDQ EDITORIAL BOARD':
            return 'editorial'
        return 'advisory'

    @cached_property
    def script(self):
        """
        Create the Javascript objects which are used at runtime to
        adjust the composition of the summary and board member picklists.
        """
        glue = ",\n        "
        members = list(self.members.values())
        summaries = list(self.summaries.values())
        if members:
            members = glue.join([m.script for m in sorted(members)])
            members = "\n        %s" % members
        if summaries:
            summaries = glue.join([s.script for s in sorted(summaries)])
            summaries = "\n        %s" % summaries
        return f"""\
    '{self.id}': new Board('{self.id}', '{self.type}', [{members}
    ], [{summaries}
    ])"""


class Choice:
    """
    Base class for picklist option that knows how to serialize itself
    as a Javascript object, supports sorting, and supports tricky
    checkbox pages with nested options for which gets which mailer.
    """

    NAME_DELIM = ";"

    def __init__(self, control, board, id, doc_title):
        """Remember the caller's values.

        Pass:
            control - access to the database and the user's selections
            board - Board object for the user's board selection
            id - integer for the board's member or summary
            doc_title - string for the member or summary title
        """

        self.control = control
        self.board = board
        self.id = id
        self.doc_title = doc_title

    def __lt__(self, other):
        """Sort the choices by their names."""
        return self.name < other.name

    @cached_property
    def name(self):
        """Parse the front part of the title for a name."""
        return self.doc_title.split(self.NAME_DELIM)[0].strip()

    @cached_property
    def script(self):
        """Create JavaScript object for the choice."""
        return f"""new Choice({dumps(self.name)}, "{self.id}")"""

    @cached_property
    def checkbox_ids(self):
        raise Exception("Property checkbox_ids method must be overridden.")


class BoardMember(Choice):
    """
    Option for picklist of members of a PDQ board. We do some additional
    trimming of the name to eliminate the '(board membership information)'
    suffix.
    """

    NAME_DELIM = "("

    @cached_property
    def checkbox_ids(self):
        """
        Find the document IDs of the summaries for which this board
        member is responsible in the context of her membership on
        this board. Used by the Board class to build a set of boxes
        the user can check or clear to customize the set of mailers
        which will be generated (see Board.show_choices() above).
        """
        query = self.control.Query("query_term m", "m.doc_id").unique()
        query.join("query_term b", "b.doc_id = m.doc_id",
                   "LEFT(b.node_loc, 8) = LEFT(m.node_loc, 8)")
        query.where(query.Condition("m.path", Board.M_PATH))
        query.where(query.Condition("b.path", Board.B_PATH))
        query.where(query.Condition("m.int_val", self.id))
        query.where(query.Condition("b.int_val", self.board.id))
        rows = query.execute(self.control.cursor).fetchall()
        return [row[0] for row in rows]


class BoardSummary(Choice):
    """Option for picklist of PDQ summaries for a single board."""

    @cached_property
    def checkbox_ids(self):
        """
        Find the document IDs of the members of this board who are
        responsible for reviewing this summary. Used by the Board
        class to build a set of boxes the user can check or clear
        to customize the set of mailers which will be generated
        (see Board.show_choices() above).
        """
        query = self.control.Query("query_term m", "m.int_val").unique()
        query.join("query_term b", "b.doc_id = m.doc_id",
                   "LEFT(b.node_loc, 8) = LEFT(m.node_loc, 8)")
        query.where(query.Condition("m.path", Board.M_PATH))
        query.where(query.Condition("b.path", Board.B_PATH))
        query.where(query.Condition("m.doc_id", self.id))
        query.where(query.Condition("b.int_val", self.board.id))
        rows = query.execute(self.control.cursor).fetchall()
        return [row[0] for row in rows]


class Tracker:
    """
    CDR document used to track review of a summary by an advisory board member.
    """

    NS = "cips.nci.nih.gov/cdr"
    NSMAP = dict(cdr=NS)
    NOW = datetime.now().isoformat().split(".")[0]
    TYPE = "Summary-PDQ Advisory Board"
    MODE = "Web-based"
    OPTS = dict(encoding="unicode", pretty_print=True)

    summaries = {}
    reviewers = {}

    def __init__(self, session, summary_id, reviewer_id):
        """
        Capture the information for the new tracker document

        Pass:
          session - Session object for the logged-in user
          summary - Doc object for the CDR PDQ Cancer Information Summary
          reviewer - Doc object for the board member
        """

        self.session = session
        self.summary_id = summary_id
        self.reviewer_id = reviewer_id

    @cached_property
    def summary(self):
        """CDR API `Doc` object for the tracker's PDQ Summary."""

        summary = Tracker.summaries.get(self.summary_id)
        if not summary:
            doc = Doc(self.session, id=self.summary_id)
            summary = Tracker.summaries[self.summary_id] = doc
        return summary

    @cached_property
    def reviewer(self):
        """CDR API `Doc` object for the tracker's board member."""

        reviewer = Tracker.reviewers.get(self.reviewer_id)
        if not reviewer:
            doc = Doc(self.session, id=self.reviewer_id)
            reviewer = Tracker.reviewers[self.reviewer_id] = doc
        return reviewer

    @cached_property
    def xml(self):
        """
        Serialized XML for the new CDR document encoded as UTF-8
        """

        root = etree.Element("Mailer", nsmap=self.NSMAP)
        etree.SubElement(root, "Type", Mode=self.MODE).text = self.TYPE
        child = etree.Element("Recipient")
        child.text = self.reviewer.title
        child.set(f"{{{self.NS}}}ref", self.reviewer.cdr_id)
        root.append(child)
        child = etree.Element("Document")
        child.text = self.summary.title
        child.set(f"{{{self.NS}}}ref", self.summary.cdr_id)
        root.append(child)
        etree.SubElement(root, "Sent").text = self.NOW
        return etree.tostring(root, **self.OPTS)

    def save(self):
        """Create and store a new CDR document to track the review.

        Return:
            integer for the newly created mailer tracking document
        """

        doc = Doc(self.session, xml=self.xml, doctype="Mailer")
        doc.save(unlock=True, val_types=["links", "schema"])
        return doc.id


if __name__ == "__main__":
    control = Control()
    try:
        control.run()
    except Exception:
        control.logger.exception("failure:")
