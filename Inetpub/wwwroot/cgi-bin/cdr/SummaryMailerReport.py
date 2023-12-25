#!/usr/bin/env python

"""Show information about PDQ summary mailers.

Two flavors of the report are available, standard, and historical.
"""

from collections import UserDict
from datetime import date
from functools import cached_property
from cdr import Board
from cdrapi.docs import Doc
from cdrcgi import Controller


class Control(Controller):
    """Access to the database and report-building tools."""

    LOGNAME = "SummaryMailerReport"
    MEMBER_SORT = "member"
    SUMMARY_SORT = "summary"
    CDR_REF = f"{{{Doc.NS}}}ref"
    CREATE_TABLES = (
        "CREATE TABLE #board_member (person_id INT, member_id INT)",
        "CREATE TABLE #board_summary (doc_id INT)",
    )
    INFO_PATH = "/PDQBoardMemberInfo"
    MEMBER_PATH = f"{INFO_PATH}/BoardMemberName/@cdr:ref"
    BOARD_PATH = f"{INFO_PATH}/BoardMembershipDetails/BoardName/@cdr:ref"
    SUMMARY_PATH = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
    SORTS = (
        (MEMBER_SORT, "Board Member", True),
        (SUMMARY_SORT, "Summary Name", False),
    )
    LAST = "last"
    LAST_CHECKED_IN = "last-checked-in"
    SHOW = (
        (LAST, "Last Mailer", True),
        (LAST_CHECKED_IN, "Last Checked-In Mailer", False),
    )
    WIDTHS = 65, 185, 365, 70, 70, 250, 305
    HEADERS = (
        "Mailer ID",
        "Board Member",
        "Summary",
        "Sent",
        "Response",
        "Changes",
        "Comments",
    )
    assert len(WIDTHS) == len(HEADERS)

    def build_tables(self):
        """Assemble the report's single table."""

        if not self.board:
            self.bail("No board selected")
        opts = dict(
            sheet_name=self.sheet_name,
            columns=self.columns,
            freeze_panes="A4",
            caption=self.caption,
        )
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Solicit options for the report.

        Pass:
            page - HTMLPage object where the fields go
        """

        page.form.append(page.hidden_field("flavor", self.flavor))
        fieldset = page.fieldset("Select PDQ Board")
        checked = True
        for board in sorted(self.boards.values()):
            opts = dict(value=board.id, label=board.name, checked=checked)
            fieldset.append(page.radio_button("board", **opts))
            checked = False
        page.form.append(fieldset)
        fieldset = page.fieldset("Report Sorting")
        for value, display, checked in self.SORTS:
            label = f"Order by {display}"
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("sort", **opts))
        page.form.append(fieldset)
        if self.historical:
            fieldset = page.fieldset("Report Date Range")
            fieldset.append(page.date_field("start", value=self.start))
            fieldset.append(page.date_field("end", value=self.end))
            page.form.append(fieldset)
        else:
            fieldset = page.fieldset("Select Mailers To Be Displayed")
            for value, display, checked in self.SHOW:
                label = f"Show {display}"
                opts = dict(value=value, label=label, checked=checked)
                fieldset.append(page.radio_button("show", **opts))
            page.form.append(fieldset)
        page.add_css("fieldset { width: 650px; }")

    @cached_property
    def board(self):
        """Integer CDR document ID for the report's selected board."""

        try:
            board = int(self.fields.getvalue("board"))
            if board not in self.boards:
                self.bail()
            return board
        except Exception:
            return None

    @cached_property
    def boards(self):
        """Dictionary of PDQ boards for the form's radio buttons."""
        return Board.get_boards(None, self.cursor)

    @cached_property
    def board_members(self):
        """Dictionary of `BoardMember` objects, indexed by Person doc ID."""

        for create_sql in self.CREATE_TABLES:
            self.cursor.execute(create_sql)
        query = self.Query("query_term m", "m.int_val", "m.doc_id")
        query.join("query_term b", "b.doc_id = m.doc_id")
        query.join("active_doc d", "d.id = m.doc_id")
        query.where(f"m.path = '{self.MEMBER_PATH}'")
        query.where(f"b.path = '{self.BOARD_PATH}'")
        query.where(f"b.int_val = {self.board}")
        query.unique()
        self.cursor.execute(f"INSERT INTO #board_member {query}")
        query = self.Query("query_term", "doc_id").unique()
        query.where(f"path = '{self.SUMMARY_PATH}'")
        query.where(f"int_val = {self.board}")
        self.cursor.execute(f"INSERT INTO #board_summary {query}")
        self.conn.commit()
        query = self.Query("#board_member", "person_id", "member_id")
        board_members = {}
        for row in query.execute(self.cursor).fetchall():
            board_members[row.person_id] = BoardMember(self, row)
        return board_members

    @cached_property
    def caption(self):
        """What we display at the top of the report."""

        if self.historical:
            title = "Summary Mailer History Report ({} - {})"
            title = title.format(self.start, self.end)
        elif self.show == self.LAST:
            title = "Summary Mailer Report (Last)"
        else:
            title = "Summary Mailer Report (Last Checked In)"
        board_name = self.boards[self.board].name
        return f"{title} - {board_name} - {date.today()}"

    @cached_property
    def columns(self):
        """Headers we display at the top of each report table column."""

        columns = []
        for i, header in enumerate(self.HEADERS):
            opts = dict(width=f"{self.WIDTHS[i]:d}px")
            columns.append(self.Reporter.Column(header, **opts))
        return columns

    @cached_property
    def end(self):
        """End of the report's date range."""

        try:
            value = self.fields.getvalue("end", str(date.today()))
            return self.parse_date(value)
        except Exception:
            self.bail("Invalid date")

    @cached_property
    def flavor(self):
        """Is this the 'standard' or the 'historical' version of the report?"""
        return self.fields.getvalue("flavor", "standard")

    @cached_property
    def format(self):
        """This is an Excel report."""
        return "excel"

    @cached_property
    def historical(self):
        """True if we're running the historical flavor of the report."""
        return "histor" in self.flavor

    @cached_property
    def mailers(self):
        """The documents on which we're reporting.

        Don't eliminate the check of self.board_members at the top.
        It's necessary to populate the temporary tables before they're
        used.
        """

        if not self.board_members:
            self.bail("Internal failure")
        fields = (
            "s.doc_id AS mailer_id",
            "s.int_val AS summary_id",
            "d.value AS date",
            "r.int_val AS recipient_id",
        )
        date_path = "/Mailer/Sent"
        if not self.historical and self.show == self.LAST_CHECKED_IN:
            date_path = "/Mailer/Response/Received"
        query = self.Query("query_term s", *fields)
        query.where("s.path = '/Mailer/Document/@cdr:ref'")
        query.join("query_term r", "r.doc_id = s.doc_id")
        query.where("r.path = '/Mailer/Recipient/@cdr:ref'")
        query.join("query_term d", "d.doc_id = s.doc_id")
        query.where(f"d.path = '{date_path}'")
        query.join("#board_member m", "m.person_id = r.int_val")
        query.join("#board_summary b", "b.doc_id = s.int_val")
        if self.historical:
            start, end = self.start, f"{self.end} 23:59:59"
            query.where(query.Condition("d.value", start, ">="))
            query.where(query.Condition("d.value", end, "<="))
        mailers = [] if self.historical else {}
        for row in query.execute(self.cursor).fetchall():
            member = self.board_members[row.recipient_id]
            if row.date and member.was_active(row.date):
                if self.historical:
                    mailers.append(Mailer(self, row.mailer_id))
                else:
                    key = row.recipient_id, row.summary_id
                    if key not in mailers or mailers[key][1] < row.date:
                        mailers[key] = row.mailer_id, row.date
        if self.historical:
            return mailers
        return [Mailer(self, v[0]) for v in mailers.values()]

    @cached_property
    def order(self):
        """How should we sort the report?"""

        order = self.fields.getvalue("sort", self.MEMBER_SORT)
        if order not in [values[0] for values in self.SORTS]:
            self.bail()
        return order

    @cached_property
    def recipients(self):
        """Cached lookup of mailer recipient names by CDR Person ID.

        This is an alias for the base class method which does cached
        lookup of document titles.
        """

        return self.doc_titles

    @cached_property
    def rows(self):
        """One for each mailer in the report."""

        rows = []
        for mailer in sorted(self.mailers):
            rows.append([
                self.Reporter.Cell(mailer.id, center=True),
                mailer.recipient,
                mailer.summary,
                self.Reporter.Cell(mailer.sent, center=True),
                self.Reporter.Cell(mailer.response, center=True),
                "\n".join(mailer.changes),
                "\n".join(mailer.comments),
            ])
        return rows

    @cached_property
    def sheet_name(self):
        """String for the report's tab."""
        return self.subtitle

    @cached_property
    def show(self):
        """Last mailer or last checked-in mailer?"""

        show = self.fields.getvalue("show", self.LAST)
        if show not in [values[0] for values in self.SHOW]:
            self.bail()
        return show

    @cached_property
    def start(self):
        """Beginning of the report's date range."""

        value = self.fields.getvalue("start", "2000-01-01")
        try:
            start = self.parse_date(value)
        except Exception:
            self.bail("Invalid date")
        return start

    @cached_property
    def subtitle(self):
        """What we display at the top of the page."""

        if self.historical:
            return "Summary Mailer History Report"
        return "Summary Mailer Report"

    @cached_property
    def summaries(self):
        """Cached lookup of PDQ summary title by CDR document ID."""

        class Summaries(UserDict):
            def __init__(self, control):
                self.__control = control
                UserDict.__init__(self)

            def __getitem__(self, key):
                if key not in self.data:
                    query = self.__control.Query("query_term", "value")
                    query.where("path = '/Summary/SummaryTitle'")
                    query.where(f"doc_id = {key}")
                    row = query.execute(self.__control.cursor).fetchone()
                    self.data[key] = row.value if row else None
                return self.data[key]
        return Summaries(self)

    @cached_property
    def title(self):
        """Depends on whether we're showing the form or the report."""
        return self.subtitle if self.request else self.TITLE


class BoardMember:
    """Information about one of the PDQ board's members."""

    def __init__(self, control, row):
        """Capture the caller's information.

        Pass:
            control - access to the database and the report settings
            row - CDR document IDs for the board member
        """

        self.control = control
        self.row = row

    def was_active(self, when):
        """True if the board member was an active member of the board.

        Pass:
            when - date string to check

        Return:
            True if the date falls in one of the member's membership terms
        """

        when = str(when)[:10]
        for term in self.terms:
            if term.start <= when:
                if not term.end or term.end >= when:
                    return True
        return False

    @cached_property
    def member_id(self):
        """Integer ID for the board member's CDR `PDQBoardMemberInfo` doc."""
        return self.row.member_id

    @cached_property
    def person_id(self):
        """Integer ID for the board member's CDR `Person` document."""
        return self.row.person_id

    @cached_property
    def terms(self):
        """Membership terms for the board member."""

        terms = []
        doc = Doc(self.control.session, id=self.member_id)
        for node in doc.root.findall("BoardMembershipDetails"):
            term = self.MembershipTerm(node)
            if term.board == self.control.board and term.start:
                terms.append(term)
        return terms

    class MembershipTerm:
        """Date range and board ID for a PDQ board membership term."""

        def __init__(self, node):
            """Remember the caller's value.

            Pass:
                node - XML doc node from which the properties can be pulled
            """

            self.node = node

        @cached_property
        def board(self):
            """CDR Organization document integer ID for the PDQ board."""

            try:
                ref = self.node.find("BoardName").get(Control.CDR_REF)
                return Doc.extract_id(ref)
            except Exception:
                return None

        @cached_property
        def end(self):
            """When this membership term ended, if applicable."""

            node = self.node.find("TerminationDate")
            if node is not None and node.text is not None:
                return node.text
            return None

        @cached_property
        def start(self):
            """When this membership term started."""

            node = self.node.find("TermStartDate")
            if node is not None and node.text is not None:
                return node.text
            return None


class Mailer:
    """Information need for a single row in the report."""

    def __init__(self, control, id):
        """Remember the caller's values.

        Pass:
            control - access to the database and the report settings
            id - integer for the unique ID of the CDR `Mailer` document
        """

        self.control = control
        self.id = id

    def __lt__(self, other):
        """Sorting depends on the `key` property, determined by report type."""
        return self.key < other.key

    @cached_property
    def changes(self):
        """Categories of changes reflected in the recipient's response."""

        changes = []
        for node in self.doc.root.findall("Response/ChangesCategory"):
            change = node.text.strip() if node.text else ""
            if change:
                changes.append(change)
        return changes

    @cached_property
    def comments(self):
        """Additional notes supplied byu the mailer recipient."""

        comments = []
        for node in self.doc.root.findall("Response/Comment"):
            comment = node.text.strip() if node.text else ""
            if comment:
                comments.append(comment)
        return comments

    @cached_property
    def doc(self):
        """`Doc` object for the mailer."""
        return Doc(self.control.session, id=self.id)

    @cached_property
    def key(self):
        """Sorting support, adjusted for the type of report."""

        if self.control.order == Control.MEMBER_SORT:
            return self.recipient.lower(), self.summary.lower()
        return self.summary.lower(), self.recipient.lower()

    @cached_property
    def recipient(self):
        """Name of the person who got the mailer."""

        node = self.doc.root.find("Recipient")
        try:
            doc_id = Doc.extract_id(node.get(Control.CDR_REF))
            return self.control.recipients[doc_id]
        except Exception:
            return None

    @cached_property
    def response(self):
        """When the recipient's response was received."""

        for node in self.doc.root.findall("Response/Received"):
            if node.text:
                return node.text.strip()[:10]
        return None

    @cached_property
    def sent(self):
        """The date the summary mailer was mailed."""

        node = self.doc.root.find("Sent")
        if node is not None and node.text is not None:
            return node.text[:10]
        return None

    @cached_property
    def summary(self):
        """Document title of the PDQ summary behind this mailer."""

        node = self.doc.root.find("Document")
        try:
            doc_id = Doc.extract_id(node.get(Control.CDR_REF))
            return self.control.summaries[doc_id]
        except Exception:
            return None


if __name__ == "__main__":
    """Don't execute script if loaded as a module."""
    Control().run()
