#!/usr/bin/env python

"""Report on the most recent changes made to PDQ summary documents.

The users have insisted that we keep all the tables for the report
on a single worksheet, so we can't use the standard report harness
to generate the Excel file.
"""

from datetime import date, timedelta
from functools import cached_property
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
            # English, Spanish summary types (boards): est, sst.
            field_name = f"{language[0].lower()}st"
            if self.request:
                ids = self.fields.getlist(field_name)
                checked = "all" in ids
            else:
                ids = []
                checked = language == "English"
            classes = f"{field_name}-individual"
            fieldset = page.fieldset(language)
            opts = dict(value="all", checked=checked)
            fieldset.append(page.checkbox(field_name, **opts))
            for name, id in boards:
                opts = dict(value=id, label=name, classes=classes)
                if str(id) in ids:
                    opts["checked"] = True
                fieldset.append(page.checkbox(field_name, **opts))
            page.form.append(fieldset)
        fieldset = page.fieldset("Include")
        for value, label in self.OPTS:
            checked = value in self.opts
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.checkbox("opt", **opts))
        page.form.append(fieldset)
        if self.request:
            start, end = self.user_start, self.user_end
        else:
            end = date.today()
            start = end - timedelta(6)
        fieldset = page.fieldset("Report by Date Last Modified (User)")
        opts = dict(value=start, label="Start Date")
        fieldset.append(page.date_field("u-start", **opts))
        opts = dict(value=end, label="End Date")
        fieldset.append(page.date_field("u-end", **opts))
        page.form.append(fieldset)
        start = end = None
        if self.request:
            start, end = self.system_start, self.system_end
        fieldset = page.fieldset("Report by Date Last Modified (System)")
        opts = dict(label="Start Date", value=start)
        fieldset.append(page.date_field("s-start", **opts))
        opts = dict(label="End Date", value=end)
        fieldset.append(page.date_field("s-end", **opts))
        page.form.append(fieldset)
        page.head.append(page.B.SCRIPT(src=self.SCRIPT))

    def show_report(self):
        """Override base class version to get all tables on the same sheet."""

        if not self.ready:
            self.show_form()
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

    @cached_property
    def audience(self):
        """Health professional or patient or both."""

        audience = self.fields.getvalue("audience")
        if not audience:
            return self.AUDIENCES
        if audience not in self.AUDIENCES:
            self.bail()
        return [audience]

    @cached_property
    def blocked(self):
        """Include documents which are blocked."""
        return "blocked" in self.opts

    @cached_property
    def board(self):
        """Board(s) selected for the report.

        In a weird requirements twist, users need to be able to mix and
        match languages and boards. So, for example, they can ask for a
        report on English adult treatment summaries and Spanish child
        treatment summaries.

        We're building a dictionary of summaries. The key for each member
        of the dictionary is the summary ID, and the value is a sequence
        of language names.

        The cryptic field names "est" and "sst" represent the fields for
        English and Spanish summary types (this report uses "summary type"
        as a synonym for "board").
        """

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
        return [Board(self, id, boards[id]) for id in boards]

    @cached_property
    def boards(self):
        """Index of PDQ Editorial boards by CDR Organization document ID."""
        return self.get_boards()

    @cached_property
    def caption(self):
        """Rows at the very top of the report."""
        return self.report_title, self.date_range

    @cached_property
    def caption_style(self):
        """How we display the lines at the top of each table."""

        return dict(
            alignment=self.workbook.left,
            font=self.workbook.bold,
        )

    @cached_property
    def center(self):
        """Cell style for most data cells in the report."""

        opts = dict(
            horizontal="center",
            vertical="top",
            wrap_text=True,
        )
        return dict(
            alignment=Alignment(**opts),
            font=Font(size=10),
        )

    @cached_property
    def columns(self):
        """Column headers, depending on the report type."""

        columns = [
            "DocID",
            "Summary Title",
            "Date Last Modified",
            "Last Modify Action Date (System)",
            "LastV Publish?",
            "User",
        ]
        if self.report_type == self.SYSTEM_REPORT:
            columns[2:2] = ["Type", "Aud", "Last Comment"]
        return columns

    @cached_property
    def date_range(self):
        """Second line of the report caption."""

        if self.report_type == self.USER_REPORT:
            start, end = self.user_start, self.user_end
        else:
            start, end = self.system_start, self.system_end
        if start:
            if end:
                return f"{start} - {end}"
            else:
                return f"Since {start}"
        elif end:
            return f"Through {end}"
        else:
            return "All dates"

    @cached_property
    def date_style(self):
        """How we display the report date."""

        return dict(
            alignment=self.workbook.left,
            font=Font(bold=True, size=10),
        )

    @cached_property
    def default_audience(self):
        """Make sure the form doesn't lose the user's selection."""
        return self.fields.getvalue("audience")

    @cached_property
    def header_style(self):
        """How we display the column headers."""

        opts = dict(
            horizontal="center",
            vertical="bottom",
            wrap_text=True,
        )
        return dict(
            alignment=Alignment(**opts),
            font=self.workbook.bold,
        )

    @cached_property
    def left(self):
        """Cell style for comments and titles."""

        opts = dict(
            horizontal="left",
            vertical="top",
            wrap_text=True,
        )
        return dict(
            alignment=Alignment(**opts),
            font=Font(size=10),
        )

    @cached_property
    def link_style(self):
        """Cell style for hyperlinks."""

        opts = dict(
            horizontal="center",
            vertical="top",
            wrap_text=True,
        )
        return dict(
            alignment=Alignment(**opts),
            font=Font(size=10, color="000000FF", underline="single"),
        )

    @cached_property
    def main_caption_style(self):
        """How we display the lines at the top of the report sheet."""

        return dict(
            alignment=self.workbook.center,
            font=Font(bold=True, size=12),
        )

    @cached_property
    def modules(self):
        """Include summary modules."""
        return "modules" in self.opts

    @cached_property
    def opts(self):
        """Additional options for refining the report criteria."""
        return set(self.fields.getlist("opt"))

    @cached_property
    def ready(self):
        """True if we have everything we need."""

        if not self.board:
            message = "No summary types selected."
            self.alerts.append(dict(message=message, type="error"))
            return False
        if not any(self.board):
            message = "No summaries match the report criteria."
            self.alerts.append(dict(message=message, type="warning"))
            return False
        return True

    @cached_property
    def report_title(self):
        """Top caption line."""

        if self.report_type == self.USER_REPORT:
            return "Summary Date Last Modified (User) Report"
        else:
            return "Summary Last Modified Date (System) Report"

    @cached_property
    def report_type(self):
        """Date fields determine whether this is a system or a user report."""

        if self.system_start or self.system_end:
            return self.SYSTEM_REPORT
        return self.USER_REPORT

    @cached_property
    def same_window(self):
        """Control when new browser tabs are opened."""
        return [self.SUBMIT] if self.request else []

    @cached_property
    def system_end(self):
        """End date for system version of the report."""

        value = self.fields.getvalue("s-end")
        try:
            return self.parse_date(value)
        except Exception:
            self.bail("invalid date")

    @cached_property
    def system_start(self):
        """Start date for system version of the report."""

        value = self.fields.getvalue("s-start")
        try:
            return self.parse_date(value)
        except Exception:
            self.bail("invalid date")

    @cached_property
    def unpublished(self):
        """Include documents if they haven't been sent to cancer.gov."""
        return "unpub" in self.opts

    @cached_property
    def user_end(self):
        """End date for user version of the report."""

        value = self.fields.getvalue("u-end")
        try:
            return self.parse_date(value)
        except Exception:
            self.bail("invalid date")

    @cached_property
    def user_start(self):
        """Start date for user version of the report."""

        value = self.fields.getvalue("u-start")
        try:
            return self.parse_date(value)
        except Exception:
            self.bail("invalid date")

    @cached_property
    def widths(self):
        """How wide should each column be?"""

        widths = [12, 50, 15, 15, 10, 15]
        if self.report_type == self.SYSTEM_REPORT:
            widths[2:2] = [15, 7, 50]
        return widths

    @cached_property
    def workbook(self):
        """Excel workbook for the report."""

        workbook = Excel(self.SUBTITLE, wrap=True, stamp=True)
        workbook.add_sheet("DLM Report")
        return workbook


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

        self.control = control
        self.id = id
        self.languages = languages

    def __len__(self):
        """How many summaries did we find?"""

        count = 0
        for key in self.summaries:
            count += len(self.summaries[key])
        return count

    def add_tables(self, row):
        book = self.control.workbook
        header_style = self.control.header_style
        caption_style = self.control.caption_style
        link_style = self.control.link_style
        left = self.control.left
        center = self.control.center
        full = f"PDQ {self.control.boards[self.id]} Editorial Board"
        host = self.control.session.tier.hosts["APPC"]
        id_url = self.VERSION_HISTORY_URL.format(host)
        audit_url = self.AUDIT_URL.format(host)
        system_report = self.control.report_type == Control.SYSTEM_REPORT
        saved_style = link_style if system_report else center
        for key in self.summaries:
            subset = self.summaries[key]
            if subset:
                language, audience = key
                aud = "HP" if audience[0] == "H" else "PAT"
                subtitle = f"{audience.capitalize()}s ({language})"
                book.merge(row, 1, row, len(self.control.columns))
                book.write(row, 1, full, caption_style)
                row += 1
                book.merge(row, 1, row, len(self.control.columns))
                book.write(row, 1, subtitle, caption_style)
                row += 1
                book.sheet.row_dimensions[row].height = 50
                for col, header in enumerate(self.control.columns):
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

    @cached_property
    def summaries(self):
        """Dictionary of summary sets, grouped by language and audience."""

        summaries = {}
        for language in self.languages:
            for audience in self.control.audience:
                key = language, audience
                summaries[key] = self.__select(language, audience)
        return summaries

    def __select(self, language, audience):
        """Assemble the sequence of summaries for this language/audience combo.

        Pass:
            language - English or Spanish
            audience - Patient or Health Professional
        """

        query = self.control.Query("query_term title", *self.FIELDS)
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
        if self.control.unpublished:
            if not self.control.blocked:
                query.join("active_doc", "active_doc.id = title.doc_id")
        else:
            query.outer("pub_proc_cg", "pub_proc_cg.id = title.doc_id")
            options = ["pub_proc_cg.id IS NOT NULL"]
            if self.control.blocked:
                query.join("document", "document.id = title.doc_id")
                options.append("document.active_status = 'I'")
            if self.control.modules:
                options.append("modules.value = 'Yes'")
            query.where(query.Or(*options))
        if not self.control.modules:
            query.where("modules.value IS NULL")

        # Date filtering depends on which flavor of the report was requested.
        if self.control.report_type == Control.USER_REPORT:
            start = self.control.user_start
            end = self.control.user_end
            if start or end:
                if start:
                    query.where(f"last_mod.value >= '{start}'")
                if end:
                    query.where(f"last_mod.value <= '{end} 23:59:59'")
        else:
            start = self.control.system_start
            end = self.control.system_end
            if start or end:
                if start:
                    query.where(f"saved.last_save_date >= '{start}'")
                if end:
                    query.where(f"saved.last_save_date <= '{end} 23:59:59'")

        # Run the query.
        if language == "Spanish":
            self.control.logger.info("summary query:\n%s", query)
        rows = query.execute(self.control.cursor).fetchall()
        args = self.id, language, audience
        self.control.logger.info("board=%r language=%s audience=%s", *args)
        self.control.logger.info("found %d summaries", len(rows))
        return sorted([Summary(self.control, row) for row in rows])


class Summary:
    """Collection of information we need for the report."""

    def __init__(self, control, row):
        """Remember the caller's values."""
        self.control = control
        self.row = row

    def __lt__(self, other):
        """Support sorting the summaries by title."""
        return self.key < other.key

    @cached_property
    def comment(self):
        """Get the comment from the last version of the document."""

        query = self.control.Query("doc_version", "comment")
        query.where(query.Condition("id", self.id))
        query.order("num DESC").limit(1)
        rows = query.execute(self.control.cursor).fetchall()
        return rows[0].comment if rows else None

    @cached_property
    def id(self):
        """CDR document ID for this PDQ summary."""
        return self.row.doc_id

    @cached_property
    def key(self):
        """Sort ordering."""
        return self.title, self.id

    @cached_property
    def last_modified(self):
        """String for the date the users say the summary was last changed."""
        return self.row.last_modified

    @cached_property
    def last_saved(self):
        """Date/time when the system says the document was last saved."""
        return self.row.last_saved

    @cached_property
    def last_version_publishable(self):
        """True if the most recent version is publishable."""

        doc = Doc(self.control.session, id=self.id)
        if doc.last_version is None:
            return None
        last_ver = doc.last_version
        last_pub_ver = doc.last_publishable_version
        return last_ver == last_pub_ver

    @cached_property
    def module(self):
        """True if this summary can be used as a module."""

        if self.row.is_module is not None:
            if self.row.is_module.capitalize() == "Yes":
                return True
        return False

    @cached_property
    def saver(self):
        """Who saved the document last?"""

        query = self.control.Query("doc_last_save s", "u.fullname")
        query.join("doc_save_action a", "a.doc_id = s.doc_id",
                   "s.last_save_date = a.save_date")
        query.join("usr u", "u.id = a.save_user")
        query.where(query.Condition("s.doc_id", self.id))
        rows = query.execute(self.control.cursor).fetchall()
        return rows[0].fullname if rows else None

    @cached_property
    def title(self):
        """String for the title of the PDQ summary."""

        title = self.row.summary_title.strip()
        if self.module:
            title += " [Module]"
        return title

    @cached_property
    def type(self):
        """String for the type of the PDQ summary."""
        return self.row.summary_type


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
