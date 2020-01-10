#----------------------------------------------------------------------
# Report listing all references cited in a selected version of a
# cancer information summary.
#
# BZIssue::4598 modify sort order to use local setting and ignore case
# BZIssue::4651 add PMID link to citations
# BZIssue::4786 fix non-Pubmed citations
# JIRA::OCECDR-3456 switch NCBI url to use HTTPS protocol
# JIRA::OCECDR-4179 include module refs by default (complete rewrite)
# JIRA::OCECDR-4194 remove duplicate citations
#----------------------------------------------------------------------

import datetime
import locale
import lxml.etree as etree
import cdr
import cdrcgi
from cdrapi import db

class Control(cdrcgi.Control):
    """
    Report-specific behavior implemented in this derived class.
    """

    def __init__(self):
        """
        Collect and validate the request parameters.
        """

        cdrcgi.Control.__init__(self, "Summary Citations Report")
        self.parsed = set()
        self.summary_title = None
        self.doc_id = self.fields.getvalue("DocId")
        self.title_fragment = self.fields.getvalue("DocTitle", "").strip()
        self.doc_version = self.fields.getvalue("DocVersion")
        self.modules = self.fields.getvalue("modules") and True or False
        if self.doc_id:
            try:
                self.doc_id = cdr.exNormalize(self.doc_id)[1]
            except:
                cdrcgi.bail("invalid CDR document id format")
        if self.doc_version:
            try:
                self.doc_version = int(self.doc_version)
            except:
                cdrcgi.bail(cdrcgi.TAMPERING)

    def populate_form(self, form):
        """
        Put up the initial report request form.
        """

        if self.doc_id:
            self.show_versions(form)
        elif self.title_fragment:
            self.show_titles(form)
        else:
            self.show_first_form(form)

    def show_first_form(self, form):
        """
        Gather the preliminary information for the request.

        User must enter either a CDR ID or a title fragment. By
        default we recurse into linked summary modules, but the
        user can suppress that behavior.
        """

        form.add("<fieldset>")
        form.add(form.B.LEGEND("Select a document"))
        form.add_text_field("DocTitle", "Title")
        form.add_text_field("DocId", "CDR ID")
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Linked summary modules"))
        form.add_radio("modules", "Include citations in linked modules",
                       "1", checked=True)
        form.add_radio("modules", "Exclude citations in linked modules", "")
        form.add("</fieldset>")

    def show_versions(self, form):
        """
        Let the user select the document version for the report.
        """

        query = db.Query("doc_version v", "v.num", "v.dt", "v.comment")
        query.join("usr u", "u.id = v.usr")
        query.where(query.Condition("v.id", self.doc_id))
        rows = query.order("v.num DESC").execute(self.cursor).fetchall()
        if not rows:
            self.doc_version = -1
            self.show_report()
        else:
            query = db.Query("document", "title")
            query.where("id = %d" % self.doc_id)
            title = query.execute(self.cursor).fetchone()[0].split(";")[0]
            form.add_hidden_field("modules", self.modules and "1" or "")
            form.add_hidden_field("DocId", str(self.doc_id))
            form.add("<fieldset>")
            form.add(form.B.LEGEND("Select version for %s" % title))
            versions = [(-1, "Current Working Version")]
            for version, date, comment in rows:
                comment = comment or "[No comment]"
                label = "[V%d %s] %s" % (version, str(date)[:10], comment)
                versions.append((version, label))
            form.add_select("DocVersion", "Version", versions, -1)
            form.add("</fieldset>")

    def show_titles(self, form):
        """
        Let the user pick from a list of summaries matching the title fragment.

        If no summaries match the title fragment, bail with an error message.
        If only one summary matches, jump straight to the version selection.
        """

        docs = self.get_docs()
        if not docs:
            cdrcgi.bail("No matching documents found")
        elif len(docs) == 1:
            self.doc_id = docs[0].id
            self.show_versions(form)
        else:
            form.add_hidden_field("modules", self.modules and "1" or "")
            form.add("<fieldset style='width: 1024px'>")
            form.add(form.B.LEGEND("Select Summary"))
            for doc in docs:
                display = "[CDR%010d] %s" % (doc.id, doc.title)
                form.add_radio("DocId", display, str(doc.id))
            form.add("</fieldset>")

    def show_report(self):
        """
        Override the base class method since we have a non-tablar report
        with intermediary forms to refine the request.
        """

        if not self.doc_id or not self.doc_version:
            self.show_form()
        self.parse_summary(self.doc_id, self.doc_version, self.modules)
        locale.setlocale(locale.LC_COLLATE, "")
        citations = sorted(Citation.citations.values())
        page = cdrcgi.Page(self.title, banner=None)
        page.add(page.B.H1(self.summary_title))
        page.add(page.B.H2("References"))
        if not citations:
            page.add("<p>No references found</p>")
        else:
            page.add("<ol>")
            for citation in citations:
                page.add(citation.li())
            page.add("</ol>")
        page.send()

    def parse_summary(self, doc_id, doc_version=-1, recurse=False):
        """
        Collect the citations and the summary title from the document.

        If the user has not suppressed recursion into linked summary
        modules, parse them, too.
        """

        self.parsed.add(doc_id)
        if doc_version == -1:
            doc_version = None
        filter_set = ['set:Denormalization Summary Set']
        response = cdr.filterDoc("guest", filter_set, doc_id,
                                 docVer=doc_version)
        if isinstance(response, (str, bytes)):
           cdrcgi.bail(response)
        try:
            root = etree.XML(response[0])
        except:
            cdrcgi.bail("Failure parsing filtered document")
        for node in root.iter("ReferenceList"):
            for child in node.findall("Citation"):
                Citation(child)
        if self.summary_title is None:
            self.summary_title = ""
            for node in root.findall("SummaryTitle"):
                self.summary_title = node.text
                break
        if recurse:
            for node in root.iter("SummaryModuleLink"):
                cdr_id = self.extract_cdr_id(node)
                if cdr_id and cdr_id not in self.parsed:
                    self.parse_summary(cdr_id, recurse=recurse)

    def get_docs(self):
        """
        Find the summaries matching the user's title fragment.
        """

        fragment = f"{self.title_fragment}%"
        query = db.Query("document d", "d.id", "d.title")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'Summary'")
        query.where(query.Condition("d.title", fragment, "LIKE"))
        rows = query.order("d.id").execute(self.cursor).fetchall()
        class Doc:
            def __init__(self, doc_id, doc_title):
                self.id = doc_id
                self.title = doc_title
        return [Doc(*row) for row in rows]

    @staticmethod
    def extract_cdr_id(node):
        """
        Pull out the CDR ID as an integer from a node's cdr:ref attribute.
        """

        cdr_id = None
        cdr_ref = node.get("{cips.nci.nih.gov/cdr}ref")
        if cdr_ref:
            try:
                cdr_id = cdr.exNormalize(cdr_ref)[1]
            except:
                pass
        return cdr_id

class Citation:
    """
    Objects representing each of the unique citations found in the summaries.

    Instance variables:

        text  -  formatted text for the citation
        pmid  -  optional Pubmed ID

    Class variables:

        citations - dictionary of unique citations found
        BASE      - front portion of the URL for viewing the Pubmed citation
    """

    citations = {}
    BASE = "https://www.ncbi.nlm.nih.gov/pubmed"

    def __init__(self, node):
        """
        Extract the formatted citation and Pubmed ID.

        If the citation text is not empty, and we haven't seen this one
        yet, add the citation to the dictionary of unique citations found.
        """

        self.text = "".join(node.itertext()).strip()
        self.pmid = node.get("PMID")
        if self.text:
            if not self.text.endswith("."):
                self.text += "."
            key = (self.pmid, self.text)
            if key not in Citation.citations:
                Citation.citations[key] = self

    def li(self):
        """
        Return the object representing the list item for the citation.

        If the citation has a Pubmed ID, also include a link to the
        citation on the Pubmed web site.
        """

        if self.pmid:
            url = "%s/%s?dopt=Abstract" % (self.BASE, self.pmid)
            a = cdrcgi.Page.B.A(self.pmid, href=url, target="_blank")
            a.tail = "]"
            return cdrcgi.Page.B.LI(self.text + " [", a)
        return cdrcgi.Page.B.LI(self.text)

    def __lt__(self, other):
        """
        Use intelligent sorting for the citations, folding characters
        with different diacritics together.
        """

        return locale.strcoll(self.text.lower(), other.text.lower()) < 0

Control().run()
