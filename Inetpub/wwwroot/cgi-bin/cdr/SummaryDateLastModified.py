#!/usr/bin/env python

"""Report on the most recent changes made to PDQ summary documents.

The users have insisted that we keep all the tables for the report
on a single worksheet, so we can't use the standard report harness
to generate the Excel file.
"""

from datetime import date, timedelta
from openpyxl.styles import Alignment, Font
from cdrapi.docs import Doc
from cdrcgi import Controller, Excel


class Control(Controller):

    SUBTITLE = "Summary Date Last Modified"
    LOGNAME = "SummaryDateLastModified"
    INCLUDE_ANY_AUDIENCE_CHECKBOX = True
    OPTS = (
        ("modules", "Modules"),
        ("blocked", "Blocked Documents"),
        ("unpub", "Other Unpublished Documents"),
    )
    SCRIPT = "../../js/SummaryDateLastModified.js"
    USER_REPORT = "user"
    SYSTEM_REPORT = "system"

    def populate_form(self, page):
        """Add the field sets to the form page.

        Pass:
            page - object where we store the fields
        """

        self.add_audience_fieldset(page)
        boards = sorted([(name, id) for id, name in self.boards.items()])
        for language in self.LANGUAGES:
            field_name = f"{language[0].lower()}st"
            classes = f"{field_name}-individual"
            fieldset = page.fieldset(language)
            opts = dict(value="all", checked=language == "English")
            fieldset.append(page.checkbox(field_name, **opts))
            for name, id in boards:
                opts = dict(value=id, label=name, classes=classes)
                fieldset.append(page.checkbox(field_name, **opts))
            page.form.append(fieldset)
        fieldset = page.fieldset("Include")
        for value, label in self.OPTS:
            fieldset.append(page.checkbox("opt", value=value, label=label))
        page.form.append(fieldset)
        end = date.today()
        start = end - timedelta(6)
        fieldset = page.fieldset("Report by Date Last Modified (User)")
        opts = dict(value=start, label="Start Date")
        fieldset.append(page.date_field("u-start", **opts))
        opts = dict(value=end, label="End Date")
        fieldset.append(page.date_field("u-end", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Report by Date Last Modified (System)")
        fieldset.append(page.date_field("s-start", label="Start Date"))
        fieldset.append(page.date_field("s-end", label="End Date"))
        page.form.append(fieldset)
        page.head.append(page.B.SCRIPT(src=self.SCRIPT))

    def show_report(self):
        """Override base class version to get all tables on the same sheet."""

        if self.empty:
            self.bail("No summaries match the report criteria")
        row = 1
        book = self.workbook
        for col, width in enumerate(self.widths):
            book.set_width(col+1, width)
        for line in self.caption:
            book.merge(row, 1, row, len(self.columns))
            book.write(row, 1, line, self.main_caption_style)
            row += 1
        book.merge(row, 1, row, len(self.columns))
        book.write(row, 1, f"Report Date: {date.today()}", self.date_style)
        row += 2
        for board in self.board:
            row = board.add_tables(row)
        book.send()

    @property
    def audience(self):
        """Health professional or patient or both."""

        if not hasattr(self, "_audience"):
            audience = self.fields.getvalue("audience")
            if not audience:
                self._audience = self.AUDIENCES
            elif audience not in self.AUDIENCES:
                self.bail()
            else:
                self._audience = [audience]
        return self._audience

    @property
    def blocked(self):
        """Include documents which are blocked."""
        return "blocked" in self.opts

    @property
    def board(self):
        """Board(s) selected for the report.

        In a weird requirements twist, users need to be able to mix and
        match languages and boards. So, for example, they can ask for a
        report on English adult treatment summaries and Spanish child
        treatment summaries.
        """

        if not hasattr(self, "_board"):
            self._board = []
            boards = {}
            for language in self.LANGUAGES:
                ids = self.fields.getlist(f"{language[0].lower()}st")
                if "all" in ids:
                    ids = list(self.boards)
                for id in ids:
                    try:
                        id = int(id)
                    except Exception:
                        self.bail()
                    if id not in self.boards:
                        self.bail()
                    if id not in boards:
                        boards[id] = []
                    boards[id].append(language)
            if not boards:
                self.bail("No summary types selected")
            self._board = [Board(self, id, boards[id]) for id in boards]
        return self._board

    @property
    def boards(self):
        """Index of PDQ Editorial boards by CDR Organization document ID."""

        if not hasattr(self, "_boards"):
            self._boards = self.get_boards()
        return self._boards

    @property
    def caption(self):
        """Rows at the very top of the report."""
        return self.report_title, self.date_range

    @property
    def caption_style(self):
        """How we display the lines at the top of each table."""

        if not hasattr(self, "_caption_style"):
            self._caption_style = dict(
                alignment=self.workbook.left,
                font=self.workbook.bold,
            )
        return self._caption_style

    @property
    def center(self):
        """Cell style for most data cells in the report."""

        if not hasattr(self, "_center"):
            opts = dict(
                horizontal="center",
                vertical="top",
                wrap_text=True,
            )
            self._center = dict(
                alignment=Alignment(**opts),
                font=Font(size=10),
            )
        return self._center

    @property
    def columns(self):
        """Column headers, depending on the report type."""

        if not hasattr(self, "_columns"):
            self._columns = [
                "DocID",
                "Summary Title",
                "Date Last Modified",
                "Last Modify Action Date (System)",
                "LastV Publish?",
                "User",
            ]
            if self.report_type == self.SYSTEM_REPORT:
                self._columns[2:2] = ["Type", "Aud", "Last Comment"]
        return self._columns

    @property
    def empty(self):
        """Check to make sure we have something to report."""
        return not any(self.board)

    @property
    def date_range(self):
        """Second line of the report caption."""

        if not hasattr(self, "_date_range"):
            if self.report_type == self.USER_REPORT:
                start, end = self.user_start, self.user_end
            else:
                start, end = self.system_start, self.system_end
            if start:
                if end:
                    self._date_range = f"{start} - {end}"
                else:
                    self._date_range = f"Since {start}"
            elif end:
                self._date_range = f"Through {end}"
            else:
                self._date_range = "All dates"
        return self._date_range

    @property
    def date_style(self):
        """How we display the report date."""

        if not hasattr(self, "_date_style"):
            self._date_style = dict(
                alignment=self.workbook.left,
                font=Font(bold=True, size=10),
            )
        return self._date_style

    @property
    def header_style(self):
        """How we display the column headers."""

        if not hasattr(self, "_header_style"):
            opts = dict(
                horizontal="center",
                vertical="bottom",
                wrap_text=True,
            )
            self._header_style = dict(
                alignment=Alignment(**opts),
                font=self.workbook.bold,
            )
        return self._header_style

    @property
    def left(self):
        """Cell style for comments and titles."""

        if not hasattr(self, "_left"):
            opts = dict(
                horizontal="left",
                vertical="top",
                wrap_text=True,
            )
            self._left = dict(
                alignment=Alignment(**opts),
                font=Font(size=10),
            )
        return self._left

    @property
    def link_style(self):
        """Cell style for hyperlinks."""

        if not hasattr(self, "_link_style"):
            opts = dict(
                horizontal="center",
                vertical="top",
                wrap_text=True,
            )
            self._link_style = dict(
                alignment=Alignment(**opts),
                font=Font(size=10, color="000000FF", underline="single"),
            )
        return self._link_style

    @property
    def main_caption_style(self):
        """How we display the lines at the top of the report sheet."""

        if not hasattr(self, "_main_caption_style"):
            self._main_caption_style = dict(
                alignment=self.workbook.center,
                font=Font(bold=True, size=12),
            )
        return self._main_caption_style

    @property
    def modules(self):
        """Include summary modules."""
        return "modules" in self.opts

    @property
    def opts(self):
        """Additional options for refining the report criteria."""

        if not hasattr(self, "_opts"):
            self._opts = set(self.fields.getlist("opt"))
        return self._opts

    @property
    def report_title(self):
        """Top caption line."""

        if self.report_type == self.USER_REPORT:
            return "Summary Date Last Modified (User) Report"
        else:
            return "Summary Last Modified Date (System) Report"

    @property
    def report_type(self):
        """Date fields determine whether this is a system or a user report."""

        if not hasattr(self, "_report_type"):
            if self.system_start or self.system_end:
                self._report_type = self.SYSTEM_REPORT
            else:
                self._report_type = self.USER_REPORT
        return self._report_type

    @property
    def system_end(self):
        """End date for system version of the report."""

        if not hasattr(self, "_system_end"):
            value = self.fields.getvalue("s-end")
            try:
                self._system_end = self.parse_date(value)
            except Exception:
                self.bail("invalid date")
        return self._system_end

    @property
    def system_start(self):
        """Start date for system version of the report."""

        if not hasattr(self, "_system_start"):
            value = self.fields.getvalue("s-start")
            try:
                self._system_start = self.parse_date(value)
            except Exception:
                self.bail("invalid date")
        return self._system_start

    @property
    def unpublished(self):
        """Include documents if they haven't been sent to cancer.gov."""
        return "unput" in self.opts

    @property
    def user_end(self):
        """End date for user version of the report."""

        if not hasattr(self, "_user_end"):
            value = self.fields.getvalue("u-end")
            try:
                self._user_end = self.parse_date(value)
            except Exception:
                self.bail("invalid date")
        return self._user_end

    @property
    def user_start(self):
        """Start date for user version of the report."""

        if not hasattr(self, "_user_start"):
            value = self.fields.getvalue("u-start")
            try:
                self._user_start = self.parse_date(value)
            except Exception:
                self.bail("invalid date")
        return self._user_start

    @property
    def widths(self):
        """How wide should each column be?"""

        if not hasattr(self, "_widths"):
            self._widths = [12, 50, 15, 15, 10, 15]
            if self.report_type == self.SYSTEM_REPORT:
                self._widths[2:2] = [15, 7, 50]
        return self._widths

    @property
    def workbook(self):
        """Excel workbook for the report."""

        if not hasattr(self, "_workbook"):
            self._workbook = Excel(self.SUBTITLE, wrap=True, stamp=True)
            self._workbook.add_sheet("DLM Report")
        return self._workbook


class Board:
    """Collection of summaries for the report."""

    AUDIENCE_PATH = "path = '/Summary/SummaryMetaData/SummaryAudience'"
    AUDIT_URL = "https://{}/cgi-bin/cdr/AuditTrail.py?id="
    VERSION_HISTORY_URL = "https://{}/cgi-bin/cdr/DocVersionHistory.py?DocId="
    BOARD_PATH = "path = '/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref'"
    LANGUAGE_PATH = "path = '/Summary/SummaryMetaData/SummaryLanguage'"
    LAST_MOD_PATH = "path = '/Summary/DateLastModified'"
    LAST_MOD_JOIN = "last_mod.doc_id = title.doc_id"
    LAST_MOD_JOIN = LAST_MOD_JOIN, f"last_mod.{LAST_MOD_PATH}"
    MODULE_PATH = "path = '/Summary/@AvailableAsModule'"
    MODULE_JOIN = "modules.doc_id = title.doc_id", f"modules.{MODULE_PATH}"
    TITLE_PATH = "path = '/Summary/SummaryTitle'"
    TYPE_PATH = "path = '/Summary/SummaryMetaData/SummaryType'"
    TRANSLATION_PATH = "path = '/Summary/TranslationOf/@cdr:ref'"
    FIELDS = (
        "title.doc_id AS doc_id",
        "title.value AS summary_title",
        "type.value AS summary_type",
        "last_mod.value AS last_modified",
        "saved.last_save_date AS last_saved",
        "modules.value as is_module",
    )

    def __init__(self, control, id, languages):
        """Remember the caller's values.

        Pass:
            control - access to the report options and the database
            id - CDR Organization document ID integer for the board
            languages - English and/or Spanish
        """

        self.__control = control
        self.__id = id
        self.__languages = languages

    def __len__(self):
        """How many summaries did we find?"""

        if not hasattr(self, "_count"):
            self._count = 0
            for key in self.summaries:
                self._count += len(self.summaries[key])
        return self._count

    def add_tables(self, row):
        book = self.__control.workbook
        header_style = self.__control.header_style
        caption_style = self.__control.caption_style
        link_style = self.__control.link_style
        left = self.__control.left
        center = self.__control.center
        full = f"PDQ {self.__control.boards[self.__id]} Editorial Board"
        host = self.__control.session.tier.hosts["APPC"]
        id_url = self.VERSION_HISTORY_URL.format(host)
        audit_url = self.AUDIT_URL.format(host)
        system_report = self.__control.report_type == Control.SYSTEM_REPORT
        saved_style = link_style if system_report else center
        for key in self.summaries:
            subset = self.summaries[key]
            if subset:
                language, audience = key
                aud = "HP" if audience[0] == "H" else "PAT"
                subtitle = f"{audience.capitalize()}s ({language})"
                book.merge(row, 1, row, len(self.__control.columns))
                book.write(row, 1, full, caption_style)
                row += 1
                book.merge(row, 1, row, len(self.__control.columns))
                book.write(row, 1, subtitle, caption_style)
                row += 1
                book.sheet.row_dimensions[row].height = 50
                for col, header in enumerate(self.__control.columns):
                    book.write(row, col+1, header, header_style)
                row += 1
                for summary in subset:
                    id = summary.id
                    summary_type = summary.type
                    if "COMPLEMENTARY" in summary_type.upper():
                        summary_type = "IACT"
                    cdr_id = f"CDR{id}"
                    doc_link = f'=HYPERLINK("{id_url}{id}", "{cdr_id}")'
                    saved = str(summary.last_saved)[:10]
                    if summary.last_version_publishable is None:
                        lastv_pub = "N/A"
                    elif summary.last_version_publishable:
                        lastv_pub = "Y"
                    else:
                        lastv_pub = "N"
                    col = 1
                    book.write(row, 1, doc_link, link_style)
                    book.write(row, 2, summary.title, left)
                    if system_report:
                        saved = f'=HYPERLINK("{audit_url}{id}", "{saved}")'
                        book.write(row, 3, summary_type, center)
                        book.write(row, 4, aud, center)
                        book.write(row, 5, summary.comment, left)
                        col = 6
                    else:
                        col = 3
                    book.write(row, col, summary.last_modified, center)
                    book.write(row, col+1, saved, saved_style)
                    book.write(row, col+2, lastv_pub, center)
                    book.write(row, col+3, summary.saver, center)
                    row += 1
                row += 1
        return row

    @property
    def id(self):
        """CDR Organization document ID integer for the board."""
        return self.__id

    @property
    def summaries(self):
        """Dictionary of summary sets, grouped by language and audience."""

        if not hasattr(self, "_summaries"):
            self._summaries = {}
            for language in self.__languages:
                for audience in self.__control.audience:
                    key = language, audience
                    self._summaries[key] = self.__select(language, audience)
        return self._summaries

    def __select(self, language, audience):
        """Assemble the sequence of summaries for this language/audience combo.

        Pass:
            language - English or Spanish
            audience - Patient or Health Professional
        """

        query = self.__control.Query("query_term title", *self.FIELDS)
        query.join("query_term audience", "audience.doc_id = title.doc_id")
        query.join("query_term language", "language.doc_id = title.doc_id")
        query.join("query_term type", "type.doc_id = title.doc_id")
        query.join("doc_last_save saved", "saved.doc_id = title.doc_id")
        query.outer("query_term last_mod", *self.LAST_MOD_JOIN)
        query.outer("query_term modules", *self.MODULE_JOIN)
        query.where(f"audience.{self.AUDIENCE_PATH}")
        query.where(f"language.{self.LANGUAGE_PATH}")
        query.where(f"title.{self.TITLE_PATH}")
        query.where(f"type.{self.TYPE_PATH}")
        query.where(query.Condition("audience.value", audience+"s"))
        query.where(query.Condition("language.value", language))

        # Board selection differs for English and Spanish.
        if language == "English":
            query.join("query_term board", "board.doc_id = title.doc_id")
        else:
            query.join("query_term english", "english.doc_id = title.doc_id")
            query.where(f"english.{self.TRANSLATION_PATH}")
            query.join("query_term board", "board.doc_id = english.int_val")
        query.where(f"board.{self.BOARD_PATH}")
        query.where(query.Condition("board.int_val", self.id))

        # OCECDR-4285: add filtering of summary document states. By default,
        # only summaries which have been published to Cancer.gov are included
        # in the report (which would exclude all blocked documents, summaries
        # which are marked 'available as module' and summaries which are new
        # and in progress). Checkboxes are provided to lift some or all of
        # those restrictions. It's complicated, but it works.
        if self.__control.unpublished:
            if not self.__control.blocked:
                query.join("active_doc", "active_doc.id = title.doc_id")
        else:
            query.outer("pub_proc_cg", "pub_proc_cg.id = title.doc_id")
            options = ["pub_proc_cg.id IS NOT NULL"]
            if self.__control.blocked:
                query.join("document", "document.id = title.doc_id")
                options.append("document.active_status = 'I'")
            if self.__control.modules:
                options.append("modules.value = 'Yes'")
            query.where(query.Or(*options))
        if not self.__control.modules:
            query.where("modules.value IS NULL")

        # Date filtering depends on which flavor of the report was requested.
        if self.__control.report_type == Control.USER_REPORT:
            start = self.__control.user_start
            end = self.__control.user_end
            if start or end:
                if start:
                    query.where(f"last_mod.value >= '{start}'")
                if end:
                    query.where(f"last_mod.value <= '{end} 23:59:59'")
        else:
            start = self.__control.system_start
            end = self.__control.system_end
            if start or end:
                if start:
                    query.where(f"saved.last_save_date >= '{start}'")
                if end:
                    query.where(f"saved.last_save_date <= '{end} 23:59:59'")

        # Run the query.
        if language == "Spanish":
            self.__control.logger.info("summary query:\n%s", query)
        rows = query.execute(self.__control.cursor).fetchall()
        args = self.id, language, audience
        self.__control.logger.info("board=%r language=%s audience=%s", *args)
        self.__control.logger.info("found %d summaries", len(rows))
        return sorted([Summary(self.__control, row) for row in rows])


class Summary:
    """Collection of information we need for the report."""

    def __init__(self, control, row):
        """Remember the caller's values."""
        self.__control = control
        self.__row = row

    def __lt__(self, other):
        """Support sorting the summaries by title."""
        return self.key < other.key

    @property
    def comment(self):
        """Get the comment from the last version of the document."""

        if not hasattr(self, "_comment"):
            query = self.__control.Query("doc_version", "comment")
            query.where(query.Condition("id", self.id))
            query.order("num DESC").limit(1)
            rows = query.execute(self.__control.cursor).fetchall()
            self._comment = rows[0].comment if rows else None
        return self._comment

    @property
    def id(self):
        """CDR document ID for this PDQ summary."""
        return self.__row.doc_id

    @property
    def key(self):
        """Sort ordering."""
        return self.title, self.id

    @property
    def last_modified(self):
        """String for the date the users say the summary was last changed."""
        return self.__row.last_modified

    @property
    def last_saved(self):
        """Date/time when the system says the document was last saved."""
        return self.__row.last_saved

    @property
    def last_version_publishable(self):
        """True if the most recent version is publishable."""

        if not hasattr(self, "_last_version_publishable"):
            doc = Doc(self.__control.session, id=self.id)
            if doc.last_version is None:
                self._last_version_publishable = None
            else:
                last_ver = doc.last_version
                last_pub_ver = doc.last_publishable_version
                self._last_version_publishable = last_ver == last_pub_ver
        return self._last_version_publishable

    @property
    def module(self):
        """True if this summary can be used as a module."""

        if not hasattr(self, "_module"):
            self._module = False
            if self.__row.is_module is not None:
                if self.__row.is_module.capitalize() == "Yes":
                    self._module = True
        return self._module

    @property
    def saver(self):
        "Who saved the document last?"""

        if not hasattr(self, "_saver"):
            query = self.__control.Query("doc_last_save s", "u.fullname")
            query.join("doc_save_action a", "a.doc_id = s.doc_id",
                       "s.last_save_date = a.save_date")
            query.join("usr u", "u.id = a.save_user")
            query.where(query.Condition("s.doc_id", self.id))
            rows = query.execute(self.__control.cursor).fetchall()
            self._saver = rows[0].fullname if rows else None
        return self._saver

    @property
    def title(self):
        """String for the title of the PDQ summary."""

        if not hasattr(self, "_title"):
            self._title = self.__row.summary_title.strip()
            if self.module:
                self._title += " [Module]"
        return self._title

    @property
    def type(self):
        """String for the type of the PDQ summary."""
        return self.__row.summary_type


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
