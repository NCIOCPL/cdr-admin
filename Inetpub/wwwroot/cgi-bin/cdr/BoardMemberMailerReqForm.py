#!/usr/bin/env python

"""Request form for generating RTF letters to board members.
"""

from json import dumps, loads
from cdr import getControlValue
from cdrcgi import Controller, navigateTo
from cdrapi.docs import Doc
from cdrapi.publishing import Job


class Control(Controller):
    """Logic for generating board member mailer letters."""

    LOGNAME = "mailer"
    SUBTITLE = "PDQ Board Member Correspondence Mailers"
    SYSTEM = "Mailers"
    SUBMENU = "Mailers"
    SUBSYSTEM = "PDQ Board Member Correspondence Mailer"
    LETTERS = "board-member-letters"

    def build_tables(self):
        """Create the publishing job and list the mailer recipients."""

    def populate_form(self, page):
        """Add the parameters for mailer generation.

        Pass:
            page - HTMLPage object to which we add the form fields.
        """

        fieldset = page.fieldset("Note")
        fieldset.append(page.B.P(
            "Invitation letter for prospective Pediatric Treatment "
            "editorial board members cannot be generated from the interface."
        ))
        page.form.append(fieldset)
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

    def run(self):
        """Override to handle routing to Mailers menu."""

        if self.request == self.SUBMENU:
            navigateTo("Mailers.py", self.session.name)
        else:
            Controller.run(self)

    def show_report(self):
        """Overridden so we can create the mailers."""

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
        buttons = (
            self.HTMLPage.button("Status Page", onclick="show_status()"),
            self.HTMLPage.button(self.SUBMENU),
            self.HTMLPage.button(self.ADMINMENU),
            self.HTMLPage.button(self.LOG_OUT),
        )
        opts = dict(
            action=self.script,
            buttons=buttons,
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
        page.add_script(f"""\
function show_status() {{
    window.open("PubStatus.py?id={job.id}", "status-{job.id}");
}}""")
        page.send()

    @property
    def board(self):
        """Which board was selected?"""
        return self.fields.getvalue("board")

    @property
    def boards(self):
        """All active boards in the CDR, as id/title tuples."""

        if not hasattr(self, "_boards"):
            self._boards = Boards(self)
        return self._boards

    @property
    def board_members(self):
        """Dictionary of all active PDQ board members in the CDR."""
        if not hasattr(self, "_board_members"):
            path = "/PDQBoardMemberInfo/BoardMemberName/@cdr:ref"
            query = self.Query("active_doc d", "p.doc_id", "d.title")
            query.join("query_term p", "p.int_val = d.id")
            query.where(f"p.path = '{path}'")
            self._board_members = {}
            for id, title in query.execute(self.cursor):
                title = title.split(";")[0].strip()
                if title.lower() != "inactive":
                    self._board_members[id] = title
        return self._board_members

    @property
    def docs(self):
        """Sequence of `Doc` objects for the selected board members."""

        if not hasattr(self, "_docs"):
            self._docs = []
            for member_id in self.selected_members:
                doc = Doc(self.session, id=member_id, version="lastv")
                self._docs.append(doc)
        return self._docs

    @property
    def email(self):
        """Where should we send the notification?"""
        return self.fields.getvalue("email")

    @property
    def letter(self):
        """Machine name for the type of letter to be sent."""
        return self.fields.getvalue("letter")

    @property
    def letters(self):
        """Display names for letter types indexed by machine names."""

        if not hasattr(self, "_letters"):
            self._letters = {}
            for letter_type in ("advisory", "editorial"):
                for name, key in loads(self.letters_json)[letter_type]:
                    self._letters[key] = name
        return self._letters

    @property
    def letters_json(self):
        """Letter type information usable by client-side scripting."""

        if not hasattr(self, "_letters_json"):
            self._letters_json = getControlValue("Mailers", self.LETTERS)
        return self._letters_json

    @property
    def parms(self):
        """Parameters to be fed to the publishing job."""
        return dict(Board=self.board, Letter=self.letter)

    @property
    def recipients(self):
        """Sorted sequence of selected board member names."""

        if not hasattr(self, "_recipients"):
            recipients = []
            for member_id in self.selected_members:
                recipients.append(self.board_members[member_id])
            self._recipients = sorted(recipients, key=str.lower)
        return self._recipients

    @property
    def selected_members(self):
        """Document IDs for the board members which have been chosen."""

        if not hasattr(self, "_selected_members"):
            self._selected_members = []
            for id in self.fields.getlist("member"):
                if id.isdigit():
                    self._selected_members.append(int(id))
        return self._selected_members

    @property
    def user(self):
        """Object for the currently logged-on CDR user."""

        if not hasattr(self, "_user"):
            opts = dict(id=self.session.user_id)
            self._user = self.session.User(self.session, **opts)
        return self._user


class Boards:
    """Collection of all of the active PDQ boards."""

    IACT = "Integrative, Alternative, and Complementary Therapies"
    BOARD_TYPES = "PDQ Editorial Board", "PDQ Advisory Board"

    @property
    def json(self):
        """Information about the board in a form client-side scripting uses."""

        if not hasattr(self, "_json"):
            boards = {}
            for board in self.boards:
                members = [(m.id, m.name) for m in board.members]
                values = dict(
                    id=board.id,
                    type=board.type,
                    members=members
                )
                boards[board.id] = values
            self._json = dumps(boards, indent=2)
        return self._json

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

    @property
    def control(self):
        """Access to the database cursor."""
        return self.__control

    @property
    def cursor(self):
        """Access to the database."""
        return self.control.cursor

    @property
    def boards(self):
        """Assemble the sequence of `Board` objects."""

        if not hasattr(self, "_boards"):
            fields = "d.id", "d.title"
            query = self.control.Query("active_doc d", *fields)
            query.order("d.title")
            query.join("query_term t", "t.doc_id = d.id")
            query.where("t.path = '/Organization/OrganizationType'")
            query.where(query.Condition("t.value", self.BOARD_TYPES, "IN"))
            self._boards = []
            for id, title in query.execute(self.cursor).fetchall():
                title = title.split(";")[0].strip()
                title = title.replace(self.IACT, "IACT")
                self._boards.append(self.Board(self.control, id, title))
        return self._boards

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

        @property
        def control(self):
            """Access to the database cursor."""
            return self.__control

        @property
        def cursor(self):
            """Access to the database."""
            return self.control.cursor

        @property
        def id(self):
            """Primary key for the board's Organization CDR document."""
            return self.__id

        @property
        def name(self):
            """String for the name of the board."""
            return self.__name

        @property
        def members(self):
            """Sorted sequence of the board's members."""

            if not hasattr(self, "_members"):
                query = self.control.Query("active_doc d", "d.id").unique()
                query.join("query_term m", "m.doc_id = d.id")
                query.where(query.Condition("m.path", self.BOARD))
                query.where(query.Condition("m.int_val", self.id))
                members = []
                for row in query.execute(self.cursor).fetchall():
                    member = self.Member(self, row.id)
                    if member.name:
                        members.append(member)
                self._members = sorted(members)
            return self._members

        @property
        def type(self):
            """String for the board's type ("advisory" or "editorial")."""

            if not hasattr(self, "_type"):
                if "advisory" in self.name.lower():
                    self._type = "advisory"
                else:
                    self._type = "editorial"
            return self._type

        class Member:
            """One of the members of a PDQ board."""

            def __init__(self, board, id):
                """Save the caller's values."""
                self.__board = board
                self.__id = id

            def __lt__(self, other):
                """Make the board member objects sortable by member name."""
                return self.name.lower() < other.name.lower()

            @property
            def id(self):
                """Primary key for the member's PDQBoardMemberInfo doc."""
                return self.__id

            @property
            def board(self):
                """Access to the `Control` object."""
                return self.__board

            @property
            def name(self):
                """Board member's name in Surname, Given Name format."""

                if not hasattr(self, "_name"):
                    self._name = self.board.control.board_members.get(self.id)
                return self._name


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
