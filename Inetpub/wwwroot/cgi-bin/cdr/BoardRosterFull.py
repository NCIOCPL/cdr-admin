#!/usr/bin/env python

"""Display the Board Roster with or without assistant information.
"""

from functools import cached_property
from lxml import html
from cdrcgi import Controller, BasicWebPage
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
        phone="175px;",
        fax="120px;",
        start_date="100px;",
        blank="100px;",
    )
    COLUMN_OVERRIDES = dict(
        govt_employee="Gov. Empl",
        blank="Blank",
    )

    def build_tables(self):
        """Create table(s) for the "summary" version of the report."""

        if self.format == "full":
            self.show_full_report()
        else:
            opts = dict(columns=self.headers)
            if self.grouping == "by_member":
                rows = []
                for member in self.members:
                    rows.append(member.row)
                opts["caption"] = self.caption
                return [self.Reporter.Table(rows, **opts)]
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

        opts = dict(
            subtitle=self.subtitle,
            session=self.session,
            control=self,
            suppress_sidenav=True,
        )
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

    def show_report(self):
        "Use custom layout for wider tables."

        if len(self.headers) > 3:
            report = BasicWebPage()
            report.wrapper.append(report.B.H1(self.subtitle))
            for table in self.build_tables():
                report.wrapper.append(table.node)
            report.wrapper.append(self.footer)
            return report.send()
        Controller.show_report(self)

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

    @cached_property
    def boards(self):
        """All active PDQ boards of the selected type."""

        boards = []
        board_type = f"PDQ {self.board_type.title()} Board"
        query = self.Query("active_doc b", "b.id", "b.title")
        query.join("query_term t", "t.doc_id = b.id")
        query.where("t.path = '/Organization/OrganizationType'")
        query.where(query.Condition("t.value", board_type))
        for row in query.execute(self.cursor).fetchall():
            boards.append(Board(self, row))
        return sorted(boards)

    @cached_property
    def board_type(self):
        """Board type (advisory or editorial) selected for the report."""
        return self.fields.getvalue("board_type")

    @cached_property
    def caption(self):
        """Default caption for the tabular report."""
        return f"PDQ {self.board_type.title()} Board Member Roster"

    @cached_property
    def columns(self):
        """Optional columns which have been selected for the tabular report."""
        return self.fields.getlist("column")

    @cached_property
    def grouping(self):
        """Grouping ("by_member" or "by_board") chosen for the report."""
        return self.fields.getvalue("grouping")

    @cached_property
    def headers(self):
        """Column headers for the tabular ("summary") report."""

        headers = ["Board Member"]
        for name, display, _ in self.OPTIONAL_COLUMNS:
            if name in self.columns:
                header = self.COLUMN_OVERRIDES.get(name, display)
                width = self.WIDTHS.get(name)
                if width is not None:
                    header = self.Reporter.Column(header, width=width)
                headers.append(header)
        return headers

    @cached_property
    def members(self):
        """All active members of board of the selected type."""

        members = []
        for board in self.boards:
            members += board.members
        return sorted(members)

    @cached_property
    def format(self):
        """Selected flavor of the report ("full" or "summary")."""
        return self.fields.getvalue("format")


class Board:
    """One advisory or editorial PDQ board."""

    DETAILS = "/PDQBoardMemberInfo/BoardMembershipDetails"
    BOARD_PATH = f"{DETAILS}/BoardName/@cdr:ref"
    CURRENT_PATH = f"{DETAILS}/CurrentMember"
    TERM_START_PATH = f"{DETAILS}/TermStartDate"
    GOVT_EMPLOYEE_PATH = "/PDQBoardMemberInfo/GovernmentEmployee"
    PERSON_PATH = "/PDQBoardMemberInfo/BoardMemberName/@cdr:ref"
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

    @cached_property
    def control(self):
        """Access to the database and the runtime report parameters."""
        return self.__control

    @cached_property
    def fields(self):
        """Values which need to be fetched from the database for this board."""
        return self.FIELDS[self.control.format]

    @cached_property
    def id(self):
        """CDR document ID for the board's Organization document."""
        return self.__row.id

    @cached_property
    def name(self):
        """Board name, tailored for display in the report."""

        title = self.__row.title.replace(self.IACT, "IACT")
        return title.split(";")[0].strip()

    @cached_property
    def members(self):
        """Sorted sequence of `Member` objects for this PDQ board."""

        query = self.control.Query("query_term m", *self.fields).unique()
        query.where(query.Condition("m.path", self.BOARD_PATH))
        query.where(query.Condition("m.int_val", self.id))
        query.join("query_term c", "c.doc_id = m.doc_id",
                   "LEFT(c.node_loc, 4) = LEFT(m.node_loc, 4)")
        query.where(query.Condition("c.path", self.CURRENT_PATH))
        query.where("c.value = 'Yes'")
        query.join("query_term p", "p.doc_id = m.doc_id")
        query.where(query.Condition("p.path", self.PERSON_PATH))
        query.join("active_doc d", "d.id = p.int_val")
        if self.control.format == "summary":
            query.join("query_term g", "g.doc_id = m.doc_id")
            query.where(query.Condition("g.path", self.GOVT_EMPLOYEE_PATH))
            query.outer("query_term t", "t.doc_id = m.doc_id",
                        "LEFT(t.node_loc, 4) = LEFT(m.node_loc, 4)",
                        f"t.path = '{self.TERM_START_PATH}'")
        members = []
        for row in query.execute(self.control.cursor).fetchall():
            members.append(self.Member(self, row))
        return sorted(members)

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

        @cached_property
        def board(self):
            """PDQ board of which this individual is an active member."""
            return self.__board

        @cached_property
        def board_name(self):
            """Name of the member's board, streamlined for the report."""
            return self.board.name.replace("PDQ ", "")

        @cached_property
        def cdrid(self):
            """CDR ID for the membership document."""
            return self.id

        @cached_property
        def control(self):
            """Access to the runtime parameters chose for the report."""
            return self.board.control

        @cached_property
        def doc(self):
            """The `Doc` object for the PDQBoardMemberInfo document."""
            return Doc(self.session, id=self.id)

        @cached_property
        def email(self):
            """Email address for the board member."""

            for node in self.table.iter("email"):
                return node.text
            return None

        @cached_property
        def fax(self):
            """Fax number for the board member."""

            for node in self.table.iter("fax"):
                return node.text
            return None

        @cached_property
        def filters(self):
            """Filters used for assembling the member's report information."""

            filters = list(self.PREP_FILTERS)
            filters.append(self.finishing_filter)
            return filters

        @cached_property
        def finishing_filter(self):
            """The final filter used on the member for this report."""
            return f"name:{self.FINISHING_FILTERS[self.control.format]}"

        @cached_property
        def govt_employee(self):
            """'Yes' if the member is a government employee."""
            return self.__row.govt_employee

        @cached_property
        def html(self):
            """Filtered member document."""

            self.control.logger.info("filtering %s", self.doc.cdr_id)
            result = self.doc.filter(*self.filters, parms=self.PARAMS)
            html_root = html.fromstring(str(result.result_tree))
            for node in html_root:
                if node.tag == "br" and node.tail == "U.S.A.":
                    html_root.remove(node)
            return html_root

        @cached_property
        def id(self):
            """CDR ID for the membership document."""
            return self.__row.member_id

        @cached_property
        def key(self):
            """Normalized name for sorting."""
            return self.__row.person_name.lower()

        @cached_property
        def name(self):
            """Board member name (used for the 'summary' report."""

            b = self.html.find("b")
            return b.text if b is not None else None

        @cached_property
        def phone(self):
            """Phone number for the board member."""

            for node in self.table.iter("phone"):
                return node.text
            return None

        @cached_property
        def row(self):
            """Values for the tabular ("summary") version of the report."""

            row = [self.name]
            for column in self.control.columns:
                self.control.logger.debug("column %s", column)
                value = "" if column == "blank" else getattr(self, column)
                if value and column == "start_date":
                    value = value.replace("-", Control.NONBREAKING_HYPHEN)
                row.append(value)
            return row

        @cached_property
        def session(self):
            """Used for creating the `Doc` object for the board member."""
            return self.board.control.session

        @cached_property
        def start_date(self):
            """When the board member's term began."""
            return self.__row.term_start

        @cached_property
        def table(self):
            """Node from which email, fax, and phone values are retrieved."""
            return self.html.find("table")


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
