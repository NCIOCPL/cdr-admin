#----------------------------------------------------------------------
#
# $Id$
#
# Report of history of changes for a board's summaries
#
# Rewritten July 2015 as part of a security sweep.
#
#----------------------------------------------------------------------
import cdr
import cdrdb
import datetime
import cgi
import cdrcgi
import re
import lxml.etree as etree

class Control(cdrcgi.Control):
    AUDIENCES = ("Health Professionals", "Patients")
    DOCTYPE = "<!DOCTYPE html>"
    def __init__(self):
        cdrcgi.Control.__init__(self, "Changes To Summaries Report")
        end = datetime.date.today()
        start = end - datetime.timedelta(7)
        self.board = self.fields.getvalue("board", "All")
        self.audience = self.fields.getvalue("audience", self.AUDIENCES[0])
        self.start = self.fields.getvalue("start", str(start))
        self.end = self.fields.getvalue("end", str(end))
        self.boards = self.get_boards()
        if self.request and self.request not in self.buttons:
            cdrcgi.bail()
        if self.board != "All" and not self.board.isdigit():
            cdrcgi.bail()
        msg = cdrcgi.TAMPERING
        cdrcgi.valParmVal(self.audience, val_list=self.AUDIENCES, msg=msg)
        cdrcgi.valParmDate(self.start, msg=msg)
        cdrcgi.valParmDate(self.end, msg=msg)
        if self.end < self.start:
            cdrcgi.bail("End date cannot precede start date.")

    def populate_form(self, form):
        "Fill in the fields for requesting the report"
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Select PDQ Board For Report"))
        form.add_select("board", "Board", ["All"] + list(self.boards))
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Select Audience"))
        for value in self.AUDIENCES:
            label = value[:-1] # Trim plural 's'
            form.add_radio("audience", label, value, onclick=None)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Date Last Modified Range"))
        form.add_date_field("start", "Start Date", value=str(self.start))
        form.add_date_field("end", "End Date", value=str(self.end))
        form.add("</fieldset>")

    def show_report(self):
        "Generate an HTML report that can be pasted into MS Word"
        B = cdrcgi.Page.B
        title = "Changes to Summaries Report - %s" % datetime.date.today()
        css = self.get_common_css()
        date_range = B.BR()
        date_range.tail = "From %s to %s" % (self.start, self.end)
        head = B.HEAD(B.META(charset="utf-8"), B.TITLE(title), B.STYLE(css))
        body = B.BODY(B.H1("Changes to Summaries Report", date_range))
        if self.board == "All":
            boards = [Board(self, *board) for board in self.boards]
        else:
            board_id = int(self.board)
            board_name = dict(self.boards).get(board_id)
            if not board_name:
                raise Exception(cdrcgi.TAMPERING)
            boards = [Board(self, board_id, board_name)]
        for board in boards:
            board.show(body)
        page = B.HTML(head, body)
        print "Content-type: text/html\n"
        print etree.tostring(page, method="html", pretty_print=True,
                             doctype=self.DOCTYPE, encoding="utf-8")
    def get_boards(self):
        "Fetch IDs and names of the PDQ editorial boards (for piclist)"
        n_path = "/Organization/OrganizationNameInformation/OfficialName/Name"
        t_path = "/Organization/OrganizationType"
        query = cdrdb.Query("query_term n", "n.doc_id", "n.value")
        query.join("query_term t", "t.doc_id = n.doc_id")
        query.where(query.Condition("n.path", n_path))
        query.where(query.Condition("t.path", t_path))
        query.where(query.Condition("t.value", "PDQ Editorial Board"))
        query.order("n.value")
        return query.execute(self.cursor, timeout=300).fetchall()

    @staticmethod
    def get_common_css():
        "Load and customize the style rules from the repository"
        script = """\
<?xml version="1.0"?>
<xsl:transform           xmlns:xsl = "http://www.w3.org/1999/XSL/Transform"
                           version = "1.0"
                         xmlns:cdr = "cips.nci.nih.gov/cdr"
           exclude-result-prefixes = "cdr">
 <xsl:output                method = "html"/>
 <xsl:include                 href = "cdr:name:Module: STYLE Default"/>
 <xsl:template               match = "/">
  <style type='text/css'>
   <xsl:call-template         name = "defaultStyle"/>
   h1       { font-family: Arial, sans-serif; font-size: 16pt;
              text-align: center; font-weight: bold; }
   h2       { font-family: Arial, sans-serif; font-size: 14pt;
              text-align: center; font-weight: bold; }
   h1.left  { font-family: Arial, sans-serif; font-size: 16pt;
              text-align: left; font-weight: bold; }
   h2.left  { font-family: Arial, sans-serif; font-size: 14pt;
              text-align: left; font-weight: bold; }
   td.hdg   { font-family: Arial, sans-serif; font-size: 16pt;
              font-weight: bold; }
   p        { font-family: Arial, sans-serif; font-size: 12pt; }
   body     { font-family: Arial; font-size: 12pt; }
   span.SectionRef { text-decoration: underline; font-weight: bold; }
   .summary { border: 2px solid black; text-align: left; }
   .board   { margin-top: 40px; }
   .changes { margin-bottom: 40px; }
  </style>
 </xsl:template>
</xsl:transform>
"""
        response = cdr.filterDoc('guest', script, doc="<dummy/>", inline=True)
        if isinstance(response, basestring):
            cdrcgi.bail("Failure loading common CSS style information: %s" %
                        response)
        return response[0]

class Board:
    "PDQ board to be showed on the report"
    def __init__(self, control, doc_id, name):
        self.control = control
        self.doc_id = doc_id
        self.name = name
        self.summaries = []
        a_path = "/Summary/SummaryMetaData/SummaryAudience"
        b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        query = cdrdb.Query("query_term a", "a.doc_id")
        query.join("query_term b", "b.doc_id = a.doc_id")
        query.where(query.Condition("a.path", a_path))
        query.where(query.Condition("b.path", b_path))
        query.where(query.Condition("a.value", control.audience))
        query.where(query.Condition("b.int_val", doc_id))
        for row in query.execute(control.cursor).fetchall():
            summary = Summary(control, row[0])
            if summary.changes is not None:
                self.summaries.append(summary)

    def show(self, body):
        "If the board has summaries with changes in the date range, show them"
        if self.summaries:
            B = cdrcgi.Page.B
            audience = B.BR()
            audience.tail = self.control.audience
            body.append(B.H2(self.name, audience, B.CLASS("left board")))
            for summary in sorted(self.summaries):
                summary.show(body)

class Summary:
    "One of the cancer topic summaries for a PDQ board"
    PATTERN = re.compile("<DateLastModified[^>]*>([^<]+)</DateLastModified>")
    def __init__(self, control, doc_id):
        self.doc_id = doc_id
        self.changes = None
        query = cdrdb.Query("document", "title")
        query.where(query.Condition("id", doc_id))
        rows = query.execute(control.cursor).fetchall()
        self.title = rows[0][0].split(";")[0]
        query = cdrdb.Query("publishable_version", "num").order("num DESC")
        query.where(query.Condition("id", doc_id))
        versions = [row[0] for row in query.execute(control.cursor).fetchall()]
        html = ""
        for version in versions:
            query = cdrdb.Query("doc_version", "xml", "dt")
            query.where(query.Condition("id", doc_id))
            query.where(query.Condition("num", version))
            xml, date = query.execute(control.cursor).fetchone()
            match = self.PATTERN.search(xml)
            if match:
                last_modified = match.group(1)
                if control.start <= last_modified <= control.end:
                    date = "%s/%s/%s" % (date[5:7], date[8:10], date[:4])
                    filt = ["name:Summary Changes Report"]
                    resp = cdr.filterDoc("guest", filt, doc=xml)
                    if isinstance(resp, basestring):
                        error = "Failure parsing CDR%d V%d" % (doc_id, version)
                        raise Exception(error)
                    html = resp[0].replace("@@PubVerDate@@", date).strip()
                    break
        if html:
            div = "<div class='changes'>%s</div>" % html
            self.changes = cdrcgi.lxml.html.fromstring(div)

    def show(self, page):
        "Add the summary to the HTML object"
        B = cdrcgi.Page.B
        doc_id = B.BR()
        doc_id.tail = cdr.normalize(self.doc_id)
        page.append(B.H2(self.title, doc_id, B.CLASS("summary")))
        page.append(self.changes)

    def __cmp__(self, other):
        "Support intelligent sorting of the summaries"
        return cmp(self.title, other.title)

if __name__ == "__main__":
    "Allow documentation and lint tools to import without side effects"
    Control().run()
