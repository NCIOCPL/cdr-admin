#!/usr/bin/env python

"""Track past board member invitations.


 "Creatign a HTML report to help track who had been invited to the
  Boards in the past, what their current (and past) membership statuses
  are, and reasons why they left PDQ. This information will be helpful
  in discussions about inviting new members."
                                           Volker Englisch, 2011-09-23
"""

from functools import cached_property
from cdrcgi import Controller, BasicWebPage
from cdrapi.docs import Doc, Link


class Control(Controller):
    """Contains the top-level logic for this report."""

    SUBTITLE = "PDQ Board Invitation History Report"
    METHOD = "get"
    IACT = "Integrative, Alternative, and Complementary Therapies"
    EXCLUDE_EDITORIAL = "Exclude current members of any editorial board"
    EXCLUDE_ADVISORY = "Exclude current members of any advisory board"
    EXCLUSIONS = EXCLUDE_EDITORIAL, EXCLUDE_ADVISORY
    BOARD_TYPES = "PDQ Editorial Board", "PDQ Advisory Board"
    BLANK_COLUMN = "Blank Column"
    OPTIONAL_COLUMNS = (
        "Board Name",
        "Area of Expertise",
        "Invitation Date",
        "Response to Invitation",
        "Current Member",
        "Termination End Date",
        "Termination Reason",
        BLANK_COLUMN,
    )

    def build_tables(self):
        """Create the meat of the report."""

        # Create one row for each member/board combination. If we have
        # not been asked to display any board-specific columns, only
        # include one row per board member.
        rows = []
        for member in self.members:
            if self.including_board_specific_columns:
                for board in member.boards:
                    row = [
                        self.Reporter.Cell(member.id),
                        self.Reporter.Cell(member.name),
                    ]
                    for name in self.OPTIONAL_COLUMNS:
                        if name in self.optional_columns:
                            if name == self.BLANK_COLUMN:
                                value = ""
                            else:
                                key = name.replace(" ", "_").lower()
                                value = getattr(board, key)
                            row.append(value)
                    rows.append(row)
            else:
                row = [
                    self.Reporter.Cell(member.id),
                    self.Reporter.Cell(member.name),
                ]
                rows.append(row)

        # Assemble the table and return it.
        caption = self.board_names.get(self.board)
        if not caption:
            caption = "PDQ Board Invitation History for All Boards"
        opts = dict(columns=self.columns, caption=caption)
        return self.Reporter.Table(rows, **opts)

    def populate_form(self, page):
        """Add the report control options to the form.

        Pass:
            page - HTMLPage object on which the fields are placed
        """

        fieldset = page.fieldset("Select Board")
        boards = [("all", "All Boards")] + self.boards
        board = self.board or "all"
        for id, name in boards:
            checked = id == board
            opts = dict(value=id, label=name, checked=checked)
            fieldset.append(page.radio_button("board", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Exclusions")
        for exclusion in self.EXCLUSIONS:
            checked = exclusion in self.exclusions
            opts = dict(value=exclusion, label=exclusion, checked=checked)
            fieldset.append(page.checkbox("exclusions", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Optional Columns")
        default_columns = self.OPTIONAL_COLUMNS[0]
        if self.request:
            default_columns = self.optional_columns
        for column in self.OPTIONAL_COLUMNS:
            checked = column in default_columns
            opts = dict(value=column, label=column, checked=checked)
            fieldset.append(page.checkbox("optional", **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Use custom page layout for wider tables."""

        if len(self.columns) > 3:
            report = BasicWebPage()
            report.wrapper.append(report.B.H1(self.subtitle))
            report.wrapper.append(self.build_tables().node)
            report.wrapper.append(self.footer)
            return report.send()
        Controller.show_report(self)

    @cached_property
    def board(self):
        """ID of the board selected for the report (or None for all boards)."""

        try:
            return int(self.fields.getvalue("board"))
        except Exception:
            return None

    @cached_property
    def board_names(self):
        """Dictionary of board names indexed by organization ID."""

        names = {}
        for id, name in self.boards:
            names[id] = name.replace("PDQ ", "")
        return names

    @cached_property
    def boards(self):
        """All active boards in the CDR, as id/title tuples."""

        fields = "d.id", "d.title"
        query = self.Query("active_doc d", *fields).order("d.title")
        query.join("query_term t", "t.doc_id = d.id")
        query.where("t.path = '/Organization/OrganizationType'")
        query.where(query.Condition("t.value", self.BOARD_TYPES, "IN"))
        boards = []
        for id, title in query.execute(self.cursor).fetchall():
            title = title.split(";")[0].strip()
            boards.append((id, title.replace(self.IACT, "IACT")))
        return boards

    @cached_property
    def columns(self):
        # Add the column headers, based on which optional columns we want.

        cols = [
            "ID",
            self.Reporter.Column("Name", width="200px"),
        ]
        widths = {
            "Board Name": 350,
            "Area of Expertise": 250,
            "Response to Invitation": 150,
            "Termination Reason": 200,
        }
        for name in self.OPTIONAL_COLUMNS:
            if name in self.optional_columns:
                if name == self.BLANK_COLUMN:
                    cols.append(self.Reporter.Column("Blank", width="250px"))
                elif "Date" in name:
                    cols.append(self.Reporter.Column(name, width="100px"))
                elif name in widths:
                    width = f"{widths[name]}px"
                    cols.append(self.Reporter.Column(name, width=width))
                else:
                    cols.append(name)
        return cols

    @cached_property
    def exclusions(self):
        """The types of board members to be excluded from the report."""
        return self.fields.getlist("exclusions")

    @cached_property
    def including_board_specific_columns(self):
        """If False, we show only one row per board member."""

        if not self.optional_columns:
            return False
        if self.optional_columns == [self.BLANK_COLUMN]:
            return False
        return True

    @cached_property
    def members(self):
        """Sequence of BoardMember objects in scope for the report."""

        query = self.Query("query_term", "doc_id").unique()
        query.where(query.Condition("path", BoardMember.BOARD))
        if self.board is not None:
            query.where(query.Condition("int_val", self.board))
        else:
            boards = list(self.board_names)
            query.where(query.Condition("int_val", boards, "IN"))
        members = []
        for row in query.execute(self.cursor).fetchall():
            member = BoardMember(self, row.doc_id)
            if member.in_scope:
                members.append(member)
        self.logger.info("collected %d members", len(members))
        return sorted(members)

    @cached_property
    def optional_columns(self):
        """Which optional columns has the user requested?"""
        return self.fields.getlist("optional")


class BoardMember:
    """Information about a PDQ board member and his/her board memberships."""

    BOARD = "/PDQBoardMemberInfo/BoardMembershipDetails/BoardName/@cdr:ref"
    FIRST_NAME = "/Person/PersonNameInformation/GivenName"
    LAST_NAME = "/Person/PersonNameInformation/SurName"
    PERSON = "/PDQBoardMemberInfo/BoardMemberName/@cdr:ref"

    def __init__(self, control, id):
        """Capture the caller's information; let properties do the real work.

        Pass:
            control - provides access to runtime options and the database
            id - CDR ID for the PDQBoardMemberInfo document
            boards - integers for the member's boards
        """
        self.__control = control
        self.__id = id

    def __lt__(self, other):
        """Make the board member objects sortable by member name."""
        return self.name.lower() < other.name.lower()

    @cached_property
    def boards(self):
        """Board objects for PDQ board to which this member has belonged."""

        boards = []
        for node in self.doc.root.findall("BoardMembershipDetails"):
            boards.append(self.Board(self, node))
        return boards

    @cached_property
    def control(self):
        """Access to the database and the runtime options."""
        return self.__control

    @cached_property
    def cursor(self):
        """Access to the database."""
        return self.__control.cursor

    @cached_property
    def doc(self):
        """The PDQBoardMemberInfo document for this board member."""
        return Doc(self.session, id=self.id)

    @cached_property
    def id(self):
        """CDR ID for this member's PDQBoardMemberInfo document."""
        return self.__id

    @cached_property
    def in_scope(self):
        """Boolean indicating whether this board member should be included."""

        if not self.boards or not self.name:
            return False
        if not self.control.exclusions:
            return True
        exclusions = self.control.exclusions
        for board in self.boards:
            if board.current:
                if "advisory" in board.name.lower():
                    if self.control.EXCLUDE_ADVISORY in exclusions:
                        return False
                else:
                    if self.control.EXCLUDE_EDITORIAL in exclusions:
                        return False
        return True

    @cached_property
    def name(self):
        """Board member's name in Surname, Given Name format."""

        query = self.control.Query("query_term g", "g.value", "s.value")
        query.join("query_term s", "s.doc_id = g.doc_id")
        query.join("query_term p", "p.int_val = g.doc_id")
        query.where(query.Condition("p.path", self.PERSON))
        query.where(query.Condition("g.path", self.FIRST_NAME))
        query.where(query.Condition("s.path", self.LAST_NAME))
        query.where(query.Condition("p.doc_id", self.id))
        rows = query.execute(self.cursor).fetchall()
        if rows:
            return f"{rows[0][1].strip()}, {rows[0][0].strip()}"
        return None

    @cached_property
    def session(self):
        """Login session for the user running the report."""
        return self.control.session

    class Board:
        """Information about a board member's membership in a PDQ board."""

        NAME = "/Organization/OrganizationNameInformation/OfficialName/Name"

        def __init__(self, member, node):
            """Remember the caller's information.

            Let @properties do the real work.

            Pass:
                member - `BoardMember` object for this membership
                node - portion of the PDQBoardMemberInfo document for this
                       board membership
            """

            self.__member = member
            self.__node = node

        @cached_property
        def control(self):
            """Access to the database, runtime parameters, logging, etc."""
            return self.member.control

        @cached_property
        def cursor(self):
            """Access to the database."""
            return self.control.cursor

        @cached_property
        def member(self):
            """Access to the `BoardMember` object."""
            return self.__member

        @cached_property
        def node(self):
            """Portion of the member info document for this membership."""
            return self.__node

        @cached_property
        def id(self):
            """CDR ID for the board's Organization document."""

            value = self.node.find("BoardName").get(Link.CDR_REF)
            return Doc.extract_id(value)

        @cached_property
        def name(self):
            """The string for this PDQ board's name."""
            return self.control.board_names.get(self.id)

        @cached_property
        def board_name(self):
            """Alias for name.

            Needed for hooking into the automatic lookup for column values.
            """

            return self.name

        @cached_property
        def area_of_expertise(self):
            """Expertise applicable to membership on this board."""

            areas = []
            for child in self.node.findall("AreaOfExpertise"):
                area = Doc.get_text(child, "").strip()
                if area:
                    areas.append(area)
            return ", ".join(areas)

        @cached_property
        def current(self):
            """Boolean indicating whether the membership is still active."""
            return self.current_member == "Yes"

        @cached_property
        def current_member(self):
            """String value displayed in the Current Member column."""
            return Doc.get_text(self.node.find("CurrentMember"), "Unknown")

        @cached_property
        def invitation_date(self):
            """Date the member was invited to join the board, if known."""
            return Doc.get_text(self.node.find("InvitationDate"), "Unknown")

        @cached_property
        def response_to_invitation(self):
            """How the prospective board member replied to the invitation."""
            return Doc.get_text(self.node.find("ResponseToInvitation"), "None")

        @cached_property
        def termination_end_date(self):
            """When the member's participation ended, if applicable."""

            child = self.node.find("TerminationDate")
            default = "N/A" if self.current else "None"
            return Doc.get_text(child, default)

        @cached_property
        def termination_reason(self):
            """Why the membership ended, if applicable."""

            child = self.node.find("TerminationReason")
            default = "N/A" if self.current else "None"
            return Doc.get_text(child, default)


if __name__ == "__main__":
    "Don't execute the script if loaded as a module."""
    Control().run()
