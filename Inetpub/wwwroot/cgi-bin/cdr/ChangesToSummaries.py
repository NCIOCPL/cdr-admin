#!/usr/bin/env python

from cdrcgi import Controller, sendPage
import cdr
import datetime
import lxml.html
from re import compile
from sys import stdout


class Control(Controller):
    """Access to the current login session and report-building tools."""

    SUBTITLE = "Changes To Summaries Report"
    AUDIENCES = ("Health Professionals", "Patients")
    CSS = "/stylesheets/ChangesToSummaries.css"
    NAME_PATH = "/Organization/OrganizationNameInformation/OfficialName/Name"
    TYPE_PATH = "/Organization/OrganizationType"
    INCLUDE = (
        ("a", "Summaries and modules", False),
        ("s", "Summaries only", True),
        ("m", "Modules only", False),
    )

    def populate_form(self, page):
        """Add the fields for requesting the report.

        Pass:
            page - HTMLPage where the fields go
        """

        if self.debug:
            form.add_hidden_field("debug", True)
        end = datetime.date.today()
        start = end - datetime.timedelta(7)
        fieldset = page.fieldset("Select PDQ Board For Report")
        options = ["all", "All"] + self.boards
        fieldset.append(page.select("board", options=["All"]+self.boards))
        page.form.append(fieldset)
        fieldset = page.fieldset("Select Audience")
        checked = True
        for value in self.AUDIENCES:
            opts = dict(value=value, checked=checked)
            fieldset.append(page.radio_button("audience", **opts))
            checked = False
        page.form.append(fieldset)
        fieldset = page.fieldset("Included Documents")
        for value, label, checked in self.INCLUDE:
            opts = dict(checked=checked, value=value, label=label)
            fieldset.append(page.radio_button("include", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Date Last Modified Range")
        fieldset.append(page.date_field("start", value=start))
        fieldset.append(page.date_field("end", value=end))
        page.form.append(fieldset)

    def show_report(self):
        """Generate an HTML report that can be pasted into MS Word."""

        B = self.HTMLPage.B
        m = ""
        if self.include == "m":
            m = " (Modules Only)"
        elif self.include == "s":
            m = " (Excluding Modules)"
        title = f"Changes to Summaries Report{m} - {datetime.date.today()}"
        head = B.HEAD(
            B.META(charset="utf-8"),
            B.TITLE(title),
            B.LINK(href=self.CSS, rel="stylesheet")
        )
        body = B.BODY(
            B.H1(
                f"Changes to Summaries Report{m}",
                B.BR(),
                f"From {self.start} to {self.end}"
            )
        )
        if self.board == "All":
            boards = [Board(self, *board) for board in self.boards]
        else:
            board_id = int(self.board)
            board_name = dict(self.boards).get(board_id)
            if not board_name:
                self.bail()
            boards = [Board(self, board_id, board_name)]
        self.logger.debug("collected %d boards", len(boards))
        args = Summary.VERSIONS_EXAMINED, Summary.SUMMARIES_EXAMINED
        self.logger.debug("examined %d versions in %d summaries", *args)
        non_modules = available_as_module = module_only = 0
        boards_with_summaries = 0
        for board in boards:
            if board.summaries:
                boards_with_summaries += 1
            non_modules += board.non_modules
            available_as_module += board.available_as_module
            module_only += board.module_only
        self.add_totals(body, non_modules, available_as_module, module_only)
        show_subtotals = boards_with_summaries > 1
        for board in boards:
            board.show(body, show_subtotals)
        stdout.buffer.write(b"Content-type: text/html; charset=utf-8\n\n")
        page = B.HTML(head, body)
        page = lxml.html.tostring(page, pretty_print=True, encoding="unicode")
        stdout.buffer.write(page.encode("utf-8"))

    def add_totals(self, body, non_modules, available_as_module, module_only):
        """Add a table with totals (OCECDR-4872)."""

        totals = non_modules + available_as_module + module_only
        B = self.HTMLPage.B
        table = B.TABLE(
            B.TR(
                B.TH("Only usable as standalone summaries:"),
                B.TD(str(non_modules)),
            ),
            B.TR(
                B.TH("Only usable as summary modules:"),
                B.TD(str(module_only)),
            ),
            B.TR(
                B.TH("Can be used standalone or as modules:"),
                B.TD(str(available_as_module)),
            ),
            B.TR(
                B.TH("Total summaries:"),
                B.TD(str(totals)),
            ),
            B.CLASS("totals-table"),
        )
        body.append(table)

    @property
    def audience(self):
        """Audience selected from the form."""
        return self.fields.getvalue("audience")

    @property
    def board(self):
        """Board ID selected from the picklist (or "all")."""
        return self.fields.getvalue("board")

    @property
    def boards(self):
        """IDs and names of the PDQ editorial boards (for picklist)."""

        if not hasattr(self, "_boards"):
            query = self.Query("query_term n", "n.doc_id", "n.value")
            query.join("query_term t", "t.doc_id = n.doc_id")
            query.where(query.Condition("n.path", self.NAME_PATH))
            query.where(query.Condition("t.path", self.TYPE_PATH))
            query.where(query.Condition("t.value", "PDQ Editorial Board"))
            query.order("n.value")
            rows = query.execute(self.cursor).fetchall()
            self._boards = [tuple(row) for row in rows]
        return self._boards

    @property
    def debug(self):
        """Boolean for debugging."""
        return self.fields.getvalue("debug")

    @property
    def end(self):
        """End of the report's date range."""

        if not hasattr(self, "_end"):
            try:
                self._end = self.parse_date(self.fields.getvalue("end"))
            except:
                self.bail()
        return self._end

    @property
    def include(self):
        """Should we include summaries (s), modules (m), or both (a)?"""

        if not hasattr(self, "_include"):
            self._include = self.fields.getvalue("include", "s")
            if self._include not in [values[0] for values in self.INCLUDE]:
                self.bail()
        return self._include

    @property
    def start(self):
        """Beginning of the report's date range."""

        if not hasattr(self, "_start"):
            try:
                self._start = self.parse_date(self.fields.getvalue("start"))
            except:
                self.bail()
        return self._start


class Board:
    """PDQ board to be shown on the report."""

    def __init__(self, control, doc_id, name):
        self.control = control
        self.doc_id = doc_id
        self.name = name
        self.summaries = []
        self.non_modules = self.available_as_module = self.module_only = 0
        a_path = "/Summary/SummaryMetaData/SummaryAudience"
        b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        query = control.Query("query_term a", "a.doc_id")
        query.join("query_term b", "b.doc_id = a.doc_id")
        query.where(query.Condition("a.path", a_path))
        query.where(query.Condition("b.path", b_path))
        query.where(query.Condition("a.value", control.audience))
        query.where(query.Condition("b.int_val", doc_id))
        if control.include == "m":
            query.join("query_term m", "m.doc_id = a.doc_id",
                       "m.path = '/Summary/@ModuleOnly'",
                       "m.value = 'Yes'")
        elif control.include == "s":
            query.outer("query_term m", "m.doc_id = a.doc_id",
                        "m.path = '/Summary/@ModuleOnly'")
            query.where("(m.value IS NULL OR m.value <> 'Yes')")
        for row in query.execute(control.cursor).fetchall():
            summary = Summary(control, row[0])
            if summary.changes is not None:
                self.summaries.append(summary)
                if summary.module_only:
                    self.module_only += 1
                elif summary.available_as_module:
                    self.available_as_module += 1
                else:
                    self.non_modules += 1
        args = len(self.summaries), name
        control.logger.debug("Collected %d summaries for %s", *args)

    def show(self, body, show_subtotals):
        "If the board has summaries with changes in the date range, show them"

        if self.summaries:
            self.control.logger.debug("showing summaries for %s", self.name)
            B = self.control.HTMLPage.B
            audience = B.BR()
            audience.tail = self.control.audience
            body.append(B.H2(self.name, audience, B.CLASS("left board")))
            if show_subtotals:
                self.control.add_totals(body, self.non_modules,
                                        self.available_as_module,
                                        self.module_only)
            for summary in sorted(self.summaries):
                summary.show(body)
                self.control.logger.debug("showing CDR%s", summary.doc_id)


class Summary:
    """One of the cancer topic summaries for a PDQ board."""

    PATTERN = compile("<DateLastModified[^>]*>([^<]+)</DateLastModified>")
    SUMMARIES_EXAMINED = VERSIONS_EXAMINED = 0
    def __init__(self, control, doc_id):
        Summary.SUMMARIES_EXAMINED += 1
        self.control = control
        self.doc_id = doc_id
        self.changes = None
        query = control.Query("document", "title")
        query.where(query.Condition("id", doc_id))
        rows = [tuple(row) for row in query.execute(control.cursor).fetchall()]
        self.title = rows[0][0].split(";")[0]
        query = control.Query("publishable_version", "num")
        query.order("num DESC")
        query.where(query.Condition("id", doc_id))
        #start = datetime.datetime.strptime(control.start, "%Y-%m-%d")
        cutoff = control.start - datetime.timedelta(365)
        end = f"{control.end} 23:59:59"
        query.where(query.Condition("dt", str(cutoff), ">="))
        query.where(query.Condition("dt", end, "<"))
        versions = [row[0] for row in query.execute(control.cursor).fetchall()]
        html = ""
        for version in versions:
            Summary.VERSIONS_EXAMINED += 1
            control.logger.debug("examining CDR%dV%d", doc_id, version)
            query = control.Query("doc_version", "xml", "dt")
            query.where(query.Condition("id", doc_id))
            query.where(query.Condition("num", version))
            xml, date = query.execute(control.cursor).fetchone()
            match = self.PATTERN.search(xml)
            if match:
                last_modified = match.group(1)
                control.logger.debug("DateLastModified: %r", last_modified)
                if str(control.start) <= last_modified <= str(control.end):
                    date = str(date)
                    date = "%s/%s/%s" % (date[5:7], date[8:10], date[:4])
                    filt = ["name:Summary Changes Report"]
                    resp = cdr.filterDoc(control.session, filt, doc=xml)
                    if isinstance(resp, (str, bytes)):
                        error = "Failure parsing CDR%d V%d" % (doc_id, version)
                        raise Exception(error)
                    html = resp[0].replace("@@PubVerDate@@", date).strip()
                    break
        if html:
            div = "<div class='changes'>%s</div>" % html
            self.changes = lxml.html.fromstring(div)

    def show(self, page):
        "Add the summary to the HTML object"
        B = self.control.HTMLPage.B
        doc_id = B.BR()
        doc_id.tail = cdr.normalize(self.doc_id)
        page.append(B.H2(self.title, doc_id, B.CLASS("summary")))
        page.append(self.changes)

    @property
    def available_as_module(self):
        """True if this summary can be used as a module."""

        if not hasattr(self, "_available_as_module"):
            self._available_as_module = False
            query = self.control.Query("query_term", "value")
            query.where("path = '/Summary/@AvailableAsModule'")
            query.where(query.Condition("doc_id", self.doc_id))
            rows = query.execute(self.control.cursor).fetchall()
            if rows and rows[0].value.lower() == 'yes':
                self._available_as_module = True
        return self._available_as_module

    @property
    def module_only(self):
        """True if this summary can be used as a module."""

        if not hasattr(self, "_module_only"):
            self._module_only = False
            query = self.control.Query("query_term", "value")
            query.where("path = '/Summary/@ModuleOnly'")
            query.where(query.Condition("doc_id", self.doc_id))
            rows = query.execute(self.control.cursor).fetchall()
            if rows and rows[0].value.lower() == 'yes':
                self._module_only = True
        return self._module_only

    def __lt__(self, other):
        "Support intelligent sorting of the summaries"
        return self.title.lower() < other.title.lower()


if __name__ == "__main__":
    "Allow documentation and lint tools to import without side effects"
    Control().run()
