#!/usr/bin/env python

"""Display the Board Roster with or without assistant information.
"""

from lxml import html
from cdrcgi import Controller
from cdrapi.docs import Doc

class Control(Controller):
    """Logic for creating the report."""

    SUBTITLE = "PDQ Board Roster"
    LOGNAME = "BoardRoster"
    METHOD = "get"
    BOARD_TYPES = (
        ("editorial", "PDQ Editorial Boards", True),
        ("advisory", "PDQ Editorial Advisory Boards", False),
    )
    GROUPINGS = (
        ("by_member", "Single sequence of all board members", True),
        ("by_board", "Group by PDQ board", False),
    )
    FORMATS = (
        ("full", "Full report", True),
        ("summary", "Summary report", False),
    )
    OPTIONAL_COLUMNS = (
        ("board_name", "Board Name", True),
        ("phone", "Phone", False),
        ("fax", "Fax", False),
        ("email", "Email", False),
        ("cdrid", "CDR ID", False),
        ("start_date", "Start Date", False),
        ("govt_employee", "Government Employee", False),
        ("blank", "Blank Column", False),
    )
    WIDTHS = dict(
        phone="100px;",
        fax="100px;",
        start_date="75px;",
        blank="100px;",
    )
    COLUMN_OVERRIDES = dict(
        govt_employee="Gov. Empl",
        blank="Blank",
    )

    def build_tables(self):
        """Create table(s) for the "summary" version of the report."""

        if self.report_format == "full":
            self.show_full_report()
        else:
            opts = dict(columns=self.headers)
            if self.grouping == "by_member":
                rows = []
                for member in self.members:
                    rows.append(member.row)
                #self.bail(f"{len(rows)} rows")
                opts["caption"] = self.caption
                return self.Reporter.Table(rows, **opts)
            tables = []
            for board in self.boards:
                rows = []
                for member in board.members:
                    rows.append(member.row)
                opts["caption"] = f"{board.name} Roster"
                tables.append(self.Reporter.Table(rows, **opts))
            return tables

    def show_full_report(self):
        """Show the QC-format version of the report."""

        buttons = self.SUBMENU, self.ADMINMENU, self.LOG_OUT
        opts = {
            "action": self.script,
            "buttons": [self.HTMLPage.button(b) for b in buttons],
            "subtitle": self.subtitle,
            "session": self.session
        }
        page = self.HTMLPage(self.title, **opts)
        page.body.set("class", "report")
        page.add_css("""\
h3 { color: black; }
th, td { border: none; font-size: 12pt; padding: 0; }
i { font-style: normal; }
p { margin: 0 0 35px 0; font-style: italic; }""")

        if self.grouping == "by_member":
            for member in self.members:
                page.form.append(member.html)
                page.form.append(page.B.P(member.board.name))
        else:
            for board in self.boards:
                page.form.append(page.B.H3(board.name))
                for member in board.members:
                    page.form.append(member.html)
        page.send()

    def populate_form(self, page):
        """
        Add the fields to the form page.

        Pass:
            page - HTMLPage object to be populated
        """

        fieldset = page.fieldset("Select Boards")
        for value, label, checked in self.BOARD_TYPES:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("board_type", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Report Grouping")
        for value, label, checked in self.GROUPINGS:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("grouping", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Report Format")
        fieldset.set("id", "report-formats")
        for value, label, checked in self.FORMATS:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("format", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Optional Table Columns")
        fieldset.set("id", "columns")
        for value, label, checked in self.OPTIONAL_COLUMNS:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.checkbox("column", **opts))
        page.form.append(fieldset)
        page.add_script("""\
function check_format(which) {
    let format = jQuery("#report-formats input:checked").val();
    console.log("format is now " + format);
    if (format == "full")
        jQuery("#columns").hide();
    else
        jQuery("#columns").show();
}
jQuery(function() {
    //jQuery("#report-formats input").click(check_format);
    check_format();
});""")

    @property
    def boards(self):
        """All active PDQ boards of the selected type."""

        if not hasattr(self, "_boards"):
            boards = []
            board_type = f"PDQ {self.board_type.title()} Board"
            query = self.Query("active_doc b", "b.id", "b.title")
            query.join("query_term t", "t.doc_id = b.id")
            query.where("t.path = '/Organization/OrganizationType'")
            query.where(query.Condition("t.value", board_type))
            for row in query.execute(self.cursor).fetchall():
                boards.append(Board(self, row))
            self._boards = sorted(boards)
        return self._boards

    @property
    def board_type(self):
        """Board type (advisory or editorial) selected for the report."""
        return self.fields.getvalue("board_type")

    @property
    def caption(self):
        """Default caption for the tabular report."""
        return f"PDQ {self.board_type.title()} Board Member Roster"

    @property
    def columns(self):
        """Optional columns which have been selected for the tabular report."""
        return self.fields.getlist("column")

    @property
    def grouping(self):
        """Grouping ("by_member" or "by_board") chosen for the report."""
        return self.fields.getvalue("grouping")

    @property
    def headers(self):
        """Column headers for the tabular ("summary") report."""

        if not hasattr(self, "_headers"):
            self._headers = ["Board Member"]
            for name, display, default in self.OPTIONAL_COLUMNS:
                if name in self.columns:
                    header = self.COLUMN_OVERRIDES.get(name, display)
                    width = self.WIDTHS.get(name)
                    if width is not None:
                        header = self.Reporter.Column(header, width=width)
                    self._headers.append(header)
        return self._headers

    @property
    def members(self):
        """All active members of board of the selected type."""

        if not hasattr(self, "_members"):
            members = []
            for board in self.boards:
                members += board.members
            self._members = sorted(members)
        return self._members

    @property
    def report_format(self):
        """Selected flavor of the report ("full" or "summary")."""
        return self.fields.getvalue("format")


class Board:
    """One advisory or editorial PDQ board."""

    DETAILS = "/PDQBoardMemberInfo/BoardMembershipDetails"
    BOARD_PATH = f"{DETAILS}/BoardName/@cdr:ref"
    CURRENT_PATH = f"{DETAILS}/CurrentMember"
    TERM_START_PATH = f"{DETAILS}/TermStartDate"
    GOVT_EMPLOYEE_PATH = "/PDQBoardMemberInfo/GovernmentEmployee"
    PERSON_PATH = f"/PDQBoardMemberInfo/BoardMemberName/@cdr:ref"
    IACT = "Integrative, Alternative, and Complementary Therapies"
    FULL_FIELDS = (
        "m.doc_id AS member_id",
        "d.title AS person_name",
    )
    SUMMARY_FIELDS = FULL_FIELDS + (
        "g.value AS govt_employee",
        "t.value AS term_start",
    )
    FIELDS = dict(full=FULL_FIELDS, summary=SUMMARY_FIELDS)

    def __init__(self, control, row):
        """Capture the information provided by the caller."""

        self.__control = control
        self.__row = row

    def __lt__(self, other):
        """Make the `Board` objects sortable by name, case-insensitive."""
        return self.name.lower() < other.name.lower()

    @property
    def control(self):
        """Access to the database and the runtime report parameters."""
        return self.__control

    @property
    def fields(self):
        """Values which need to be fetched from the database for this board."""
        return self.FIELDS[self.control.report_format]

    @property
    def id(self):
        """CDR document ID for the board's Organization document."""
        return self.__row.id

    @property
    def name(self):
        """Board name, tailored for display in the report."""

        if not hasattr(self, "_title"):
            title = self.__row.title.replace(self.IACT, "IACT")
            self._title = title.split(";")[0].strip()
        return self._title

    @property
    def members(self):
        """Sorted sequence of `Member` objects for this PDQ board."""

        if not hasattr(self, "_members"):
            query = self.control.Query("query_term m", *self.fields).unique()
            query.where(query.Condition("m.path", self.BOARD_PATH))
            query.where(query.Condition("m.int_val", self.id))
            query.join("query_term c", "c.doc_id = m.doc_id")
            query.where(query.Condition("c.path", self.CURRENT_PATH))
            query.where("c.value = 'Yes'")
            query.join("query_term p", "p.doc_id = m.doc_id")
            query.where(query.Condition("p.path", self.PERSON_PATH))
            query.join("active_doc d", "d.id = p.int_val")
            if self.control.report_format == "summary":
                query.join("query_term g", "g.doc_id = m.doc_id")
                query.where(query.Condition("g.path", self.GOVT_EMPLOYEE_PATH))
                query.outer("query_term t", "t.doc_id = m.doc_id",
                            "LEFT(t.node_loc, 4) = LEFT(m.node_loc, 4)",
                            f"t.path = '{self.TERM_START_PATH}'")
            members = []
            for row in query.execute(self.control.cursor).fetchall():
                members.append(self.Member(self, row))
            self._members = sorted(members)
        return self._members


    class Member:
        """Member of a PDQ board."""

        PREP_FILTERS = (
            "set:Denormalization PDQBoardMemberInfo Set",
            "name:Copy XML for Person 2",
        )
        FINISHING_FILTERS = dict(
            summary="PDQBoardMember Roster Summary",
            full="PDQBoardMember Roster",
        )
        PARAMS = dict(
            otherInfo="Yes",
            assistant="Yes",
        )

        def __init__(self, board, row):
            """Capture the caller's information."""

            self.__board = board
            self.__row = row

        def __lt__(self, other):
            """Make members sortable by name."""
            return self.key < other.key

        @property
        def board(self):
            """PDQ board of which this individual is an active member."""
            return self.__board

        @property
        def board_name(self):
            """Name of the member's board, streamlined for the report."""
            return self.board.name.replace("PDQ ", "")

        @property
        def cdrid(self):
            """CDR ID for the membership document."""
            return self.id

        @property
        def control(self):
            """Access to the runtime parameters chose for the report."""
            return self.board.control

        @property
        def doc(self):
            """The `Doc` object for the PDQBoardMemberInfo document."""

            if not hasattr(self, "_doc"):
                self._doc = Doc(self.session, id=self.id)
            return self._doc

        @property
        def email(self):
            """Email address for the board member."""

            if not hasattr(self, "_email"):
                self._email = None
                for node in self.table.iter("email"):
                    self._email = node.text
                    break
            return self._email

        @property
        def fax(self):
            """Fax number for the board member."""

            if not hasattr(self, "_fax"):
                self._fax = None
                for node in self.table.iter("fax"):
                    self._fax = node.text
                    break
            return self._fax

        @property
        def filters(self):
            """Filters used for assembling the member's report information."""

            if not hasattr(self, "_filters"):
                self._filters = list(self.PREP_FILTERS)
                self._filters.append(self.finishing_filter)
            return self._filters

        @property
        def finishing_filter(self):
            """The final filter used on the member for this report."""

            if not hasattr(self, "_finishing_filter"):
                name = self.FINISHING_FILTERS[self.control.report_format]
                self._finishing_filter = f"name:{name}"
            return self._finishing_filter

        @property
        def govt_employee(self):
            """String indicating whether the member is a government employee.
            """

            return self.__row.govt_employee

        @property
        def html(self):
            """Filtered member document."""

            if not hasattr(self, "_html"):
                result = self.doc.filter(*self.filters, parms=self.PARAMS)
                tree = result.result_tree
                self._html = html.fromstring(str(tree))
                for node in self._html:
                    if node.tag == "br" and node.tail == "U.S.A.":
                        self._html.remove(node)
            return self._html

        @property
        def id(self):
            """CDR ID for the membership document."""
            return self.__row.member_id

        @property
        def key(self):
            """Normalized name for sorting."""

            if not hasattr(self, "_key"):
                self._key = self.__row.person_name.lower()
            return self._key

        @property
        def name(self):
            """Board member name (used for the 'summary' report."""

            if not hasattr(self, "_name"):
                b = self.html.find("b")
                self._name = b.text if b is not None else None
            return self._name

        @property
        def phone(self):
            """Phone number for the board member."""

            if not hasattr(self, "_phone"):
                self._phone = None
                for node in self.table.iter("phone"):
                    self._phone = node.text
                    break
            return self._phone

        @property
        def row(self):
            """Values for the tabular ("summary") version of the report."""

            if not hasattr(self, "_row"):
                self._row = [self.name]
                for column in self.control.columns:
                    self.control.logger.debug("column %s", column)
                    value = "" if column == "blank" else getattr(self, column)
                    self._row.append(value)
            return self._row

        @property
        def session(self):
            """Used for creating the `Doc` object for the board member."""
            return self.board.control.session

        @property
        def start_date(self):
            """When the board member's term began."""
            return self.__row.term_start

        @property
        def table(self):
            """Node from which email, fax, and phone values are retrieved."""

            if not hasattr(self, "_table"):
                self._table = self.html.find("table")
            return self._table


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
