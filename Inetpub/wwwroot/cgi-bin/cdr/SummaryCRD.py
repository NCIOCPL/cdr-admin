#----------------------------------------------------------------------
#
# SummaryCRD.py
# -------------
#
# BZIssue::4648
#   Report to list the Comprehensive Review Dates
# BZIssue::4987 - Problem using Comprehensive Review Date Report
# BZIssue::5273 - Identifying Modules in Summary Reports
# OCECDR-3698 - Failure Running Comprehensive Review Date Report
# Rewritten July 2015 to address security vulnerabilities.
# OCECDR-4286 - Fix bug in review selection
#----------------------------------------------------------------------
import cdr
import cdrcgi
import cdrdb
import cgi
import datetime

class Control:
    "One master class to rule them all."

    SUBMENU = "Report Menu"
    AUDIENCES = ("Health Professional", "Patient")
    LANGUAGES = ("English", "Spanish")

    def __init__(self):
        "Collect and scrub the request parameters"
        fields = cgi.FieldStorage()
        self.session = cdrcgi.getSession(fields)
        self.request = cdrcgi.getRequest(fields)
        self.audience = fields.getvalue("audience")
        self.language = fields.getvalue("lang")
        self.show_all = fields.getvalue("show_all") == "Y"
        self.show_id = fields.getvalue("show_id") == "Y"
        self.excel = fields.getvalue("format") == "excel"
        self.sets = fields.getlist("sets")
        self.included = fields.getvalue("included") or "s"
        self.unpub = fields.getvalue("unpub") == "Y"
        self.title = "CDR Administration"
        self.subtitle = "Summaries Comprehensive Review Dates"
        self.script = "SummaryCRD.py"
        self.buttons = ("Submit", Control.SUBMENU, cdrcgi.MAINMENU)
        self.cursor = cdrdb.connect("CdrGuest").cursor()
        self.boards = cdr.getBoardNames("editorial", "short")
        self.sanitize()

    def run(self):
        "Top-level program logic"
        if self.request == cdrcgi.MAINMENU:
            cdrcgi.navigateTo("Admin.py", session)
        elif self.request == Control.SUBMENU:
            cdrcgi.navigateTo("reports.py", session)
        elif self.request == "Submit":
            self.show_report()
        else:
            self.show_form()

    def show_report(self):
        "Generate an HTML or Excel report"
        #cdrcgi.bail("a")
        columns = []
        if self.show_id:
            columns.append(cdrcgi.Report.Column("CDR ID", width="50px"))
        columns.extend([
            cdrcgi.Report.Column("Summary Title", width="400px"),
            cdrcgi.Report.Column("Date", width="75px"),
            cdrcgi.Report.Column("Status", width="75px"),
            cdrcgi.Report.Column("Comment", width="400px")
        ])
        sets = self.sets
        doc_ids = (not sets or "all" in sets) and self.boards.keys() or sets
        title = "PDQ Summary Comprehensive Review Report"
        now = datetime.date.today()
        subtitle = "%s %s Summaries (%s)" % (self.language, self.audience, now)
        boards = [Board(self, doc_id) for doc_id in doc_ids]
        tables = []
        for board in sorted(boards):
            if self.included in "sa":
                if board.summaries:
                    tables.append(board.to_table(columns))
            if self.included in "ma":
                if board.modules:
                    tables.append(board.to_table(columns, True))
        report = cdrcgi.Report(title, tables, banner=title, subtitle=subtitle)
        report.send(self.excel and "excel" or "html")

    def show_form(self):
        "Put up the page for the report's options"
        opts = {
            "session": self.session,
            "subtitle": self.subtitle,
            "buttons": self.buttons,
            "action": self.script
        }
        page = cdrcgi.Page(self.title, **opts)
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Select Summary Audience"))
        page.add_radio("audience", Control.AUDIENCES[0], Control.AUDIENCES[0],
                       checked=True)
        page.add_radio("audience", Control.AUDIENCES[1], Control.AUDIENCES[1])
        page.add("</fieldset>")
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Display Review Dates"))
        page.add_radio("show_all", "Show only last actual review date", "N",
                       checked=True)
        page.add_radio("show_all", "Show all review dates", "Y")
        page.add("</fieldset>")
        page.add("<fieldset>")
        page.add(page.B.LEGEND("ID Display"))
        page.add_radio("show_id", "Without CDR ID", "N", checked=True)
        page.add_radio("show_id", "With CDR ID", "Y")
        page.add("</fieldset>")
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Version Display"))
        page.add_radio("unpub", "Publishable only", "N", checked=True)
        page.add_radio("unpub", "Publishable and non-publishable", "Y")
        page.add("</fieldset>")
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Summary Language"))
        page.add_radio("lang", Control.LANGUAGES[0], Control.LANGUAGES[0],
                       checked=True)
        page.add_radio("lang", Control.LANGUAGES[1], Control.LANGUAGES[1])
        page.add("</fieldset>")
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Select Summary Set(s)"))
        page.add_checkbox("sets", "All", "all", checked=True)
        for key in sorted(self.boards, key=lambda k: self.boards[k]):
            name = self.boards[key].replace("Editorial Board", "").strip()
            page.add_checkbox("sets", name, str(key), widget_classes="some")
        page.add("</fieldset>")
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Included Documents"))
        page.add_radio("included", "Summaries and modules", "a")
        page.add_radio("included", "Summaries only", "s", checked=True)
        page.add_radio("included", "Modules only", "m")
        page.add("</fieldset>")
        page.add_output_options("html")
        page.add_script("""\
function check_sets(val) {
    if (val == 'all')
        jQuery('.some').prop('checked', false);
    else
        jQuery('#sets-all').prop('checked', false);
}""")
        page.send()

    def sanitize(self):
        "Make sure the CGI form parameters haven't been tampered with"
        if self.audience and self.audience not in Control.AUDIENCES:
            raise Exception("CGI parameter tampering detected")
        if self.language and self.language not in Control.LANGUAGES:
            raise Exception("CGI parameter tampering detected")
        for value in self.sets:
            if not self.sets_value_ok(value):
                raise Exception("CGI parameter tampering detected")
        if self.included not in "asm":
            raise Exception("CGI parameter tampering detected")

    def sets_value_ok(self, value):
        "Make sure a board parameter hasn't been tampered with"
        if value == "all":
            return True
        if not value.isdigit() or int(value) not in self.boards:
            return False
        return True

class Board:
    "Metadata about a single PDQ board and its summaries for this report"
    def __init__(self, control, doc_id):
        self.control = control
        self.doc_id = int(doc_id)
        self.name = control.boards[self.doc_id]
        self.audience = control.audience or Control.AUDIENCES[0]
        self.language = control.language or Control.LANGUAGES[0]
        qt = control.unpub and "query_term" or "query_term_pub"
        b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        query = cdrdb.Query("query_term t", "t.doc_id", "t.value", "m.value")
        query.join("%s a" % qt, "a.doc_id = t.doc_id")
        query.join("%s l" % qt, "l.doc_id = t.doc_id")
        if not control.unpub:
            query.join("active_doc d", "d.id = t.doc_id")
        query.where("t.path = '/Summary/SummaryTitle'")
        query.where("a.path = '/Summary/SummaryMetaData/SummaryAudience'")
        query.where("l.path = '/Summary/SummaryMetaData/SummaryLanguage'")
        query.where(query.Condition("a.value", self.audience + "s"))
        query.where(query.Condition("l.value", self.language))
        if self.language == "English":
            query.join("%s b" % qt, "b.doc_id = t.doc_id")
        else:
            query.join("%s e" % qt, "e.doc_id = t.doc_id")
            query.join("query_term b", "b.doc_id = e.int_val")
            query.where("e.path = '/Summary/TranslationOf/@cdr:ref'")
        query.where(query.Condition("b.path", b_path))
        query.where(query.Condition("b.int_val", doc_id))
        if control.included == "m":
            query.join("%s m" % qt, "m.doc_id = t.doc_id",
                       "m.path = '/Summary/@ModuleOnly' AND m.value = 'Yes'")
        else:
            query.outer("%s m" % qt, "m.doc_id = t.doc_id",
                        "m.path = '/Summary/@ModuleOnly'")
            if control.included == "s":
                query.where("(m.value IS NULL OR m.value <> 'Yes')")
        rows = query.unique().execute(control.cursor).fetchall()
        summaries = [Summary(control, *row) for row in rows]
        self.summaries = [s for s in summaries if not s.module]
        self.modules = [s for s in summaries if s.module]

    def to_table(self, columns, modules=False):
        """
        Create a table showing the board's metadata and comprenehsive reviews.
        """

        name = self.name.replace("Editorial Board", "").strip()
        if modules:
            docs = self.modules
            what = "modules"
        else:
            docs = self.summaries
            what = "summaries"
        opts = {
            "caption": "%s Editorial Board (%s)" % (name, what),
            "sheet_name": name
        }
        if "Complementary" in name:
            opts["sheet_name"] = "IACT" # name is too big
        if modules:
            opts["sheet_name"] += " (m)"
        rows = []
        for doc in sorted(docs):
            reviews = []
            have_actual = False
            i = len(doc.reviews)
            while i > 0:
                i -= 1
                review = doc.reviews[i]
                if self.control.show_all:
                    reviews.insert(0, review)
                elif not have_actual and review.state == "Actual":
                    reviews.insert(0, review)
                    have_actual = True
            span = len(reviews)
            if span < 2:
                span = None
            row = []
            if self.control.show_id:
                row.append(cdrcgi.Report.Cell(doc.doc_id, rowspan=span))
            title = doc.title
            row.append(cdrcgi.Report.Cell(title, rowspan=span))
            if reviews:
                review = reviews[0]
                row.extend([
                    review.date,
                    cdrcgi.Report.Cell(review.state, classes="center"),
                    review.comment or ""
                ])
            else:
                row.extend(["", "", ""])
            rows.append(row)
            for review in reviews[1:]:
                rows.append([
                    review.date,
                    cdrcgi.Report.Cell(review.state, classes="center"),
                    review.comment or ""
                ])
        return cdrcgi.Report.Table(columns, rows, **opts)

    def __cmp__(self, other):
        "Support sorting by board name"
        return cmp(self.name, other.name)

class Summary:
    logged = False
    "Metadata and comprehensive reviews for a single PDQ summary"
    def __init__(self, control, doc_id, title, module):
        self.control = control
        self.doc_id = doc_id
        self.title = title
        self.module = module == "Yes"
        self.reviews = []
        c_path = "/Summary/ComprehensiveReview/Comment"
        d_path = "/Summary/ComprehensiveReview/ComprehensiveReviewDate"
        t_path = d_path + "/@DateType"
        query = cdrdb.Query("query_term d", "d.value", "t.value", "c.value")
        query.join("query_term t", "t.doc_id = d.doc_id",
                   "LEFT(t.node_loc, 4) = LEFT(d.node_loc, 4)")
        query.outer("query_term c", "c.doc_id = d.doc_id",
                    "LEFT(c.node_loc, 4) = LEFT(d.node_loc, 4)",
                    "c.path = '/Summary/ComprehensiveReview/Comment'")
        query.where(query.Condition("d.doc_id", doc_id))
        query.where(query.Condition("d.path", d_path))
        query.where(query.Condition("t.path", t_path))
        rows = query.execute(control.cursor).fetchall()
        self.reviews = sorted([Review(*row) for row in rows])

    def __cmp__(self, other):
        return cmp(self.title.upper(), other.title.upper())

class Review:
    "Information about a single proposed or actual comprehensive review"
    def __init__(self, date, state, comment):
        self.date = date
        self.state = state
        self.comment = comment

    def __cmp__(self, other):
        "Support sorting reviews in chronological order"
        return cmp((self.date, self.state), (other.date, other.state))

if __name__ == "__main__":
    "Allow import (by doc or lint tools, for example) without side effects"
    Control().run()
