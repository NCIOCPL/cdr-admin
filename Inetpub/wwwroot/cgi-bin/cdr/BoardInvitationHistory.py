#!/usr/bin/env python

"""Track past board member invitations.


 "Creatign a HTML report to help track who had been invited to the
  Boards in the past, what their current (and past) membership statuses
  are, and reasons why they left PDQ. This information will be helpful
  in discussions about inviting new members."
                                           Volker Englisch, 2011-09-23
"""

from cdrcgi import Controller
from cdrapi.docs import Doc, Link

class Control(Controller):
    """Contains the top-level logic for this report."""

    SUBTITLE = "PDQ Board Invitation History Report"
    METHOD = "get"
    IACT = "Integrative, Alternative, and Complementary Therapies"
    EXCLUDE_EDITORIAL = "Exclude current editorial board members"
    EXCLUDE_ADVISORY = "Exclude current advisory board members"
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

        # Add the column headers, based on which optional columns we want.
        cols = ["ID", "Name"]
        for name in self.OPTIONAL_COLUMNS:
            if name in self.optional_columns:
                if name == self.BLANK_COLUMN:
                    cols.append(self.Reporter.Column("Blank", width="250px"))
                elif "Date" in name:
                    cols.append(self.Reporter.Column(name, width="75px"))
                else:
                    cols.append(name)

        # Create one row for each member/board combination. If we have
        # not been asked to display any board-specific columns, only
        # include one row per board member.
        rows = []
        for member in self.members:
            row = row_start = [
                self.Reporter.Cell(member.id, center=True),
                self.Reporter.Cell(member.name)
            ]
            if self.including_board_specific_columns:
                for board in member.boards:
                    row = list(row_start)
                    for name in self.OPTIONAL_COLUMNS:
                        if name in self.optional_columns:
                            if name == self.BLANK_COLUMN:
                                value = ""
                            else:
                                key = name.replace(" ", "_").lower()
                                value = getattr(board, key)
                            row.append(value)
            rows.append(row)

        # Assemble the table and return it.
        caption = self.board_names.get(self.board)
        if not caption:
            caption = "PDQ Board Invitation History for All Boards"
        opts = dict(columns=cols, caption=caption)
        return self.Reporter.Table(rows, **opts)

    def populate_form(self, page):
        """Add the report control options to the form.

        Pass:
            page - HTMLPage object on which the fields are placed
        """

        fieldset = page.fieldset("Select Board")
        boards = [("all", "All Boards")] + self.boards
        checked = True
        for id, name in boards:
            opts = dict(value=id, label=name, checked=checked)
            fieldset.append(page.radio_button("board", **opts))
            checked = False
        page.form.append(fieldset)
        fieldset = page.fieldset("Exclusions")
        opts = dict(value=self.EXCLUDE_EDITORIAL, label=self.EXCLUDE_EDITORIAL)
        fieldset.append(page.checkbox("exclusions", **opts))
        opts = dict(value=self.EXCLUDE_ADVISORY, label=self.EXCLUDE_ADVISORY)
        fieldset.append(page.checkbox("exclusions", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Optional Columns")
        checked = True
        for column in self.OPTIONAL_COLUMNS:
            opts = dict(value=column, label=column, checked=checked)
            fieldset.append(page.checkbox("optional", **opts))
            checked = False
        page.form.append(fieldset)

    @property
    def board(self):
        """ID of the board selected for the report (or None for all boards)."""

        if not hasattr(self, "_board"):
            board = self.fields.getvalue("board")
            try:
                self._board = int(board)
            except:
                self._board = None
        return self._board

    @property
    def board_names(self):
        """Dictionary of board names indexed by organization ID."""

        if not hasattr(self, "_board_names"):
            self._board_names = {}
            for id, name in self.boards:
                self._board_names[id] = name.replace("PDQ ", "")
        return self._board_names

    @property
    def boards(self):
        """All active boards in the CDR, as id/title tuples."""

        if not hasattr(self, "_boards"):
            fields = "d.id", "d.title"
            query = self.Query("active_doc d", *fields).order("d.title")
            query.join("query_term t", "t.doc_id = d.id")
            query.where("t.path = '/Organization/OrganizationType'")
            query.where(query.Condition("t.value", self.BOARD_TYPES, "IN"))
            self._boards = []
            for id, title in query.execute(self.cursor).fetchall():
                title = title.split(";")[0].strip()
                self._boards.append((id, title.replace(self.IACT, "IACT")))
        return self._boards

    @property
    def exclusions(self):
        """The types of board members to be excluded from the report."""
        return self.fields.getlist("exclusions")

    @property
    def including_board_specific_columns(self):
        """If False, we show only one row per board member."""

        if not self.optional_columns:
            return False
        if self.optional_columns == [self.BLANK_COLUMN]:
            return False
        return True

    @property
    def members(self):
        """Sequence of BoardMember objects in scope for the report."""

        if not hasattr(self, "_members"):
            self._members = BoardMember.get_members(self)
        return self._members

    @property
    def optional_columns(self):
        """Which optional columns has the user requested?"""
        return self.fields.getlist("optional")


class BoardMember:
    """Information about a PDQ board member and his/her board memberships."""

    BOARD = "/PDQBoardMemberInfo/BoardMembershipDetails/BoardName/@cdr:ref"
    FIRST_NAME = "/Person/PersonNameInformation/GivenName"
    LAST_NAME = "/Person/PersonNameInformation/SurName"
    PERSON = "/PDQBoardMemberInfo/BoardMemberName/@cdr:ref"

    def __init__(self, control, id, boards):
        """Capture the caller's information; let properties do the real work.

        Pass:
            control - provides access to runtime options and the database
            id - CDR ID for the PDQBoardMemberInfo document
            boards - integers for the member's boards
        """
        self.__control = control
        self.__id = id
        self.__boards = boards

    def __lt__(self, other):
        """Make the board member objects sortable by member name."""
        return self.name.lower() < other.name.lower()

    @property
    def boards(self):
        """Board objects for PDQ board to which this member has belonged."""

        if not hasattr(self, "_boards"):
            self._boards = []
            for node in self.doc.root.findall("BoardMembershipDetails"):
                board = self.Board(self, node)
                if board.id in self.__boards:
                    self._boards.append(board)
        return self._boards

    @property
    def control(self):
        """Access to the database and the runtime options."""
        return self.__control

    @property
    def cursor(self):
        """Access to the database."""
        return self.__control.cursor

    @property
    def doc(self):
        """The PDQBoardMemberInfo document for this board member."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.session, id=self.id)
        return self._doc

    @property
    def id(self):
        """CDR ID for this member's PDQBoardMemberInfo document."""
        return self.__id

    @property
    def in_scope(self):
        """Boolean indicating whether this board member should be included."""

        if not hasattr(self, "_in_scope"):
            self._in_scope = True if self.boards and self.name else False
            exclusions = self.control.exclusions
            if self._in_scope and exclusions:
                for board in self.boards:
                    if "advisory" in board.name.lower():
                        if self.control.EXCLUDE_EDITORIAL in exclusions:
                            self._in_scope = False
                            break
                    else:
                        if self.control.EXCLUDE_ADVISORY in exclusions:
                            self._in_scope = False
                            break
        return self._in_scope

    @property
    def name(self):
        """Board member's name in Surname, Given Name format."""

        if not hasattr(self, "_name"):
            query = self.control.Query("query_term g", "g.value", "s.value")
            query.join("query_term s", "s.doc_id = g.doc_id")
            query.join("query_term p", "p.int_val = g.doc_id")
            query.where(query.Condition("p.path", self.PERSON))
            query.where(query.Condition("g.path", self.FIRST_NAME))
            query.where(query.Condition("s.path", self.LAST_NAME))
            query.where(query.Condition("p.doc_id", self.id))
            rows = query.execute(self.cursor).fetchall()
            if not rows:
                self._name = None
            else:
                self._name = f"{rows[0][1].strip()}, {rows[0][0].strip()}"
        return self._name

    @property
    def session(self):
        """Login session for the user running the report."""
        return self.control.session

    @classmethod
    def get_members(cls, control):
        """Get the board members in scope for this report.

        Pass:
            control - access to the database and the report parameters

        Return:
            sequence of `BoardMember` objects
        """

        query = control.Query("query_term", "doc_id", "int_val")
        query.where(query.Condition("path", cls.BOARD))
        if control.board is not None:
            query.where(query.Condition("int_val", control.board))
        else:
            boards = list(control.board_names)
            query.where(query.Condition("int_val", boards, "IN"))
        members = {}
        for member_id, board_id in query.execute(control.cursor):
            if member_id not in members:
                members[member_id] = [board_id]
            else:
                members[member_id].append(board_id)
        result = []
        for item in members.items():
            member = cls(control, *item)
            if member.in_scope:
                result.append(member)
        return sorted(result)


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

        @property
        def control(self):
            """Access to the database, runtime parameters, logging, etc."""
            return self.member.control

        @property
        def cursor(self):
            """Access to the database."""
            return self.control.cursor

        @property
        def member(self):
            """Access to the `BoardMember` object."""
            return self.__member

        @property
        def node(self):
            """Portion of the member info document for this membership."""
            return self.__node

        @property
        def id(self):
            """CDR ID for the board's Organization document."""

            if not hasattr(self, "_id"):
                value = self.node.find("BoardName").get(Link.CDR_REF)
                self._id = Doc.extract_id(value)
            return self._id

        @property
        def name(self):
            """The string for this PDQ board's name."""

            if not hasattr(self, "_name"):
                self._name = self.control.board_names.get(self.id)
            return self._name

        @property
        def board_name(self):
            """Alias for name.

            Needed for hooking into the automatic lookup for column values.
            """

            return self.name

        @property
        def area_of_expertise(self):
            """Expertise applicable to membership on this board."""

            if not hasattr(self, "_area_of_expertise"):
                areas = []
                for child in self.node.findall("AreaOfExpertise"):
                    area = Doc.get_text(child, "").strip()
                    if area:
                        areas.append(area)
                self._area_of_expertise = ", ".join(areas)
            return self._area_of_expertise

        @property
        def current(self):
            """Boolean indicating whether the membership is still active."""
            return self.current_member == "Yes"

        @property
        def current_member(self):
            """String value displayed in the Current Member column."""

            if not hasattr(self, "_current_member"):
                child = self.node.find("CurrentMember")
                self._current_member = Doc.get_text(child, "Unknown")
            return self._current_member

        @property
        def invitation_date(self):
            """Date the member was invited to join the board, if known."""

            if not hasattr(self, "_invitation_date"):
                child = self.node.find("InvitationDate")
                self._invitation_date = Doc.get_text(child, "Unknown")
            return self._invitation_date

        @property
        def response_to_invitation(self):
            """How the prospective board member replied to the invitation."""

            if not hasattr(self, "_response_to_invitation"):
                child = self.node.find("ResponseToInvitation")
                self._response_to_invitation = Doc.get_text(child, "None")
            return self._response_to_invitation

        @property
        def termination_end_date(self):
            """When the member's participation ended, if applicable."""

            if not hasattr(self, "_termination_date"):
                child = self.node.find("TerminationDate")
                default = "N/A" if self.current else "None"
                self._termination_date = Doc.get_text(child, default)
            return self._termination_date

        @property
        def termination_reason(self):
            """Why the membership ended, if applicable."""

            if not hasattr(self, "_termination_reason"):
                child = self.node.find("TerminationReason")
                default = "N/A" if self.current else "None"
                self._termination_reason = Doc.get_text(child, default)
            return self._termination_reason


if __name__ == "__main__":
    "Don't execute the script if loaded as a module."""
    Control().run()
