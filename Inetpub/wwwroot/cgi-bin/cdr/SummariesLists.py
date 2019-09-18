#----------------------------------------------------------------------
# Report on lists of summaries.
#
# BZIssue::1010 - Initial report
# BZIssue::1011 - Initial report
# BZIssue::3204 - Added count of summaries per board; display fix
# BZIssue::3716 - Unicode encoding cleanup
# BZIssue::5177 - Adding a Table Option to the Summaries Lists Report
# BZIssue::5273 - Identifying Modules in Summary Reports
# JIRA::OCECDR-3721 - Additional blank columns
# OCECDR-3899: Modify Summaries Lists report to display Spanish CAM
#              summaries
# Rewritten July 2015 to eliminate security vulnerabilities
# OCECDR-3991: Modify Summaries List Report to retrieve publishable summaries
# OCECDR-4020: add option to include modules
#----------------------------------------------------------------------------
import cdr
import cdrcgi
from cdrapi import db
import cgi
import datetime

class Control:
    TITLE = "CDR Administration"
    SUBMENU = "Report Menu"
    AUDIENCES = ("Health Professional", "Patient")
    LANGUAGES = ("English", "Spanish")
    def __init__(self):
        "Collect options for the report"
        fields = cgi.FieldStorage()
        self.session = cdrcgi.getSession(fields)
        self.request = cdrcgi.getRequest(fields)
        self.audience = fields.getvalue("audience") or Control.AUDIENCES[0]
        self.language = fields.getvalue("language") or Control.LANGUAGES[0]
        self.show_id = fields.getvalue("show_id") == "Y"
        self.show_all = fields.getvalue("show_all") or "N"
        self.extra = fields.getvalue("extra") or "0"
        self.included = fields.getvalue("included") or "s"
        self.sets = fields.getlist("sets") or ["all"]
        self.subtitle = "Summaries Lists"
        self.script = "SummariesLists.py"
        self.buttons = ("Submit", Control.SUBMENU, cdrcgi.MAINMENU)
        self.boards = cdr.getBoardNames("editorial", "short")
        self.cursor = db.connect(user="CdrGuest").cursor()
        self.sanitize()

    def run(self):
        if self.request == cdrcgi.MAINMENU:
            cdrcgi.navigateTo("Admin.py", self.session)
        elif self.request == Control.SUBMENU:
            cdrcgi.navigateTo("reports.py", self.session)
        elif self.request == "Submit":
            self.show_report()
        else:
            self.show_form()
    def show_report(self):
        columns = []
        if self.show_id:
            columns.append(cdrcgi.Report.Column("CDR ID"))
        columns.append(cdrcgi.Report.Column("Title"))
        if self.extra:
            extra = int(self.extra)
            while extra > 0:
                columns.append(cdrcgi.Report.Column("", width="50px"))
                extra -= 1
        sets = self.sets
        doc_ids = (not sets or "all" in sets) and self.boards.keys() or sets
        title = "PDQ %s %s Summaries" % (self.language, self.audience)
        if self.show_all == "Y":
            title = title + " (all)"
        now = datetime.date.today()
        subtitle = "Report Date: %s" % now
        boards = [Board(self, doc_id) for doc_id in doc_ids]
        tables = []
        for board in sorted(boards):
            if self.included in "sa":
                if board.summaries:
                    tables.append(board.to_table(columns))
            if self.included in "ma":
                if board.modules:
                    tables.append(board.to_table(columns, True))
        #tables = [b.to_table(columns) for b in sorted(boards) if b.summaries]
        report = cdrcgi.Report(title, tables, banner=title, subtitle=subtitle,
                               css="table.report { width: 1024px; }")
        report.send()

    def show_form(self):
        opts = {
            "buttons": self.buttons,
            "action": self.script,
            "subtitle": self.subtitle,
            "session": self.session
        }
        page = cdrcgi.Page(Control.TITLE, **opts)
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Select Summary Audience"))
        page.add_radio("audience", Control.AUDIENCES[0], Control.AUDIENCES[0],
                       checked=True)
        page.add_radio("audience", Control.AUDIENCES[1], Control.AUDIENCES[1])
        page.add("</fieldset>")
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Summary Language"))
        page.add_radio("language", Control.LANGUAGES[0], Control.LANGUAGES[0],
                       checked=True)
        page.add_radio("language", Control.LANGUAGES[1], Control.LANGUAGES[1])
        page.add("</fieldset>")
        page.add("<fieldset>")
        page.add(page.B.LEGEND("ID Display"))
        page.add_radio("show_id", "Without CDR ID", "N", checked=True)
        page.add_radio("show_id", "With CDR ID", "Y")
        page.add("</fieldset>")
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Version Display"))
        page.add_radio("show_all", "Publishable only", "N", checked=True)
        page.add_radio("show_all", "Publishable and non-publishable", "Y")
        page.add("</fieldset>")
        if False:
            page.add("<fieldset>")
            page.add(page.B.LEGEND("Table Options"))
            page.add_radio("table-opts", "Single column, no gridlines",
                           "simple", checked=True)
            page.add_radio("table-opts", "Extra blank columns, show gridlines",
                           "extra")
            page.add_text_field("extra-cols", "Extra Cols", default="1")
            page.add("</fieldset>")
        else:
            page.add('<fieldset id="extra-block">')
            page.add(page.B.LEGEND("Extra Blank Columns"))
            page.add_text_field("extra", "Extra Cols", value="0")
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
        if self.included not in "sam":
            raise Exception("CGI parameter tampering detected")
        if self.audience and self.audience not in Control.AUDIENCES:
            raise Exception("CGI parameter tampering detected")
        if self.language and self.language not in Control.LANGUAGES:
            raise Exception("CGI parameter tampering detected")
        if self.extra and not self.extra.isdigit():
            raise Exception("Number of extra columns must an integer")
        for value in self.sets:
            if not self.sets_value_ok(value):
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
        self.show_all = control.show_all
        b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        cols = ["t.doc_id", "t.value", "m.value"]
        if self.language != "English":
            cols.append("o.value")

        # Including only publishable versions or all versions in output
        # -------------------------------------------------------------
        if self.show_all == 'N':
           pub = '_pub'
        else:
           pub = ''

        query = db.Query("query_term%s t" % pub, *cols).unique()
        query.join("query_term%s a" % pub, "a.doc_id = t.doc_id")
        query.join("query_term%s l" % pub, "l.doc_id = t.doc_id")
        query.join("active_doc d", "d.id = t.doc_id")
        query.where("t.path = '/Summary/SummaryTitle'")
        query.where("a.path = '/Summary/SummaryMetaData/SummaryAudience'")
        query.where("l.path = '/Summary/SummaryMetaData/SummaryLanguage'")
        query.where(query.Condition("a.value", self.audience + "s"))
        query.where(query.Condition("l.value", self.language))
        if self.language == "English":
            query.join("query_term%s b" % pub, "b.doc_id = t.doc_id")
        else:
            query.join("query_term%s e" % pub, "e.doc_id = t.doc_id")
            query.join("query_term%s b" % pub, "b.doc_id = e.int_val")
            query.join("query_term%s o" % pub, "o.doc_id = e.int_val")
            query.where("e.path = '/Summary/TranslationOf/@cdr:ref'")
            query.where("o.path = '/Summary/SummaryTitle'")
        query.where(query.Condition("b.path", b_path))
        query.where(query.Condition("b.int_val", doc_id))
        query.outer("query_term m", "m.doc_id = t.doc_id",
                    "m.path = '/Summary/@ModuleOnly'")
        rows = query.execute(control.cursor).fetchall()
        summaries = [Summary(control, *row) for row in rows]
        self.summaries = [s for s in summaries if not s.module]
        self.modules = [s for s in summaries if s.module]

    def to_table(self, columns, modules=False):
        "Create a table showing the summaries for this board"
        if modules:
            docs = self.modules
            what = (len(docs) == 1) and "module" or "modules"
        else:
            docs = self.summaries
            what = (len(docs) == 1) and "summary" or "summaries"
        opts = { "caption": u"%s (%d %s)" % (self.name, len(docs), what) }
        rows = []
        for doc in sorted(docs):
            row = []
            if self.control.show_id:
                row.append(cdrcgi.Report.Cell(doc.doc_id, classes="center"))
            title = [doc.title]
            if doc.original_title:
                title.append(u"(%s)" % doc.original_title)
            row.append(title)
            while len(row) < len(columns):
                row.append(u"")
            rows.append(row)
        return cdrcgi.Report.Table(columns, rows, **opts)
    def __lt__(self, other):
        return self.name.lower() < other.name.lower()

class Summary:
    logged = False
    "Summary document ID and title(s)"
    def __init__(self, control, doc_id, title, module, original_title=None):
        self.control = control
        self.doc_id = doc_id
        self.title = title
        self.module = module == "Yes"
        self.original_title = original_title

    def __lt__(self, other):
        return self.title.upper() < other.title.upper()

if __name__ == "__main__":
    "Allow import (by doc or lint tools, for example) without side effects"
    Control().run()
