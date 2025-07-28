#!/usr/bin/env python
"""JSON API for fetching the names, IDs, and types of the PDQ Boards.
"""

from json import dumps
from cdrcgi import Controller


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "get-boards API service"
    LOGNAME = "testing"
    N_PATH = "/Organization/OrganizationNameInformation/OfficialName/Name"
    T_PATH = "/Organization/OrganizationType"
    TYPES = "PDQ Advisory Board", "PDQ Editorial Board"

    def run(self):
        """Overridden because this is not a standard report."""

        fields = "n.doc_id", "n.value AS board_name", "t.value AS board_type"
        query = self.Query("query_term n", *fields)
        query.join("query_term t", "t.doc_id = n.doc_id")
        query.join("active_doc a", "a.id = n.doc_id")
        query.where(query.Condition("n.path", self.N_PATH))
        query.where(query.Condition("t.path", self.T_PATH))
        query.where(query.Condition("t.value", self.TYPES, "IN"))
        query.unique().order("n.value")
        boards = dict(advisory=[], editorial=[])
        for row in query.execute(self.cursor).fetchall():
            board_type = row.board_type.split()[1].lower()
            board = dict(id=row.doc_id, name=row.board_name)
            boards[board_type].append(board)
        self.send_page(dumps(boards, indent=2), mime_type="application/json")


if __name__ == "__main__":
    """Only execute if invoked directly, not imported as a module."""

    control = Control()
    try:
        control.run()
    except Exception as e:
        control.logger.exception("failure getting boards")
        control.send_page(f"Failure fetching boards: {e}", text_type="plain")
