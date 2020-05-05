#!/usr/bin/env python

"""Show information about PDQ summary mailers.

Two flavors of the report are available, standard, and historical.
"""

from collections import UserDict
from datetime import date
from cdr import Board
from cdrapi.docs import Doc
from cdrcgi import Controller


class Control(Controller):
    """Access to the database and report-building tools."""

    LOGNAME = "SummaryMailerReport"
    SUBMENU = "Mailer Menu"
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
    assert(len(WIDTHS) == len(HEADERS))

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

    @property
    def board(self):
        """Integer CDR document ID for the report's selected board."""

        if not hasattr(self, "_board"):
            try:
                self._board = int(self.fields.getvalue("board"))
                if self._board not in self.boards:
                    self.bail()
            except Exception:
                self._board = None
        return self._board

    @property
    def boards(self):
        """Dictionary of PDQ boards for the form's radio buttons."""

        if not hasattr(self, "_boards"):
            self._boards = Board.get_boards(None, self.cursor)
        return self._boards

    @property
    def board_members(self):
        """Dictionary of `BoardMember` objects, indexed by Person doc ID."""

        if not hasattr(self, "_board_members"):
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
            self._board_members = {}
            for row in query.execute(self.cursor).fetchall():
                self._board_members[row.person_id] = BoardMember(self, row)
        return self._board_members

    @property
    def caption(self):
        """What we display at the top of the report."""

        if not hasattr(self, "_caption"):
            if self.historical:
                title = "Summary Mailer History Report ({} - {})"
                title = title.format(self.start, self.end)
            elif self.show == self.LAST:
                title = "Summary Mailer Report (Last)"
            else:
                title = "Summary Mailer Report (Last Checked In)"
            board_name = self.boards[self.board].name
            self._caption = f"{title} - {board_name} - {date.today()}"
        return self._caption

    @property
    def columns(self):
        """Headers we display at the top of each report table column."""

        if not hasattr(self, "_columns"):
            self._columns = []
            for i, header in enumerate(self.HEADERS):
                opts = dict(width=f"{self.WIDTHS[i]:d}px")
                self._columns.append(self.Reporter.Column(header, **opts))
        return self._columns

    @property
    def end(self):
        """End of the report's date range."""

        if not hasattr(self, "_end"):
            try:
                value = self.fields.getvalue("end", str(date.today()))
                self._end = self.parse_date(value)
            except Exception:
                self.bail("Invalid date")
        return self._end

    @property
    def flavor(self):
        """Is this the 'standard' or the 'historical' version of the report?"""

        if not hasattr(self, "_flavor"):
            self._flavor = self.fields.getvalue("flavor", "standard")
        return self._flavor

    @property
    def format(self):
        """This is an Excel report."""
        return "excel"

    @property
    def historical(self):
        """True if we're running the historical flavor of the report."""

        if not hasattr(self, "_historical"):
            self._historical = "histor" in self.flavor
        return self._historical

    @property
    def mailers(self):
        """The documents on which we're reporting.

        Don't eliminate the check of self.board_members at the top.
        It's necessary to populate the temporary tables before they're
        used.
        """

        if not hasattr(self, "_mailers"):
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
                self._mailers = mailers
            else:
                self._mailers = [Mailer(self, v[0]) for v in mailers.values()]
        return self._mailers

    @property
    def order(self):
        """How should we sort the report?"""

        if not hasattr(self, "_order"):
            self._order = self.fields.getvalue("sort", self.MEMBER_SORT)
            if self._order not in [values[0] for values in self.SORTS]:
                self.bail()
        return self._order

    @property
    def recipients(self):
        """Cached lookup of mailer recipient names by CDR Person ID.

        This is an alias for the base class method which does cached
        lookup of document titles.
        """
        return self.doc_titles

    @property
    def rows(self):
        """One for each mailer in the report."""

        if not hasattr(self, "_rows"):
            self._rows = []
            for mailer in sorted(self.mailers):
                self._rows.append([
                    self.Reporter.Cell(mailer.id, center=True),
                    mailer.recipient,
                    mailer.summary,
                    self.Reporter.Cell(mailer.sent, center=True),
                    self.Reporter.Cell(mailer.response, center=True),
                    "\n".join(mailer.changes),
                    "\n".join(mailer.comments),
                ])
        return self._rows

    @property
    def sheet_name(self):
        """String for the report's tab."""

        if self.historical:
            return "Summary Mailer History Report"
        return "Summary Mailer Report"

    @property
    def show(self):
        """Last mailer or last checked-in mailer?"""

        if not hasattr(self, "_show"):
            self._show = self.fields.getvalue("show", self.LAST)
            if self._show not in [values[0] for values in self.SHOW]:
                self.bail()
        return self._show

    @property
    def start(self):
        """Beginning of the report's date range."""

        if not hasattr(self, "_start"):
            value = self.fields.getvalue("start", "2000-01-01")
            try:
                self._start = self.parse_date(value)
            except Exception:
                self.bail("Invalid date")
        return self._start

    @property
    def subtitle(self):
        """What we display below the main banner."""

        if not hasattr(self, "_subtitle"):
            if self.historical:
                self._subtitle = "Summary Mailer History Report"
            else:
                self._subtitle = "Summary Mailer Report"
        return self._subtitle

    @property
    def summaries(self):
        """Cached lookup of PDQ summary title by CDR document ID."""

        if not hasattr(self, "_summaries"):
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
            self._summaries = Summaries(self)
        return self._summaries

    @property
    def title(self):
        """Depends on whether we're showing the form or the report."""

        if self.request == self.SUBMIT:
            return self.subtitle
        return self.TITLE

class BoardMember:
    """Information about one of the PDQ board's members."""

    def __init__(self, control, row):
        """Capture the caller's information.

        Pass:
            control - access to the database and the report settings
            row - CDR document IDs for the board member
        """

        self.__control = control
        self.__row = row

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

    @property
    def member_id(self):
        """Integer ID for the board member's CDR `PDQBoardMemberInfo` doc."""
        return self.__row.member_id

    @property
    def person_id(self):
        """Integer ID for the board member's CDR `Person` document."""
        return self.__row.person_id

    @property
    def terms(self):
        """Membership terms for the board member."""

        if not hasattr(self, "_terms"):
            self._terms = []
            doc = Doc(self.__control.session, id=self.member_id)
            for node in doc.root.findall("BoardMembershipDetails"):
                term = self.MembershipTerm(node)
                if term.board == self.__control.board and term.start:
                    self._terms.append(term)
        return self._terms

    class MembershipTerm:
        """Date range and board ID for a PDQ board membership term."""

        def __init__(self, node):
            """Remember the caller's value.

            Pass:
                node - XML doc node from which the properties can be pulled
            """

            self.__node = node

        @property
        def board(self):
            """CDR Organization document integer ID for the PDQ board."""

            if not hasattr(self, "_board"):
                try:
                    ref = self.__node.find("BoardName").get(Control.CDR_REF)
                    self._board = Doc.extract_id(ref)
                except Exception:
                    self._board = None
            return self._board

        @property
        def end(self):
            """When this membership term ended, if applicable."""

            if not hasattr(self, "_end"):
                self._end = None
                node = self.__node.find("TerminationDate")
                if node is not None and node.text is not None:
                    self._end = node.text
            return self._end

        @property
        def start(self):
            """When this membership term started."""

            if not hasattr(self, "_start"):
                self._start = None
                node = self.__node.find("TermStartDate")
                if node is not None and node.text is not None:
                    self._start = node.text
            return self._start


class Mailer:
    """Information need for a single row in the report."""

    def __init__(self, control, id):
        """Remember the caller's values.

        Pass:
            control - access to the database and the report settings
            id - integer for the unique ID of the CDR `Mailer` document
        """

        self.__control = control
        self.__id = id

    def __lt__(self, other):
        """Sorting depends on the `key` property, determined by report type."""
        return self.key < other.key

    @property
    def changes(self):
        """Categories of changes reflected in the recipient's response."""

        if not hasattr(self, "_changes"):
            self._changes = []
            for node in self.doc.root.findall("Response/ChangesCategory"):
                change = node.text.strip() if node.text else ""
                if change:
                    self._changes.append(change)
        return self._changes

    @property
    def comments(self):
        """Additional notes supplied byu the mailer recipient."""

        if not hasattr(self, "_comments"):
            self._comments = []
            for node in self.doc.root.findall("Response/Comment"):
                comment = node.text.strip() if node.text else ""
                if comment:
                    self._comments.append(comment)
        return self._comments

    @property
    def doc(self):
        """`Doc` object for the mailer."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.__control.session, id=self.id)
        return self._doc

    @property
    def id(self):
        """CDR document ID integer for the mailer."""
        return self.__id

    @property
    def key(self):
        """Sorting support, adjusted for the type of report."""

        if not hasattr(self, "_key"):
            if self.__control.order == Control.MEMBER_SORT:
                self._key = self.recipient.lower(), self.summary.lower()
            else:
                self._key = self.summary.lower(), self.recipient.lower()
        return self._key

    @property
    def recipient(self):
        """Name of the person who got the mailer."""

        if not hasattr(self, "_recipient"):
            node = self.doc.root.find("Recipient")
            try:
                doc_id = Doc.extract_id(node.get(Control.CDR_REF))
                self._recipient = self.__control.recipients[doc_id]
            except Exception:
                self._recipient = None
        return self._recipient

    @property
    def response(self):
        """When the recipient's response was received."""

        if not hasattr(self, "_response"):
            self._response = None
            for node in self.doc.root.findall("Response/Received"):
                if node.text:
                    self._response = node.text.strip()[:10]
        return self._response

    @property
    def sent(self):
        """The date the summary mailer was mailed."""

        if not hasattr(self, "_sent"):
            self._sent = None
            node = self.doc.root.find("Sent")
            if node is not None and node.text is not None:
                self._sent = node.text[:10]
        return self._sent

    @property
    def summary(self):
        """Document title of the PDQ summary behind this mailer."""

        if not hasattr(self, "_summary"):
            node = self.doc.root.find("Document")
            try:
                doc_id = Doc.extract_id(node.get(Control.CDR_REF))
                self._summary = self.__control.summaries[doc_id]
            except Exception:
                self._summary = None
        return self._summary


if __name__ == "__main__":
    """Don't execute script if loaded as a module."""
    Control().run()
