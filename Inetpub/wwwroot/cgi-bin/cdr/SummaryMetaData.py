#!/usr/bin/env python

#----------------------------------------------------------------------
#
# Report on the metadata for one or more summaries.
#
# BZIssue::1724
# BZIssue::2905
# BZIssue::3716
# BZIssue::4475
# JIRA::OCECDR-3976
# JIRA::OCECDR-4062
#
#----------------------------------------------------------------------
import cdr
import cdrcgi
from cdrapi import db
from lxml import etree

class Control(cdrcgi.Control):
    """
    Object used to determine how to respond to the client's request.
    Collects parameters used to invoke the script and scrubs them.
    """

    N_PATH = "/Organization/OrganizationNameInformation/OfficialName/Name"
    T_PATH = "/Organization/OrganizationType"
    ALL_ITEMS = ("CDR ID", "Summary Title", "Advisory Board", "Editorial Board",
                 "Audience", "Language", "Description", "Pretty URL",
                 "Topics", "Purpose Text", "Section Metadata",
                 "Summary Abstract", "Summary Keywords", "PMID")
    DEFAULT_ITEMS = set(["CDR ID", "Summary Title", "Advisory Board",
                         "Editorial Board", "Topics"])
    LANGUAGES = ("English", "Spanish")
    AUDIENCES = ("Health Professional", "Patient")
    SELECTIONS = ("id", "title", "group")

    def __init__(self):
        """
        Collect and validate the request's parameters.
        """
        cdrcgi.Control.__init__(self, "Summary Metadata Report")
        self.items = set(self.fields.getlist("items")) or self.DEFAULT_ITEMS
        self.selection = self.fields.getvalue("selection")
        self.doc_id = self.fields.getvalue("doc-id")
        self.doc_title = self.fields.getvalue("doc-title", "").strip()
        self.language = self.fields.getvalue("language")
        self.audience = self.fields.getvalue("audience")
        self.board_id = self.fields.getvalue("board")
        self.board_name = None

        # Check for tampering.
        if self.items - set(self.ALL_ITEMS):
            cdrcgi.bail()
        if self.doc_id:
            try:
                self.doc_id = cdr.exNormalize(self.doc_id)[1]
            except:
                cdrcgi.bail("Invalid document ID")
        cdrcgi.valParmVal(self.language, valList=self.LANGUAGES, empty_ok=True,
                          msg=cdrcgi.TAMPERING)
        cdrcgi.valParmVal(self.audience, valList=self.AUDIENCES, empty_ok=True,
                          msg=cdrcgi.TAMPERING)
        cdrcgi.valParmVal(self.selection, valList=self.SELECTIONS,
                          empty_ok=True, msg=cdrcgi.TAMPERING)
        if self.board_id:
            try:
                self.board_name = self.get_board_name(self.board_id)
            except:
                cdrcgi.bail()

    def populate_form(self, form):
        """
        Fill in the fields for requesting the report.
        """
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Summary Selection Method"))
        form.add_radio("selection", "Single Summary By ID", "id", checked=True)
        form.add_radio("selection", "Single Summary By Title", "title")
        form.add_radio("selection", "Multiple Summaries By Group", "group")
        form.add("</fieldset>")
        form.add('<fieldset id="doc-id-box">')
        form.add(form.B.LEGEND("Enter Document ID"))
        form.add_text_field("doc-id", "Doc ID")
        form.add("</fieldset>")
        form.add('<fieldset id="doc-title-box" class="hidden">')
        form.add(form.B.LEGEND("Enter Document Title"))
        form.add_text_field("doc-title", "Doc Title")
        form.add("</fieldset>")
        form.add('<fieldset id="group-box" class="hidden">')
        form.add(form.B.LEGEND("Summary Group"))
        form.add_select("board", "Board", self.get_boards())
        form.add_select("language", "Language", self.LANGUAGES)
        form.add_select("audience", "Audience", self.AUDIENCES)
        form.add("</fieldset>")
        self.add_item_fields(form)
        form.add_script("""\
function check_selection(sel) {
    switch (sel) {
    case 'id':
        jQuery('#doc-id-box').show();
        jQuery('#doc-title-box').hide();
        jQuery('#group-box').hide();
        break;
    case 'title':
        jQuery('#doc-id-box').hide();
        jQuery('#doc-title-box').show();
        jQuery('#group-box').hide();
        break;
    case 'group':
        jQuery('#doc-id-box').hide();
        jQuery('#doc-title-box').hide();
        jQuery('#group-box').show();
        break;
    }
}
jQuery(function() {
    var sel = jQuery('input[name="selection"]:checked').val();
    check_selection(sel);
});""")

    def show_report(self):
        """
        Override the base class method since some of the tables are vertical.
        """
        summaries = self.get_summaries()
        if not summaries:
            cdrcgi.bail("No summaries found for report.")
        if len(summaries) == 1:
            subtitle = "%s (CDR%d)" % (summaries[0].title, summaries[0].doc_id)
        else:
            subtitle = "%s Language %s Summaries for the %s" % (self.language,
                                                                self.audience,
                                                                self.board_name)
        page = cdrcgi.Page(self.title, subtitle=subtitle, body_classes="report")
        for summary in summaries:
            summary.report(page)
        page.add_css("""\
.top-section { font-weight: bold; }
.mid-section { font-weight: normal; }
.low-section { font-style: italic; }
table.summary { width: 1024px; margin-top: 40px; }
table.summary th { width: 150px; text-align: right; padding-right: 10px; }""")
        page.send()

    def add_item_fields(self, form):
        """
        Common code to create the check boxes for which data should be
        displayed on the report. Hoisted out because it's used in two
        places (the main report request form and the cascading form to
        choose a summary when multiple matches are found for a partial
        summary title string.
        """
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Include On Report"))
        for item in self.ALL_ITEMS:
            form.add_checkbox("items", item, item, checked=item in self.items)
        form.add("</fieldset>")

    def get_summaries(self):
        """
        Use the appropriate method for selection which summaries should
        appear on the report.
        """
        if self.selection == "id":
            return self.match_id()
        elif self.selection == "title":
            return self.match_title()
        elif self.selection == "group":
            return self.match_group()

    def match_id(self):
        """
        Find the summary which matches the document ID supplied by the user.
        """
        if not self.doc_id:
            cdrcgi.bail("Missing document ID")
        return [Summary(self, self.doc_id)]

    def match_title(self):
        """
        Find the summaries which match the partial title string entered
        by the user. If only a single summary matches, use it for the report.
        Otherwise, put up a cascading form for the user to pick one.
        """
        if not self.doc_title:
            cdrcgi.bail("No title specified")
        pattern = f"%{self.doc_title}%"
        query = db.Query("active_doc d", "d.id", "d.title")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where(query.Condition("t.name", "Summary"))
        query.where(query.Condition("d.title", pattern, "LIKE"))
        query.order("d.title")
        rows = query.execute(self.cursor).fetchall()
        if not rows:
            cdrcgi.bail("No matching summaries found")
        if len(rows) == 1:
            return [Summary(self, rows[0][0])]
        opts = {
            "buttons": self.buttons,
            "action": self.script,
            "subtitle": "Multiple Matching Summaries Found",
            "session": self.session
        }
        form = cdrcgi.Page(self.PAGE_TITLE, **opts)
        form.add_hidden_field("selection", "id")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Choose Summary"))
        form.add_select("doc-id", "Summary", rows)
        form.add("</fieldset>")
        self.add_item_fields(form)
        form.send()

    def match_group(self):
        """
        Find all the summaries for the user's selection for board,
        language, and audience. If the user wants the Spanish summaries,
        we first find the English language summaries for the selected
        board and audience, and then find the documents which are marked
        as translations of the English summaries we just found.
        """
        if not self.board_id:
            cdrcgi.bail("Board not selected")
        if not self.language:
            cdrcgi.bail("Language not selected")
        if not self.audience:
            cdrcgi.bail("Audience not selected")
        a_path = "/Summary/SummaryMetaData/SummaryAudience"
        b_path = "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"
        l_path = "/Summary/SummaryMetaData/SummaryLanguage"
        t_path = "/Summary/TranslationOf/@cdr:ref"
        query = db.Query("active_doc d", "d.id", "d.title").unique()
        query.join("doc_version v", "v.id = d.id")
        query.join("query_term b", "b.doc_id = d.id")
        query.join("query_term a", "a.doc_id = d.id")
        query.join("query_term l", "l.doc_id = d.id")
        query.where(query.Condition("a.path", a_path))
        query.where(query.Condition("b.path", b_path))
        query.where(query.Condition("l.path", l_path))
        query.where(query.Condition("a.value", self.audience + "s"))
        query.where(query.Condition("b.int_val", self.board_id))
        query.where(query.Condition("l.value", "English"))
        query.where(query.Condition("v.publishable", "Y"))
        query.order("d.title")
        doc_ids = [row[0] for row in query.execute(self.cursor).fetchall()]
        if self.language != "English":
            query = db.Query("document d", "d.id", "d.title").unique()
            query.join("query_term t", "t.doc_id = d.id")
            query.where(query.Condition("t.path", t_path))
            query.where(query.Condition("t.int_val", doc_ids, "IN"))
            query.order("d.title")
            rows = query.execute(self.cursor).fetchall()
            doc_ids = [row[0] for row in rows]
        return [Summary(self, doc_id) for doc_id in doc_ids]

    def get_board_name(self, board_id):
        """
        Look up the board name given the CDR ID for the board's Organization
        document. The caller will catch any exceptions raised (presumably
        because the document ID has been tampered with by a hacker).
        """
        query = db.Query("query_term", "value")
        query.where(query.Condition("path", self.N_PATH))
        query.where(query.Condition("doc_id", board_id))
        return query.execute(self.cursor).fetchone()[0]

    def get_boards(self):
        """
        Fetch IDs and names of the PDQ editorial boards (for picklist).
        """
        query = db.Query("query_term n", "n.doc_id", "n.value")
        query.join("query_term t", "t.doc_id = n.doc_id")
        query.join("active_doc a", "a.id = n.doc_id")
        query.where(query.Condition("n.path", self.N_PATH))
        query.where(query.Condition("t.path", self.T_PATH))
        query.where(query.Condition("t.value", "PDQ Editorial Board"))
        query.order("n.value")
        boards = []
        prefix, suffix = ("PDQ ", " Editorial Board")
        for id, name in query.execute(self.cursor).fetchall():
            if name.startswith(prefix):
                name = name[len(prefix):]
            if name.endswith(suffix):
                name = name[:-len(suffix)]
            boards.append([id, name])
        return boards

class Summary:
    """
    Object containing all of the information which can appear on the
    report for a single PDQ summary.
    """

    NS = "cips.nci.nih.gov/cdr"
    board_cache = {}

    def __init__(self, control, doc_id):
        """
        Parse the summary document, extracting data for the report.
        """
        self.control = control
        self.doc_id = int(doc_id)
        query = db.Query("document", "xml")
        query.where(query.Condition("id", self.doc_id))
        rows = query.execute(control.cursor).fetchall()
        if not rows:
            cdrcgi.bail("CDR%d not found" % self.doc_id)
        try:
            root = etree.XML(rows[0][0].encode("utf-8"))
        except:
            cdrcgi.bail("CDR%d malformed" % self.doc_id)
        if root.tag != "Summary":
            cdrcgi.bail("CDR%d is not a summary" % self.doc_id)
        self.title = self.language = self.audience = self.description = ""
        self.purpose = self.advisory_board = self.editorial_board = ""
        self.topics = []
        self.abstract = []
        self.keywords = []
        self.sections = []
        self.type = self.link = self.pmid = None
        for node in root.findall("SummaryTitle"):
            self.title = self.get_text(node)
        for node in root.findall("SummaryMetaData/*"):
            if node.tag == "SummaryType":
                self.type = node.text
            elif node.tag == "SummaryAudience":
                self.audience = node.text
            elif node.tag == "SummaryLanguage":
                self.language = node.text
            elif node.tag == "SummaryDescription":
                self.description = self.get_text(node)
            elif node.tag == "SummaryURL":
                self.link = self.Link(node)
            elif node.tag == "PDQBoard":
                for child in node.findall("Board"):
                    try:
                        name = self.get_board_name(child)
                        if "advisory" in name.lower():
                            self.advisory_board = name
                        else:
                            self.editorial_board = name
                    except Exception as e:
                        self.advisory_board = "oops! (%s)" % e
            elif node.tag in ("MainTopics", "SecondaryTopics"):
                self.topics.append(self.get_topic(node))
            elif node.tag == "PurposeText":
                self.purpose = self.get_text(node)
            elif node.tag == "SummaryAbstract":
                for child in node.findall("Para"):
                    self.abstract.append(self.get_text(child))
            elif node.tag == "SummaryKeyWords":
                for child in node.findall("SummaryKeyWord"):
                    self.keywords.append(child.text)
            elif node.tag == "PMID":
                self.pmid = self.get_text(node)
        for node in root.iter("SummarySection"):
            self.sections.append(self.Section(node, control.cursor))

    @staticmethod
    def get_text(node):
        """
        Get all the text content for an element, stripping internal markup.
        """
        return "".join([t for t in node.itertext()]).strip()

    def get_topic(self, node):
        """
        Pull out the name of the topic, and add a suffix indicating whether
        it is a main topic (M) or a secondary topic (S).
        """
        for child in node.findall("Term"):
            suffix = node.tag == "MainTopics" and "M" or "S"
            return "%s (%s)" % (child.text, suffix)

    def report(self, page):
        """
        Add at least one table (possibly two) describing this summary's
        meta data.
        """
        self.B = page.B
        if self.control.items - set(["Section Metadata"]):
            self.add_general_table(page)
        if "Section Metadata" in self.control.items:
            self.add_section_metadata(page)

    def add_section_metadata(self, page):
        """
        Add a table showing all of the summary's sections which have
        reportable information.
        """
        table = self.B.TABLE(
            self.B.TR(
                self.B.TH("Section Title"),
                self.B.TH("Diagnoses"),
                self.B.TH("SS\u00a0No"),
                self.B.TH("Section Type")
            )
        )
        for section in self.sections:
            if section.has_data():
                section.report(table)
        page.add(table)

    def add_general_table(self, page):
        """
        Create a vertical table for the data items to be displayed
        for this summary (excluding information on the summary
        sections).
        """
        table = self.B.TABLE(self.B.CLASS("summary"))
        for label, value in (
            ("CDR ID", self.doc_id),
            ("Summary Title", self.title),
            ("Advisory Board", self.advisory_board),
            ("Editorial Board", self.editorial_board),
            ("Audience", self.audience),
            ("Language", self.language),
            ("Description", self.description),
            ("Pretty URL", self.link),
            ("Topics", self.topics),
            ("Purpose Text", self.purpose),
            ("Summary Abstract", self.abstract),
            ("Summary Keywords", self.keywords),
            ("PMID", self.pmid),
        ):
            if label in self.control.items:
                self.add_general_row(table, label, value)
        page.add(table)

    def add_general_row(self, table, heading, value):
        """
        Append a row to the table for a single data item for this
        summary. The table is vertical, so the headers go down
        the first column instead of across the top row.
        """
        if value:
            if heading == "Pretty URL":
                link = self.B.A(value.url, href=value.url)
                td = self.B.TD(value.display, self.B.BR(), link)
            elif type(value) is list:
                lines = list(value)
                line = lines.pop(0)
                td = self.B.TD(line)
                while lines:
                    line = lines.pop(0)
                    br = self.B.BR()
                    br.tail = str(line)
                    td.append(br)
            elif isinstance(value, (str, int, float)):
                td = self.B.TD(str(value))
            else:
                cdrcgi.bail("type of value is %s" % type(value))
        else:
            td = self.B.TD()
        table.append(self.B.TR(self.B.TH(heading), td))

    def get_board_name(self, node):
        """
        Look up the name of a PDQ board using its CDR ID. Use a
        cache to improve performance.
        """
        cdr_ref = node.get("{%s}ref" % self.NS)
        if cdr_ref not in self.board_cache:
            doc_id = cdr.exNormalize(cdr_ref)[1]
            query = db.Query("query_term", "value")
            query.where(query.Condition("path", Control.N_PATH))
            query.where(query.Condition("doc_id", doc_id))
            rows = query.execute(self.control.cursor).fetchall()
            name = rows and rows[0][0] or ("no name for %s" % repr(cdr_ref))
            self.board_cache[cdr_ref] = name
        return self.board_cache[cdr_ref]

    class Section:
        """
        Nested class for all the sections of the summary, fetched in
        document order.
        """

        diagnosis_cache = {}

        def __init__(self, node, cursor):
            """
            Collect the information which can be display on the report
            for this summary section.
            """
            self.depth = len(node.getroottree().getpath(node).split("/"))
            self.cursor = cursor
            self.title = ""
            self.diagnoses = []
            self.types = []
            self.search_attr = node.get("TrialSearchString")
            for child in node.findall("Title"):
                self.title = Summary.get_text(child)
            for child in node.findall("SectMetaData/Diagnosis"):
                try:
                    self.diagnoses.append(self.get_diagnosis_name(child))
                except Exception as e:
                    self.diagnoses.append("oops: %s" % e)
            for child in node.findall("SectMetaData/SectionType"):
                self.types.append(child.text)

        def get_diagnosis_name(self, node):
            """
            Look up a diagnosis name based on its CDR ID. Use a cache
            to improve performance.
            """
            cdr_ref = node.get("{%s}ref" % Summary.NS)
            if cdr_ref not in self.diagnosis_cache:
                doc_id = cdr.exNormalize(cdr_ref)[1]
                query = db.Query("query_term", "value")
                query.where(query.Condition("path", "/Term/PreferredName"))
                query.where(query.Condition("doc_id", doc_id))
                rows = query.execute(self.cursor).fetchall()
                name = rows and rows[0][0] or ("no name for %s" %
                                               repr(cdr_ref))
                self.diagnosis_cache[cdr_ref] = name
            return self.diagnosis_cache[cdr_ref]

        def has_data(self):
            """
            See if there's anything to report for this summary section.
            """
            if self.search_attr == "No":
                return True
            return self.diagnoses or self.types or self.title

        def report(self, table):
            """
            Add the table row for this summary section's information.
            """
            B = cdrcgi.Page.B
            check_mark = self.search_attr == "No" and "\u2714" or ""
            level = { 3: "top", 4: "mid" }.get(self.depth, "low")
            table.append(
                B.TR(
                    B.TD(self.title, B.CLASS("%s-section" % level)),
                    B.TD("; ".join(self.diagnoses)),
                    B.TD(check_mark, B.CLASS("center")),
                    B.TD("; ".join(self.types))
                )
            )

    class Link:
        """
        Holds the label and URL for the summary link.
        """
        def __init__(self, node):
            self.display = node.text
            self.url = node.get("{%s}xref" % Summary.NS)

Control().run()
