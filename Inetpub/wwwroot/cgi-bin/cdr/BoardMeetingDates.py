#!/usr/bin/env python

"""List PDQ editorial board meetings by date or board.
"""

import datetime
from cdrcgi import Controller, Reporter, bail
from cdr import Board
from cdrapi import db

class Control(Controller):
    """Top-level processing logic."""

    SUBTITLE = "PDQ Editorial Board Meetings"
    BY_BOARD = "display_by_board"
    BY_DATE = "display_by_date"
    REPORT_TYPES = BY_BOARD, BY_DATE

    def build_tables(self):
        """Assemble the correct report, based on the user's choice."""
        if self.report_type == self.BY_BOARD:
            return self.table_by_board
        return self.table_by_date

    def populate_form(self, page):
        """Add the field sets to the form page.

        Add client-side scripting to make the board picklist behave
        correctly.

        Pass
            page - HTMLPage object on which the form is built
        """
        fieldset = page.fieldset("Select Report Type")
        for report_type in self.REPORT_TYPES:
            opts = dict(value=report_type)
            if report_type == self.BY_BOARD:
                opts["checked"] = True
            fieldset.append(page.radio_button("report_type", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Select Boards")
        fieldset.append(page.checkbox("board", value="all", checked=True))
        for board in sorted(self.boards.values()):
            opts = dict(value=board.id, label=str(board))
            fieldset.append(page.checkbox("board", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Date Range for Report")
        today = datetime.date.today()
        start = datetime.date(today.year, 1, 1)
        end = datetime.date(today.year, 12, 31)
        fieldset.append(page.date_field("start", value=str(start)))
        fieldset.append(page.date_field("end", value=str(end)))
        page.form.append(fieldset)
        page.form.set("method", "get")
        page.add_script("""\
function check_board(val) {
    if (val == "all") {
        jQuery("input[name='board']").prop("checked", false);
        jQuery("#board-all").prop("checked", true);
    }
    else if (jQuery("input[name='board']:checked").length > 0)
        jQuery("#board-all").prop("checked", false);
    else
        jQuery("#board-all").prop("checked", true);
}""")

    @property
    def caption(self):
        """Display string for the top of the table."""

        if not hasattr(self, "_caption"):
            caption = [self.SUBTITLE]
            if self.start:
                if self.end:
                    caption.append(f"(between {self.start} and {self.end})")
                else:
                    caption.append(f"(on or after {self.start})")
            elif self.end:
                caption.append(f"(up through {self.end})")
            self._caption = caption
        return self._caption

    @property
    def board(self):
        """Sequence of IDs for the boards to be included."""
        if not hasattr(self, "_board"):
            self._board = self.fields.getlist("board")
            for board in self._board:
                if board != "all" and int(board) not in self.boards:
                    bail()
        return self._board

    @property
    def boards(self):
        """PDQ boards for the form's picklist."""
        if not hasattr(self, "_boards"):
            self._boards = Board.get_boards(cursor=self.cursor)
        return self._boards

    @property
    def end(self):
        """End of the date range for the report."""
        if not hasattr(self, "_end"):
            self._end = self.fields.getvalue("end")
        return self._end

    @property
    def meetings(self):
        """Find the meetings which are in-scope for this report."""
        if not hasattr(self, "_meetings"):
            self._meetings = Meeting.get_meetings(self)
        return self._meetings

    @property
    def report_type(self):
        """User's decision as to whether to report by board or by date."""
        if not hasattr(self, "_report_type"):
            self._report_type = self.fields.getvalue("report_type")
            if not self._report_type:
                self._report_type = self.BY_BOARD
            elif self._report_type not in self.REPORT_TYPES:
                bail()
        return self._report_type

    @property
    def start(self):
        """Beginning of the date range for the report."""
        if not hasattr(self, "_start"):
            self._start = self.fields.getvalue("start")
        return self._start

    @property
    def table_by_board(self):
        """Create the 'by board' flavor of the report."""

        boards = {}
        for meeting in self.meetings:
            if meeting.board.name not in boards:
                boards[meeting.board.name] = [meeting]
            else:
                boards[meeting.board.name].append(meeting)
        rows = []
        for board in sorted(boards):
            if rows:
                rows.append(["\xA0"])
            rows.append([Reporter.Cell(board, bold=True)])
            for meeting in boards[board]:
                if meeting.canceled:
                    meeting = Reporter.Cell(meeting, classes="strikethrough")
                rows.append([meeting])
        return Reporter.Table(rows, caption=self.caption)

    @property
    def table_by_date(self):
        """Create the 'by date' flavor of the report."""

        cols = "Date", "Day", "Time", "WebEx", "Board"
        rows = []
        prev = None
        for meeting in sorted(self.meetings):
            if prev and prev < (meeting.date.year, meeting.date.month):
                rows.append([Reporter.Cell("\xA0", colspan=len(cols))])
            prev = meeting.date.year, meeting.date.month
            classes = ["strikethrough"] if meeting.canceled else []
            center = classes + ["center"]
            row = (
                Reporter.Cell(meeting.date, classes=center),
                Reporter.Cell(meeting.day, classes=center),
                Reporter.Cell(meeting.time, classes=center),
                Reporter.Cell("Yes" if meeting.webex else "", classes=center),
                Reporter.Cell(meeting.board.name, classes=classes),
            )
            rows.append(row)
        return Reporter.Table(rows, columns=cols, caption=self.caption)


class Meeting:
    """PDQ Board meeting information."""

    FIELDS = (
        "d.doc_id AS board_id",
        "d.value AS meeting_date",
        "t.value AS meeting_time",
        "w.value AS webex",
        "c.value AS cancellation_reason",
    )
    MEETINGS = "/Organization/PDQBoardInformation/BoardMeetings"
    MEETING = f"{MEETINGS}/BoardMeeting"
    DATE = f"{MEETING}/MeetingDate"
    TIME = f"{MEETING}/MeetingTime"
    CANCELED = f"{MEETING}/@ReasonCanceled"
    WEBEX = f"{DATE}/@WebEx"

    def __init__(self, control, row):
        """Capture the caller's information.

        Properties do the heavy lifting.
        """

        self.__control = control
        self.__row = row

    @property
    def board(self):
        """Board holding the meeting (`cdr.Board` object)."""
        return self.__control.boards.get(self.__row.board_id)

    @property
    def canceled(self):
        """Boolean indicating whether the meeting has been canceled."""
        return self.__row.cancellation_reason is not None

    @property
    def date(self):
        """Date of the meeting (a `datetime.date` object)."""
        if not hasattr(self, "_date"):
            y, m, d = self.__row.meeting_date.split("-")
            self._date = datetime.date(int(y), int(m), int(d))
        return self._date

    @property
    def day(self):
        """String for the meeting's day of the week."""
        return self.date.strftime("%A")

    @property
    def english_date(self):
        """Localized form of the date (no longer used)."""
        return self.date.strftime("%B %d, &Y")

    @property
    def time(self):
        """String for the meeting's time block."""
        return self.__row.meeting_time

    @property
    def webex(self):
        """Boolean indicating whether this is a remote meeting."""
        return self.__row.webex is not None

    def __lt__(self, other):
        """Support sorting the meetings by date, then by board."""
        return (self.date, self.board.name) < (other.date, other.board.name)

    def __str__(self):
        """Prepare the display version of the meeting for the report."""
        if self.webex:
            return f"{self.date} {self.time} (WebEx)"
        return f"{self.date} {self.time}"

    @classmethod
    def get_meetings(cls, control):
        """Find the meetings which are in-scope for the report's parameters.
        """

        query = db.Query("query_term d", *cls.FIELDS).unique()
        query.join("query_term t", *cls.meeting_join("t", "d"))
        query.outer("query_term w", *cls.meeting_join("w", "d", cls.WEBEX))
        query.outer("query_term c", *cls.meeting_join("c", "d", cls.CANCELED))
        query.where(query.Condition("d.path", cls.DATE))
        query.where(query.Condition("t.path", cls.TIME))
        if control.board and "all" not in control.board:
            query.where(query.Condition("d.doc_id", list(control.board), "IN"))
        if control.start:
            query.where(query.Condition("d.value", control.start, ">="))
        if control.end:
            query.where(query.Condition("d.value", control.end, "<="))
        query.log()
        rows = query.execute(control.cursor).fetchall()
        return [cls(control, row) for row in query.execute(control.cursor)]

    @staticmethod
    def meeting_join(a, b, path=""):
        """Conditions for a join clause in the query to find meetings."""
        conditions = [
            f"{a}.doc_id = {b}.doc_id",
            f"LEFT({a}.node_loc, 12) = LEFT({b}.node_loc, 12)",
        ]
        if path:
            conditions.append(f"{a}.path = '{path}'")
        return conditions


if __name__ == "__main__":
    """Let the script be loaded without executing (e.g., for linting)."""
    Control().run()
