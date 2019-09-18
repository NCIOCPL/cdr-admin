#----------------------------------------------------------------------
# Report on summaries with citations to publications other than journal
# articles.
#----------------------------------------------------------------------
import cdr
import cdrcgi
import cgi
import lxml.etree as etree
import time
from cdrapi import db

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
session    = cdrcgi.getSession(fields)
lang       = fields.getvalue("lang")
english    = fields.getlist("english")
spanish    = fields.getlist("spanish")
types      = fields.getlist("type")
request    = cdrcgi.getRequest(fields)
title      = "CDR Administration"
instr      = "Summaries With Non-Journal Article Citations Report"
script     = "SummariesWithNonJournalArticleCitations.py"
SUBMENU    = "Report Menu"
buttons    = ("Submit", SUBMENU, cdrcgi.MAINMENU)
start      = time.time()
dateString = time.strftime("%B %d, %Y")
subtitle   = "%s - %s" % (instr, dateString)
DEBUGGING  = False

#----------------------------------------------------------------------
# Callback for constructing the citation display, possibly with a
# link to a web site.
#----------------------------------------------------------------------
def pub_info_cell(cell, fmt):
    citation = cell.values()
    if citation.info.web_site:
        url = citation.info.web_site
        link = cdrcgi.Page.B.A(url, href=url, target="_blank")
        br = cdrcgi.Page.B.BR()
        return cdrcgi.Page.B.TD(citation.info.pub_details, br, link)
    return cdrcgi.Page.B.TD(citation.info.pub_details)

#----------------------------------------------------------------------
# Debug logging, turned off by default.
#----------------------------------------------------------------------
def debug_log(what):
    if DEBUGGING:
        now = time.time()
        elapsed = now - start
        fp = open("d:/tmp/swnjac.log", "a")
        fp.write("%10.3f: %s\n" % (elapsed, what))
        fp.close()

#----------------------------------------------------------------------
# Get the list of citations types from which the report requester
# can select.  Avoid proceedings and journal publications.
#----------------------------------------------------------------------
def get_citation_types(cursor):
    C = db.Query.Condition
    query = db.Query("query_term", "value").unique()
    query.where(C("path", "/Citation/PDQCitation/CitationType"))
    query.where(C("value", "Proceeding%", "NOT LIKE"))
    query.where(C("value", "Journal%", "NOT LIKE"))
    query.order("value")
    return [row[0] for row in query.execute(cursor).fetchall()]

#----------------------------------------------------------------------
# Get the list of editorial boards for one of the languages.  Called
# by get_english_boards() and get_spanish_boards(), each of which
# builds a custom query for this purpose.
#----------------------------------------------------------------------
def get_boards(query, cursor):
    boards = []
    for doc_id, doc_title in query.execute(cursor).fetchall():
        boards.append((cdr.extract_board_name(doc_title), doc_id))
    return sorted(boards)

#----------------------------------------------------------------------
# Get the list of editorial boards linked to active English summaries.
#----------------------------------------------------------------------
def get_english_boards(cursor):
    C = db.Query.Condition
    query = db.Query("active_doc d", "d.id", "d.title").unique()
    query.join("query_term b", "b.int_val = d.id")
    query.join("query_term l", "b.doc_id = l.doc_id")
    query.where(C("b.path",
                  "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"))
    query.where(C("l.path", "/Summary/SummaryMetaData/SummaryLanguage"))
    query.where(C("l.value", "English"))
    query.where(C("d.title", "%Editorial Advisory%", "NOT LIKE"))
    return get_boards(query, cursor)

#----------------------------------------------------------------------
# Get the list of editorial boards linked to English summaries which
# have been translated into Spanish.
#----------------------------------------------------------------------
def get_spanish_boards(cursor):
    C = db.Query.Condition
    query = db.Query("active_doc d", "d.id", "d.title").unique()
    query.join("query_term b", "b.int_val = d.id")
    query.join("query_term t", "t.int_val = b.doc_id")
    query.where(C("b.path",
                  "/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref"))
    query.where(C("t.path", "/Summary/TranslationOf/@cdr:ref"))
    query.where(C("d.title", "%Editorial Advisory%", "NOT LIKE"))
    query.where(C("d.title", "%Complementary%", "NOT LIKE"))
    return get_boards(query, cursor)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Connect to the database.
#----------------------------------------------------------------------
try:
    conn = db.connect(user='CdrGuest')
    cursor = conn.cursor()
except Exception as e:
    cdrcgi.bail("Unable to connect to the CDR database: %s" % e)

#----------------------------------------------------------------------
# If we don't have a request, put up the form.
#----------------------------------------------------------------------
def have_request():
    if not lang:
        return False
    if not types:
        return False
    if lang == "English":
        if not english:
            return False
    elif not spanish:
        return False
    return True

if not have_request():
    jscript = """\
function check_lang(lang) {
    if (lang == 'English') {
        jQuery('#english-set').show();
        jQuery('#spanish-set').hide();
    }
    else{
        jQuery('#spanish-set').show();
        jQuery('#english-set').hide();
    }
}
jQuery(function() {
    check_lang(jQuery("input[name='lang']:checked").val());
});"""

    page = cdrcgi.Page(title, subtitle=subtitle, buttons=buttons,
                       action=script, session=session)
    page.add_script(jscript)
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Select Language and PDQ Summaries"))
    page.add_radio("lang", "English", "English", checked=True)
    page.add_radio("lang", "Spanish", "Spanish")
    page.add('<fieldset id="english-set">')
    page.add(page.B.LEGEND("Select PDQ Summaries (one or more)"))
    for label, doc_id in get_english_boards(cursor):
        page.add_checkbox("english", label, str(doc_id), widget_classes="ind")
    page.add("</fieldset>")
    page.add('<fieldset id="spanish-set">')
    page.add(page.B.LEGEND("Select PDQ Summaries (one or more):"))
    for label, doc_id in get_spanish_boards(cursor):
        page.add_checkbox("spanish", label, str(doc_id), widget_classes="ind")
    page.add("</fieldset>")
    page.add("</fieldset>")
    page.add('<fieldset id="type-set">')
    page.add(page.B.LEGEND("Select Citation Type (one or more)"))
    for cite_type in get_citation_types(cursor):
        page.add_checkbox("type", cite_type, cite_type, widget_classes="ind")
    page.add("</fieldset>")
    page.send()

#----------------------------------------------------------------------
# Construct an SQL query based on the options selected by the report's
# requestor.
#----------------------------------------------------------------------
def getQuery():
    C = db.Query.Condition
    query = db.Query("query_term_pub s", "s.doc_id").unique()
    query.join("active_doc a", "a.id = s.doc_id")
    query.join("query_term c", "c.doc_id = s.int_val")
    query.where("s.path LIKE '/Summary%CitationLink/@cdr:ref'")
    query.where("c.path = '/Citation/PDQCitation/CitationType'")
    if not types or "all" in types:
        query.where("c.value NOT LIKE 'Journal%'")
        query.where("c.value NOT LIKE 'Proceeding%'")
    else:
        query.where(C("c.value", types, "IN"))
    if lang == "English":
        if not english or "all" in english:
            query.join("query_term_pub l", "l.doc_id = s.doc_id")
            query.where("l.path = '/Summary/SummaryMetaData/SummaryLanguage'")
            query.where("l.value = 'English'")
        else:
            query.join("query_term_pub b", "b.doc_id = s.doc_id")
            query.where(C("b.int_val", english, "IN"))
    else:
        if not spanish or "all" in spanish:
            query.join("query_term_pub l", "l.doc_id = s.doc_id")
            query.where("l.path = '/Summary/SummaryMetaData/SummaryLanguage'")
            query.where("l.value = 'Spanish'")
        else:
            query.join("query_term_pub t", "t.doc_id = s.doc_id")
            query.where("t.path = '/Summary/TranslationOf/@cdr:ref'")
            query.join("query_term b", "b.doc_id = t.int_val")
            query.where("b.path = "
                        "'/Summary/SummaryMetaData/PDQBoard/Board/@cdr:ref'")
            query.where(C("b.int_val", spanish, "IN"))
    query.order(1)
    return query

#----------------------------------------------------------------------
# Information about a citation found in a summary.  There's one
# instance for each such appearance of a citation in a summary,
# but we collect and store the common information about each citation
# only once, no matter how many appearances occur in summaries.
#----------------------------------------------------------------------
class Citation:
    citations = {}
    filters = ['set:Denormalization Citation Set',
               'name:Copy XML for Citation QC Report']
    class Info:
        """
        Information about a Citation document, independent of where
        it is used in summaries.
        """
        def __init__(self, doc_id):
            self.doc_id = doc_id
            self.title = self.type = self.web_site = None
            self.pub_details = ""
            query = db.Query("document", "xml")
            query.where(query.Condition("id", doc_id))
            doc = query.execute(cursor).fetchall()[0][0]
            tree = etree.XML(doc.encode("utf-8"))
            for node in tree.findall("PDQCitation/CitationType"):
                self.type = node.text
            for node in tree.findall("PDQCitation/CitationTitle"):
                self.title = node.text
            if "Internet" in self.type:
                for node in tree.iter("ExternalRef"):
                    self.web_site = node.get("{cips.nci.nih.gov/cdr}xref")
            response = cdr.filterDoc(session, Citation.filters, docId=doc_id)
            if isinstance(response, basestring):
                debug_log("failure filtering citation %s: %s" %
                          (doc_id, repr(response)))
                cdrcgi.bail("failure filtering citation CDR%s: %s" %
                            (doc_id, repr(response)))
            xml = response[0]
            try:
                tree = etree.XML(xml)
            except Exception as e:
                debug_log("failure parsing %s: %s" % (repr(xml), e))
                cdrcgi.bail("failure parsing %s: %s" % (repr(xml), e))
            for node in tree.iter("FormattedReference"):
                self.pub_details = node.text
    def __init__(self, doc_id, node):
        """
        Store the information about this particular use of the citation
        in a summary, and make sure the common information about the
        Citation document has been captured.
        """
        self.doc_id = doc_id
        self.section_title = None
        parent = node.getparent()
        while parent is not None:
            if parent.tag == "SummarySection":
                break
            parent = parent.getparent()
        if parent is not None:
            for child in parent.findall("Title"):
                self.section_title = child.text
        if doc_id not in Citation.citations:
            Citation.citations[doc_id] = Citation.Info(doc_id)
        self.info = Citation.citations[doc_id]

    @staticmethod
    def get_eligible_citations():
        """
        Get a list of all citations whose types match those selected
        on the report request form.
        """
        query = db.Query("query_term", "doc_id").unique()
        query.where("path = '/Citation/PDQCitation/CitationType'")
        if not types or "all" in types:
            query.where("value NOT LIKE 'Journal%'")
            query.where("value NOT LIKE 'Proceeding%'")
        else:
            query.where(query.Condition("value", types, "IN"))
        return set([row[0] for row in query.execute(cursor).fetchall()])
Citation.eligible_citations = Citation.get_eligible_citations()
debug_log("got eligible citations")

#----------------------------------------------------------------------
# One of these for each summary which will be represented on the report.
#----------------------------------------------------------------------
class Summary:
    count = 0
    def __init__(self, doc_id):
        citations = set()
        self.doc_id = doc_id
        self.title = None
        self.citations = []
        query = db.Query("document", "xml")
        query.where(query.Condition("id", doc_id))
        doc_xml = query.execute(cursor).fetchall()[0][0]
        tree = etree.XML(doc_xml.encode("utf-8"))
        for node in tree.findall("SummaryTitle"):
            self.title = node.text
        for node in tree.iter("CitationLink"):
            cdr_ref = node.get("{cips.nci.nih.gov/cdr}ref")
            try:
                citation_id = cdr.exNormalize(cdr_ref)[1]
            except:
                continue
            if citation_id in Citation.eligible_citations:
                citation = Citation(citation_id, node)
                key = (citation_id, citation.section_title)
                if key not in citations:
                    self.citations.append(citation)
                    citations.add(key)
        Summary.count += 1
        debug_log("constructed %d summaries" % Summary.count)

#----------------------------------------------------------------------
# Assemble and return the report.
#----------------------------------------------------------------------
query = getQuery()
debug_log("got query")
rows = query.execute(cursor).fetchall()
debug_log("query returned %d rows" % len(rows))
summaries = [Summary(row[0]) for row in rows]
debug_log("got %d summaries" % len(summaries))
cols = (
    cdrcgi.Report.Column("Summary ID"),
    cdrcgi.Report.Column("Summary Title"),
    cdrcgi.Report.Column("Summary Sec Title"),
    cdrcgi.Report.Column("Citation Type"),
    cdrcgi.Report.Column("Citation ID"),
    cdrcgi.Report.Column("Citation Title"),
    cdrcgi.Report.Column("Publication Details/Other Publication Info")
)
rows = []
for summary in summaries:
    for citation in summary.citations:
        pub_info = cdrcgi.Report.Cell(citation, callback=pub_info_cell)
        row = (summary.doc_id, summary.title, citation.section_title,
               citation.info.type, citation.doc_id, citation.info.title,
               pub_info)
        rows.append(row)
debug_log("%d rows" % len(rows))
table = cdrcgi.Report.Table(cols, sorted(rows))
report = cdrcgi.Report(title, [table], banner=instr, subtitle=dateString)
debug_log("table ready")
report.send()
