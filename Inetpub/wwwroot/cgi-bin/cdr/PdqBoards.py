#!/usr/bin/env python

"""Report on PDQ Board members and topics.
"""

from collections import UserDict
from cdrcgi import Controller
from cdr import getBoardNames


class Control(Controller):
    """Access to the DB and to report-creation tools."""

    SUBTITLE = "PDQ Board Report"
    AUDIENCES = "Health professionals", "Patients"
    GROUPINGS = dict(topic="Topic", member="Board Member")

    ORG_NAME = "/Organization/OrganizationNameInformation/OfficialName/Name"
    B_PATH = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
    M_PATH = "/Summary/SummaryMetaData/PDQBoard/BoardMember/@cdr:ref"
    A_PATH = "/Summary/SummaryMetaData/SummaryAudience"
    DISPLAY_OPTS = (
        ("N", "Without CDR ID", True),
        ("Y", "With CDR ID", False),
    )
    VERSION_OPTS = (
        ("N", "Publishable only", True),
        ("Y", "Publishable and non-publishable", False),
    )
    GROUPING_OPTS = (
        ("topic", "Group by Topic", True),
        ("member", "Group by Board Member", False),
    )
    INCLUSION_OPTS = (
        ("a", "Summaries and modules", False),
        ("s", "Summaries only", True),
        ("m", "Modules only", False),
    )

    def populate_form(self, page):
        """Put the fields on the request form.

        Pass:
            page - HTMLPage object on which the fields are installed
        """

        fieldset = page.fieldset("Board and Audience")
        fieldset.append(page.select("board", options=self.boards))
        fieldset.append(page.select("audience", options=self.AUDIENCES))
        page.form.append(fieldset)
        fieldset = page.fieldset("ID Display")
        for value, label, checked in self.DISPLAY_OPTS:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("show_id", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Version Display")
        for value, label, checked in self.VERSION_OPTS:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("show_all", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Report Grouping")
        for value, label, checked in self.GROUPING_OPTS:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("grouping", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Included Documents")
        for value, label, checked in self.INCLUSION_OPTS:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("included", **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Override this method because we have a non-tabular report."""

        page = self.report.page
        page.add_css("h3 { color: black; }")
        page.form.append(page.B.H3(self.report_title))
        if self.members:
            if self.grouping == "topic":
                entities = sorted(self.summaries)
            else:
                entities = sorted(self.members.values())
        for entity in entities:
            page.form.append(entity.block)
        self.report.send()

    @property
    def audience(self):
        """Patients or Health professionals."""

        if not hasattr(self, "_audience"):
            default = self.AUDIENCES[0]
            self._audience = self.fields.getvalue("audience", default)
            if self._audience not in self.AUDIENCES:
                self.bail()
        return self._audience

    @property
    def board(self):
        """Integer for the ID of the selected PDQ board."""

        if not hasattr(self, "_board"):
            self._board = self.fields.getvalue("board")
            if self._board:
                if not self._board.isdigit():
                    self.bail()
                self._board = int(self._board)
                if self._board not in self.boards:
                    self.bail()
        return self._board

    @property
    def boards(self):
        """Dictionary of the active boards (indexed by CDR document ID)."""

        if not hasattr(self, "_boards"):
            self._boards = dict(getBoardNames(display="short"))
        return self._boards

    @property
    def grouping(self):
        """Patients or Health professionals."""

        if not hasattr(self, "_grouping"):
            default = self.GROUPING_OPTS[0][0]
            self._grouping = self.fields.getvalue("grouping", default)
            if self._grouping not in self.GROUPINGS:
                self.bail()
        return self._grouping

    @property
    def include(self):
        """Include summaries, modules, or both?"""

        if not hasattr(self, "_include"):
            self._include = self.fields.getvalue("included", "s")
            if self._include not in [o[0] for o in self.INCLUSION_OPTS]:
                self.bail()
        return self._include

    @property
    def members(self):
        """Members of the selected board, with or with assigned summaries."""

        if not hasattr(self, "_members"):
            doctype = "PDQBoardMemberInfo"
            m_path = f"/{doctype}/BoardMemberName/@cdr:ref"
            b_path = f"/{doctype}/BoardMembershipDetails/BoardName/@cdr:ref"
            c_path = f"/{doctype}/BoardMembershipDetails/CurrentMember"
            query = self.Query("query_term m", "m.int_val")
            query.join("query_term b", "b.doc_id = m.doc_id")
            query.join("query_term c", "c.doc_id = b.doc_id",
                       "LEFT(c.node_loc, 4) = LEFT(b.node_loc, 4)")
            query.where(f"m.path = '{m_path}'")
            query.where(f"b.path = '{b_path}'")
            query.where(f"c.path = '{c_path}'")
            query.where("c.value = 'Yes'")
            query.where(query.Condition("b.int_val", self.board))
            self._members = dict(self.persons)
            for row in query.execute(self.cursor).fetchall():
                self._members[row.int_val] = self.persons[row.int_val]

            # Final loop picks up reviewers of the board's summaries even
            # if they are not found as members of the board.
            for summary in self.summaries:
                for reviewer in summary.reviewers:
                    if reviewer not in self._members:
                        self._members[reviewer] = self.persons[reviewer]
                        self._members[reviewer].non_member = True
        return self._members

    @property
    def no_results(self):
        """Suppress message about lack of tables."""
        return None

    @property
    def persons(self):
        """Cached dictionary of `Person` objects for members/reviewers."""

        if not hasattr(self, "_persons"):
            class Persons(UserDict):
                def __init__(self, control):
                    self.__control = control
                    UserDict.__init__(self)

                def __getitem__(self, key):
                    if key not in self.data:
                        self.data[key] = Person(self.__control, key)
                    return self.data[key]
            self._persons = Persons(self)
        return self._persons

    @property
    def report_title(self):
        """Level-3 header at the top of the report."""

        grouping = dict(topic="Topics", member="Reviewers")[self.grouping]
        board_name = self.boards[self.board]
        return f"{grouping} for PDQ {board_name} ({self.audience})"

    @property
    def show_id(self):
        """True if summary document ID should be included in the display."""
        return self.fields.getvalue("show_id") == "Y"

    @property
    def subtitle(self):
        """What we show below the top banner."""

        if self.request == self.SUBMIT:
            grouping = self.GROUPINGS[self.grouping]
            today = self.started.strftime("%Y-%m-%d")
            return f"PDQ Board Report by {grouping} \N{EM DASH} {today}"
        else:
            return self.SUBTITLE

    @property
    def summaries(self):
        """Sequence of the summaries managed by the selected board."""

        if not hasattr(self, "_summaries"):
            query_term = "query_term" if self.unpub else "query_term_pub"
            query = self.Query(f"{query_term} b", "b.doc_id", "m.value")
            query.join(f"{query_term} a", "a.doc_id = b.doc_id")
            if not self.unpub:
                query.join("active_doc d", "d.id = b.doc_id")
            query.where(f"a.path = '{self.A_PATH}'")
            query.where(query.Condition("a.value", self.audience))
            query.where(f"b.path = '{self.B_PATH}'")
            query.where(query.Condition("b.int_val", self.board))
            if self.include == "m":
                query.join(f"{query_term} m", "m.doc_id = b.doc_id",
                           "m.path = '/Summary/@ModuleOnly'",
                           "m.value = 'Yes'")
            else:
                query.outer(f"{query_term} m", "m.doc_id = b.doc_id",
                            "m.path = '/Summary/@ModuleOnly'")
                if self.include == "s":
                    query.where("(m.value IS NULL OR m.value <> 'Yes')")
            query.log()
            rows = query.unique().execute(self.cursor).fetchall()
            self._summaries = [Summary(self, row) for row in rows]
        return self._summaries

    @property
    def unpub(self):
        """True if unpublished summaries should be included in the report."""
        return self.fields.getvalue("show_all") == "Y"


class Summary:
    """Information needed for one summary (a.k.a. Topic) for the report."""

    NONE = "NO TITLE FOUND"

    def __init__(self, control, row):
        """Remember the caller's values.

        Pass:
            control - access to report options and report-building tools
            row - database query results for this summary
        """

        self.__control = control
        self.__row = row

    def __lt__(self, other):
        """Support sorting by normalized title."""
        return self.key < other.key

    @property
    def block(self):
        "HTML DIV block with this summary's title and reviewers."""

        if not hasattr(self, "_block"):
            B = self.control.HTMLPage.B
            self._block = B.DIV(B.H4(self.display))
            if self.reviewers:
                ul = B.UL()
                for reviewer in sorted(self.reviewers.values()):
                    ul.append(B.LI(reviewer.name))
                self._block.append(ul)
        return self._block

    @property
    def control(self):
        """Access to report options and report-building tools."""
        return self.__control

    @property
    def display(self):
        """Possibly enhanced copy of the summary's title."""

        if not hasattr(self, "_display"):
            self._display = self.title
            if self.is_module:
                self._display += " (module)"
            if self.control.show_id:
                self._display += f" ({self.id})"
        return self._display

    @property
    def id(self):
        """Integer for the summary's CDR document ID."""
        return self.__row.doc_id

    @property
    def is_module(self):
        """True if this summary can only be used as a module."""
        return self.__row.value == "Yes"

    @property
    def key(self):
        """Sort by normalized title."""

        if not hasattr(self, "_key"):
            self._key = "" if self.title == self.NONE else self.title.lower()
        return self._key

    @property
    def reviewers(self):
        """Board members assigned to review this summary."""

        if not hasattr(self, "_reviewers"):
            self._reviewers = {}
            query = self.control.Query("query_term m", "m.int_val AS id")
            query.join("query_term b", "b.doc_id = m.doc_id",
                       "LEFT(b.node_loc, 8) = LEFT(m.node_loc, 8)")
            query.where(f"b.path = '{self.control.B_PATH}'")
            query.where(f"m.path = '{self.control.M_PATH}'")
            query.where(query.Condition("b.int_val", self.control.board))
            query.where(query.Condition("b.doc_id", self.id))
            for row in query.unique().execute(self.control.cursor).fetchall():
                self._reviewers[row.id] = self.control.persons[row.id]
        return self._reviewers

    @property
    def title(self):
        """String for the official title of this PDQ summary."""

        if not hasattr(self, "_title"):
            query = self.control.Query("query_term", "value")
            query.where(query.Condition("doc_id", self.id))
            query.where("path = '/Summary/SummaryTitle'")
            rows = query.execute(self.control.cursor).fetchall()
            self._title = rows[0].value if rows else self.NONE
        return self._title


class Person:
    """One of these for every reviewer on the report."""

    NEMO = "NO NAME FOUND"

    def __init__(self, control, id):
        """Remember the caller's values.

        Pass:
            control - access to the database and report-building tools
            id - integer for the board member's CDR Person document
        """

        self.__control = control
        self.__id = id

    def __lt__(self, other):
        """Support sorting of the board members by normalized name."""
        return self.key < other.key

    @property
    def block(self):
        "HTML DIV block with this reviewer's name and summaries."""

        if not hasattr(self, "_block"):
            B = self.control.HTMLPage.B
            self._block = B.DIV(B.H4(self.name))
            if self.summaries:
                ul = B.UL()
                for summary in sorted(self.summaries):
                    ul.append(B.LI(summary.display))
                self._block.append(ul)
        return self._block

    @property
    def control(self):
        """Access to the database and report-building tools."""
        return self.__control

    @property
    def id(self):
        """Integer for the board member's CDR Person document."""
        return self.__id

    @property
    def key(self):
        """Case-insensitive sorting of board members by name."""

        if not hasattr(self, "_key"):
            self._key = "" if self.name == self.NEMO else self.name.lower()
        return self._key

    @property
    def name(self):
        """String for this reviewer's name."""

        if not hasattr(self, "_name"):
            self._name = self.control.doc_titles[self.id] or self.NEMO
            if self.non_member:
                self._name += " (non-member)"
        return self._name

    @property
    def non_member(self):
        """True=reviewer of summary of whose board (s)he is not a member."""

        if not hasattr(self, "_non_member"):
            self._non_member = False
        return self._non_member

    @non_member.setter
    def non_member(self, value):
        """Settable by the control class later on."""
        self._non_member = value

    @property
    def summaries(self):
        """Sequence of summaries assigned to this reviewer."""

        if not hasattr(self, "_summaries"):
            self._summaries = []
            for summary in self.control.summaries:
                if self.id in summary.reviewers:
                    self._summaries.append(summary)
        return self._summaries


if __name__ == "__main__":
    """Let this be loaded without doing anything to support (e.g.) lint."""
    Control().run()
