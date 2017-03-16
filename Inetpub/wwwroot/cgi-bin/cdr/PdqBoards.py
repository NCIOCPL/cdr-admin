#----------------------------------------------------------------------
# Report on PDQ Board members and topics.
#
# BZIssue::1006
# BZIssue::1007
# JIRA::OCECDR-4060
#----------------------------------------------------------------------

# Standard library modules
import datetime

# Custom/application-specific modules
import cdrcgi
import cdrdb

class Control(cdrcgi.Control):
    "Master processing object"

    AUDIENCES = ("Health professionals", "Patients")
    GROUPINGS = ("topic", "member")
    ORG_NAME = "/Organization/OrganizationNameInformation/OfficialName/Name"
    B_PATH = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
    M_PATH = "/Summary/SummaryMetaData/PDQBoard/BoardMember/@cdr:ref"
    A_PATH = "/Summary/SummaryMetaData/SummaryAudience"

    def __init__(self):
        "Collect and verify the processing parameters."
        cdrcgi.Control.__init__(self, "PDQ Board Report")
        self.boards = self.get_boards()
        self.audience = self.fields.getvalue("audience") or self.AUDIENCES[0]
        self.board = self.fields.getvalue("board")
        self.grouping = self.fields.getvalue("grouping") or self.GROUPINGS[0]
        self.show_id = self.fields.getvalue("show_id") == "Y"
        self.unpub = self.fields.getvalue("show_all") == "Y"
        self.included = self.fields.getvalue("included") or "s"
        self.sanitize()

    def populate_form(self, form):
        "Override the base class method to get our own fields on the form."
        boards = [(v, k) for k, v in self.boards.iteritems()]
        boards = [(doc_id, name) for name, doc_id in sorted(boards)]
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Board and Audience"))
        form.add_select("board", "Board", boards)
        form.add_select("audience", "Audience", self.AUDIENCES)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("ID Display"))
        form.add_radio("show_id", "Without CDR ID", "N", checked=True)
        form.add_radio("show_id", "With CDR ID", "Y")
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Version Display"))
        form.add_radio("show_all", "Publishable only", "N", checked=True)
        form.add_radio("show_all", "Publishable and non-publishable", "Y")
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Report Grouping"))
        form.add_radio("grouping", "Group by Topic", "topic", checked=True)
        form.add_radio("grouping", "Group by Board Member", "member")
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Included Documents"))
        form.add_radio("included", "Summaries and modules", "a")
        form.add_radio("included", "Summaries only", "s", checked=True)
        form.add_radio("included", "Modules only", "m")
        form.add("</fieldset>")

    def show_report(self):
        "Override this method because we have a non-tabular report."

        if not self.board:
            cdrcgi.bail("No board selected.")
        today = datetime.date.today().strftime("%Y-%m-%d")
        grouping = { "topic": "Topic", "member": "Board Member" }[self.grouping]
        opts = {
            "banner": self.title,
            "subtitle": u"Board Report by %s \u2014 %s" % (grouping, today),
            "buttons": (self.SUBMENU, self.ADMINMENU, self.LOG_OUT),
            "action": self.script,
            "body_classes": "report"
        }
        page = cdrcgi.Page(self.PAGE_TITLE, **opts)
        what = { "topic": "Topics", "member": "Reviewers" }[self.grouping]
        board = self.boards[self.board]
        page.add(page.B.H3("%s for PDQ %s (%s)" % (what, board, self.audience)))
        self.summaries = sorted(self.get_summaries())
        if self.grouping == "topic":
            self.show_topics(page)
        else:
            self.show_members(page)
        page.send()

    def get_summaries(self):
        "Collect objects for all of the summaries connected to our board."

        qt = self.unpub and "query_term" or "query_term_pub"
        query = cdrdb.Query("%s b" % qt, "b.doc_id", "m.value")
        query.join("%s a" % qt, "a.doc_id = b.doc_id")
        if not self.unpub:
            query.join("active_doc d", "d.id = b.doc_id")
        query.where("a.path = '%s'" % self.A_PATH)
        query.where(query.Condition("a.value", self.audience))
        query.where("b.path = '%s'" % self.B_PATH)
        query.where(query.Condition("b.int_val", self.board))
        if self.included == "m":
            query.join("%s m" % qt, "m.doc_id = b.doc_id",
                       "m.path = '/Summary/@ModuleOnly' AND m.value = 'Yes'")
        else:
            query.outer("%s m" % qt, "m.doc_id = b.doc_id",
                        "m.path = '/Summary/@ModuleOnly'")
            if self.included == "s":
                query.where("(m.value IS NULL OR m.value <> 'Yes')")
        rows = query.unique().execute(self.cursor).fetchall()
        return [Summary(row[0], row[1] == "Yes", self) for row in rows]

    def show_topics(self, page):
        "Display report by topics. Summary objects do all the work."

        for summary in self.summaries:
            summary.show(page)

    def show_members(self, page):
        """
        Display report by reviewers.

        Extra work to do here:
           1. Find current members of the board who aren't linked to summaries
           2. Populate the summaries member of the Person objects
        """

        doctype = "/PDQBoardMemberInfo/BoardMember"
        details = "/%s/BoardMembershipDetails" % doctype
        m_path = "/%s/BoardMemberName/@cdr:ref" % doctype
        b_path = "%s/BoardName/@cdr:ref" % details
        c_path = "%s/CurrentMember" % details
        query = cdrdb.Query("query_term m", "m.int_val")
        query.join("query_term b", "b.doc_id = m.doc_id")
        query.join("query_term c",
                   " AND ".join(("c.doc_id = m.doc_id",
                                 "LEFT(b.node_loc, 4) = LEFT(m.node_loc, 4)")))
        query.where("m.path = '%s'" % m_path)
        query.where("b.path = '%s'" % b_path)
        query.where("c.path = '%s'" % c_path)
        query.where("c.value = 'Yes'")
        rows = query.execute(self.cursor).fetchall()
        for row in rows:
            if row[0] not in Summary.persons:
                Summary.persons[row[0]] = Summary.Person(row[0], self)
        for summary in self.summaries:
            for member in summary.members:
                member.summaries.append(summary)
        for member in sorted(Summary.persons.values()):
            member.show(page)

    def sanitize(self):
        "Make sure no one is trying to hack us."

        if self.board:
            try:
                self.board = int(self.board)
            except:
                cdrcgi.bail(cdrcgi.TAMPERING)
            if self.board not in self.boards:
                cdrcgi.bail(cdrcgi.TAMPERING)
        if self.audience not in self.AUDIENCES:
            cdrcgi.bail(cdrcgi.TAMPERING)
        if self.grouping not in self.GROUPINGS:
            cdrcgi.bail(cdrcgi.TAMPERING)
        if self.included not in "msa":
            cdrcgi.bail(cdrcgi.TAMPERING)

    def get_boards(self):
        "Get a dictionary of the active boards (indexed by CDR document ID)."

        query = cdrdb.Query("query_term n", "n.doc_id", "n.value")
        query.join("query_term t", "t.doc_id = n.doc_id")
        query.join("active_doc a", "a.id = n.doc_id")
        query.where("t.path = '/Organization/OrganizationType'")
        query.where("t.value LIKE 'PDQ%Board'")
        query.where("n.path = '%s'" % self.ORG_NAME)
        rows = query.execute(self.cursor).fetchall()
        boards = {}
        for org_id, name in rows:
            if name.startswith("PDQ "):
                name = name[4:]
            boards[org_id] = name
        return boards

class Summary:
    "Information needed for one summary (a.k.a. Topic) for the report."

    persons = {}
    "Dictionary of all the board members for the report."

    def __init__(self, doc_id, is_module, control):
        """
        Find all the board members assigned to review this summary
        for the selected board.
        """

        self.is_module = is_module
        self.control = control
        self.doc_id = doc_id
        query = cdrdb.Query("query_term", "value")
        query.where(query.Condition("doc_id", doc_id))
        query.where("path = '/Summary/SummaryTitle'")
        rows = query.execute(control.cursor).fetchall()
        self.title = rows and rows[0][0] or "NO TITLE FOUND"
        query = cdrdb.Query("query_term m", "m.int_val")
        query.join("query_term b",
                   " AND ".join(("b.doc_id = m.doc_id",
                                 "LEFT(b.node_loc, 8) = LEFT(m.node_loc, 8)")))
        query.where("b.path = '%s'" % control.B_PATH)
        query.where("m.path = '%s'" % control.M_PATH)
        query.where(query.Condition("b.int_val", control.board))
        query.where(query.Condition("b.doc_id", doc_id))
        rows = query.unique().execute(control.cursor).fetchall()
        self.members = [self.get_member(row[0]) for row in rows]

    def get_member(self, person_id):
        "Get an object for the reviewer represented by this ID; uses caching."

        if person_id not in Summary.persons:
            Summary.persons[person_id] = Summary.Person(person_id, self.control)
        return Summary.persons[person_id]

    def get_display_title(self):
        "Return a possibly enhanced copy of the summary's title."

        title = self.title
        if self.is_module:
            title += " (module)"
        if self.control.show_id:
            title += " (%d)" % self.doc_id
        return title

    def show(self, page):
        "Add HTML markup to the page for this summary."

        page.add(page.B.H4(self.get_display_title()))
        if self.members:
            page.add("<ul>")
            for member in self.members:
                page.add(page.B.LI(member.name))
            page.add("</ul>")

    def __cmp__(self, other):
        "Support sorting."
        return cmp(self.title, other.title)

    class Person:
        "One of these for every reviewer on the report."

        def __init__(self, person_id, control):
            """
            Get the person's name from the document table.
            The summaries list is only populated and used if the
            report is by reviewer.
            """

            self.control = control
            self.doc_id = person_id
            self.summaries = []
            self.name = "NO NAME FOUND"
            query = cdrdb.Query("document", "title")
            query.where(query.Condition("id", person_id))
            rows = query.execute(control.cursor).fetchall()
            if rows:
                self.name = rows[0][0].split(";")[0].strip()

        def show(self, page):
            "Show the reviewer's name and all of her summaries."

            page.add(page.B.H4(self.name))
            if self.summaries:
                page.add("<ul>")
                for summary in self.summaries:
                    page.add(page.B.LI(summary.get_display_title()))
                page.add("</ul>")

        def __cmp__(self, other):
            "Support sorting."
            return cmp(self.name, other.name)

#----------------------------------------------------------------------
# Let this be loaded without doing anything to support (e.g.) lint.
#----------------------------------------------------------------------
if __name__ == "__main__":
    Control().run()
