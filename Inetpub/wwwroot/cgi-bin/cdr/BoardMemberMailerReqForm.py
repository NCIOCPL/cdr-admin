#!/usr/bin/env python

"""Request form for generating RTF letters to board members.
"""

from functools import cached_property
from json import dumps, loads
from cdr import getControlValue
from cdrcgi import Controller
from cdrapi.docs import Doc
from cdrapi.publishing import Job


class Control(Controller):
    """Logic for generating board member mailer letters."""

    LOGNAME = "mailer"
    SUBTITLE = "PDQ Board Member Correspondence Mailers"
    SYSTEM = "Mailers"
    SUBSYSTEM = "PDQ Board Member Correspondence Mailer"
    LETTERS = "board-member-letters"
    STATUS_PAGE = "Status Page"

    def populate_form(self, page):
        """Add the parameters for mailer generation.

        Pass:
            page - HTMLPage object to which we add the form fields.
        """

        page.form.append(page.B.P(
            "Note: Invitation letters for prospective Pediatric Treatment "
            "editorial board members cannot be generated from this interface.",
            page.B.CLASS("error")
        ))
        fieldset = page.fieldset("Board")
        fieldset.set("id", "boards")
        checked = True
        for board in self.boards:
            opts = dict(value=board.id, label=board.name, checked=checked)
            fieldset.append(page.radio_button("board", **opts))
            checked = False
        page.form.append(fieldset)
        fieldset = page.fieldset("Letter")
        fieldset.set("id", "letters")
        page.form.append(fieldset)
        fieldset = page.fieldset("Board Members")
        fieldset.set("id", "members")
        page.form.append(fieldset)
        fieldset = page.fieldset("Notification")
        opts = dict(value=self.user.email)
        fieldset.append(page.text_field("email", **opts))
        page.form.append(fieldset)
        page.add_script(f"var boards = {self.boards.json};")
        page.add_script(f"var letters = {self.letters_json};")
        page.head.append(page.B.SCRIPT(src="/js/BoardMemberMailerReqForm.js"))

    def show_report(self):
        """Overridden so we can create the mailers."""

        if self.request == self.STATUS_PAGE:
            return self.redirect("PubStatus.py", id=self.job_id)
        opts = dict(
            system=self.SYSTEM,
            subsystem=self.SUBSYSTEM,
            parms=self.parms,
            docs=self.docs,
            email=self.email,
            permissive=True,
        )
        try:
            job = Job(self.session, **opts)
            job.create()
        except Exception as e:
            self.logger.exception("Mailer creation failed")
            self.bail(str(e))
        opts = dict(
            action=self.script,
            subtitle=self.subtitle,
            session=self.session,
        )
        page = self.HTMLPage(self.title, **opts)
        legend = f"Queued {len(self.recipients)} Mailer(s)"
        fieldset = page.fieldset(legend)
        ul = page.B.UL()
        for recipient in self.recipients:
            ul.append(page.B.LI(recipient))
        fieldset.append(ul)
        page.form.append(fieldset)
        button = self.form_page.button(self.STATUS_PAGE)
        page.form.append(button)
        page.form.append(page.hidden_field("job-id", job.id))
        page.send()

    @cached_property
    def board(self):
        """Which board was selected?"""
        return self.fields.getvalue("board")

    @cached_property
    def boards(self):
        """All active boards in the CDR, as id/title tuples."""
        return Boards(self)

    @cached_property
    def board_members(self):
        """Dictionary of all active PDQ board members in the CDR."""

        path = "/PDQBoardMemberInfo/BoardMemberName/@cdr:ref"
        query = self.Query("active_doc d", "p.doc_id", "d.title")
        query.join("query_term p", "p.int_val = d.id")
        query.where(f"p.path = '{path}'")
        board_members = {}
        for id, title in query.execute(self.cursor):
            title = title.split(";")[0].strip()
            if title.lower() != "inactive":
                board_members[id] = title
        return board_members

    @cached_property
    def docs(self):
        """Sequence of `Doc` objects for the selected board members."""

        docs = []
        for member_id in self.selected_members:
            doc = Doc(self.session, id=member_id, version="lastv")
            docs.append(doc)
        return docs

    @cached_property
    def email(self):
        """Where should we send the notification?"""
        return self.fields.getvalue("email")

    @cached_property
    def job_id(self):
        """The ID of the job we just created."""
        return self.fields.getvalue("job-id")

    @cached_property
    def letter(self):
        """Machine name for the type of letter to be sent."""
        return self.fields.getvalue("letter")

    @cached_property
    def letters(self):
        """Display names for letter types indexed by machine names."""

        letters = {}
        for letter_type in ("advisory", "editorial"):
            for name, key in loads(self.letters_json)[letter_type]:
                letters[key] = name
        return letters

    @cached_property
    def letters_json(self):
        """Letter type information usable by client-side scripting."""
        return getControlValue("Mailers", self.LETTERS)

    @cached_property
    def parms(self):
        """Parameters to be fed to the publishing job."""
        return dict(Board=self.board, Letter=self.letter)

    @cached_property
    def recipients(self):
        """Sorted sequence of selected board member names."""

        recipients = []
        for member_id in self.selected_members:
            recipients.append(self.board_members[member_id])
        return sorted(recipients, key=str.lower)

    @cached_property
    def selected_members(self):
        """Document IDs for the board members which have been chosen."""

        members = []
        for id in self.fields.getlist("member"):
            if id.isdigit():
                members.append(int(id))
        return members

    @cached_property
    def user(self):
        """Object for the currently logged-on CDR user."""

        opts = dict(id=self.session.user_id)
        return self.session.User(self.session, **opts)


class Boards:
    """Collection of all of the active PDQ boards."""

    IACT = "Integrative, Alternative, and Complementary Therapies"
    BOARD_TYPES = "PDQ Editorial Board", "PDQ Advisory Board"

    @cached_property
    def json(self):
        """Information about the board in a form client-side scripting uses."""

        boards = {}
        for board in self.boards:
            members = [(m.id, m.name) for m in board.members]
            values = dict(
                id=board.id,
                type=board.type,
                members=members
            )
            boards[board.id] = values
        return dumps(boards, indent=2)

    def __init__(self, control):
        """Save the control object, and let properties do the heavy lifting."""
        self.__control = control

    def __len__(self):
        """Support Boolean testing."""
        return len(self.boards)

    def __iter__(self):
        """Allow this object to be used like an iterable sequence."""

        class Iter:
            def __init__(self, boards):
                self.__index = 0
                self.__boards = boards

            def __next__(self):
                if self.__index >= len(self.__boards):
                    raise StopIteration
                board = self.__boards[self.__index]
                self.__index += 1
                return board
        return Iter(self.boards)

    @cached_property
    def control(self):
        """Access to the database cursor."""
        return self.__control

    @cached_property
    def cursor(self):
        """Access to the database."""
        return self.control.cursor

    @cached_property
    def boards(self):
        """Assemble the sequence of `Board` objects."""

        fields = "d.id", "d.title"
        query = self.control.Query("active_doc d", *fields)
        query.order("d.title")
        query.join("query_term t", "t.doc_id = d.id")
        query.where("t.path = '/Organization/OrganizationType'")
        query.where(query.Condition("t.value", self.BOARD_TYPES, "IN"))
        boards = []
        for id, title in query.execute(self.cursor).fetchall():
            title = title.split(";")[0].strip()
            title = title.replace(self.IACT, "IACT")
            boards.append(self.Board(self.control, id, title))
        return boards

    class Board:
        """Information about a PDQ board and its members."""

        BOARD = "/PDQBoardMemberInfo/BoardMembershipDetails/BoardName/@cdr:ref"

        def __init__(self, control, id, name):
            """Remember the caller's values, let the properties do the work.

            Pass:
                control - access to the database
                id - primary key for the board's Organization CDR document
                name - string for the name of the board
            """

            self.__control = control
            self.__id = id
            self.__name = name

        @cached_property
        def control(self):
            """Access to the database cursor."""
            return self.__control

        @cached_property
        def cursor(self):
            """Access to the database."""
            return self.control.cursor

        @cached_property
        def id(self):
            """Primary key for the board's Organization CDR document."""
            return self.__id

        @cached_property
        def name(self):
            """String for the name of the board."""
            return self.__name

        @cached_property
        def members(self):
            """Sorted sequence of the board's members."""

            query = self.control.Query("active_doc d", "d.id").unique()
            query.join("query_term m", "m.doc_id = d.id")
            query.where(query.Condition("m.path", self.BOARD))
            query.where(query.Condition("m.int_val", self.id))
            members = []
            for row in query.execute(self.cursor).fetchall():
                member = self.Member(self, row.id)
                if member.name:
                    members.append(member)
            return sorted(members)

        @cached_property
        def type(self):
            """String for the board's type ("advisory" or "editorial")."""

            if "advisory" in self.name.lower():
                return "advisory"
            return "editorial"

        class Member:
            """One of the members of a PDQ board."""

            def __init__(self, board, id):
                """Save the caller's values."""
                self.__board = board
                self.__id = id

            def __lt__(self, other):
                """Make the board member objects sortable by member name."""
                return self.name.lower() < other.name.lower()

            @cached_property
            def id(self):
                """Primary key for the member's PDQBoardMemberInfo doc."""
                return self.__id

            @cached_property
            def board(self):
                """Access to the `Control` object."""
                return self.__board

            @cached_property
            def name(self):
                """Board member's name in Surname, Given Name format."""
                return self.board.control.board_members.get(self.id)


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
