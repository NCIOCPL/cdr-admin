#!/usr/bin/env python
"""JSON API for fetching the information about PDQ summaries.

The limit parameter can be used to restrict the set of members returned
to the first N board members. For example:

    GET /cgi-bin/cdr/get-board-members.py?limit=5

The include-non-current parameter can be used to get board members who
are not current serving on any board. For example:

    GET /cgi-bin/cdr/get-board-members.py?include-non-current=true
"""

from collections import defaultdict
from functools import cached_property
from json import dumps
from cdrcgi import Controller


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "get-board-members API service"
    LOGNAME = "testing"
    BM_PATH = "/PDQBoardMemberInfo/BoardMembershipDetails/BoardName/@cdr:ref"
    CM_PATH = "/PDQBoardMemberInfo/BoardMembershipDetails/CurrentMember"
    BN_PATH = "/Organization/OrganizationNameInformation/OfficialName/Name"
    BT_PATH = "/Organization/OrganizationType"
    BOARD_TYPES = "PDQ Advisory Board", "PDQ Editorial Board"

    def run(self):
        """Overridden because this is not a standard report."""

        opts = dict(mime_type="application/json")
        self.send_page(dumps(self.board_members, indent=2), **opts)

    @cached_property
    def board_members(self):
        """Sequence of dictionaries with board member values."""

        query = self.Query("query_term m", "m.doc_id", "m.int_val").order(1)
        query.join("active_doc a", "a.id = m.doc_id")
        query.where("m.path = '/PDQBoardMemberInfo/BoardMemberName/@cdr:ref'")
        members = []
        for member_id, person_id in query.execute(self.cursor).fetchall():
            if not self.include_non_current:
                if member_id not in self.current_members:
                    continue
            boards = []
            for membership in self.board_memberships.get(member_id, []):
                board_id = membership["board_id"]
                board = dict(
                    id=board_id,
                    name=self.boards.get(board_id),
                    current=membership["current"],
                )
                boards.append(board)
            member = dict(
                id=member_id,
                person=dict(
                    id=person_id,
                    surname=self.surnames.get(person_id),
                    forename=self.forenames.get(person_id),
                    initials=self.initials.get(person_id),
                ),
                boards=boards,
            )
            members.append(member)
            if self.limit and len(members) >= self.limit:
                break
        return members

    @cached_property
    def board_memberships(self):
        """Dictionary of board memberships indexed by member ID."""

        query = self.Query("query_term b", "b.doc_id", "b.int_val", "c.value")
        node_loc_condition = "LEFT(c.node_loc, 4) = LEFT(b.node_loc, 4)"
        query.outer("query_term c", "c.doc_id = b.doc_id", node_loc_condition)
        query.where(query.Condition("b.path", self.BM_PATH))
        query.where(query.Condition("c.path", self.CM_PATH))
        memberships = defaultdict(list)
        for row in query.execute(self.cursor).fetchall():
            current = row.value and row.value.lower() == "yes"
            membership = dict(board_id=row.int_val, current=current)
            memberships[row.doc_id].append(membership)
        return memberships

    @cached_property
    def boards(self):
        """Dictionary of board names indexed by board ID."""

        query = self.Query("query_term n", "n.doc_id", "n.value")
        query.join("query_term t", "t.doc_id = n.doc_id")
        query.join("active_doc a", "a.id = n.doc_id")
        query.where(query.Condition("n.path", self.BN_PATH))
        query.where(query.Condition("t.path", self.BT_PATH))
        query.where(query.Condition("t.value", self.BOARD_TYPES, "IN"))
        query.unique()
        boards = {}
        for id, name in query.execute(self.cursor).fetchall():
            boards[id] = name
        return boards

    @cached_property
    def current_members(self):
        """Set if active board members' IDs."""

        current = set()
        for id in self.board_memberships:
            for membership in self.board_memberships[id]:
                if membership["current"]:
                    current.add(id)
                    break
        return current

    @cached_property
    def forenames(self):
        """Dictionary mapping person IDs to forenames."""

        query = self.Query("query_term", "doc_id", "value")
        query.where("path = '/Person/PersonNameInformation/GivenName'")
        forenames = {}
        for id, forename in query.execute(self.cursor).fetchall():
            forenames[id] = forename
        return forenames

    @cached_property
    def initials(self):
        """Dictionary mapping person IDs to person name initials."""

        query = self.Query("query_term", "doc_id", "value")
        query.where("path = '/Person/PersonNameInformation/MiddleInitial'")
        initials = {}
        for id, value in query.execute(self.cursor).fetchall():
            initials[id] = value
        return initials

    @cached_property
    def include_non_current(self):
        """True if we should include summaries which are not published."""
        return True if self.fields.getvalue("include-non-current") else False

    @cached_property
    def limit(self):
        """Optional throttle on the number of summaries to return per type."""
        return int(self.fields.getvalue("limit", "0"))

    @cached_property
    def surnames(self):
        """Dictionary mapping person IDs to surnames."""

        query = self.Query("query_term", "doc_id", "value")
        query.where("path = '/Person/PersonNameInformation/SurName'")
        surnames = {}
        for id, surname in query.execute(self.cursor).fetchall():
            surnames[id] = surname
        return surnames


if __name__ == "__main__":
    """Only execute if invoked directly, not imported as a module."""

    control = Control()
    try:
        control.run()
    except Exception as e:
        control.logger.exception("failure getting board members")
        message = f"Failure fetching board members: {e}"
        control.send_page(message, text_type="plain")


