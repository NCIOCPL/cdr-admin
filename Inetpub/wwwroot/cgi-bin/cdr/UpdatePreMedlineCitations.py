#!/usr/bin/env python

"""Refresh citations from NLM.

Update premedline citations that have had their statuses changed
since they were last imported or updated.
"""

from copy import deepcopy
from cdrcgi import Controller
from cdrapi.docs import Doc
from cdr import prepare_pubmed_article_for_import
from lxml import etree
from requests import post


class Control(Controller):
    """Access to the current login session and report-building tools."""

    SUBTITLE = "Citation Status Changes"
    LOGNAME = "UpdatePreMedlineCitations"
    URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    COLUMNS = "PMID", "CDR ID", "Old Status", "New Status", "Notes"
    PMID_PATH = "/Citation/PubmedArticle/MedlineCitation/PMID"
    STATUS_PATH = "/Citation/PubmedArticle/MedlineCitation/@Status"
    STATUSES = "In-Process", "Publisher", "In-data-review"
    CAPTION = "{:d} Pre-Medline Citations Examined -- {:d} Statuses Changed"

    def build_tables(self):
        """Assemble the table showing what we did and return it."""

        if not self.session.can_do("MODIFY DOCUMENT", "Citation"):
            self.bail("You must be authorized to replace Citation documents "
                      "to run this script.")
        opts = dict(caption=self.caption, columns=self.COLUMNS)
        return self.Reporter.Table(self.rows, **opts)

    def show_form(self):
        """Bypass the form, which isn't needed for this script."""
        self.show_report()

    def show_report(self):
        """Override the base class version so we can show any errors."""

        if self.citations and self.errors is not None:
            self.report.page.form.append(self.errors)
        self.report.page.add_css("table { width: 600px; }")
        self.report.send(self.format)

    @property
    def caption(self):
        """String to be displayed immediately above the table."""
        return self.CAPTION.format(len(self.citations), len(self.rows))

    @property
    def citations(self):
        """Dictionary (by PMID) of citations with non-terminal statuses."""

        if not hasattr(self, "_citations"):
            fields = "p.doc_id", "p.value AS pmid", "s.value AS status"
            query = self.Query("query_term p", *fields)
            query.join("query_term s", "s.doc_id = p.doc_id")
            query.where(query.Condition("p.path", self.PMID_PATH))
            query.where(query.Condition("s.path", self.STATUS_PATH))
            query.where(query.Condition("s.value", self.STATUSES, "IN"))
            self._citations = {}
            self.__errors = []
            dup_message = "Duplicate PMID {} (CDR{:d} and CDR{:d}"
            for row in query.execute(self.cursor).fetchall():
                pmid = row.pmid.strip().upper()
                if pmid in self._citations:
                    args = row.pmid, self._citations[pmid].id, row.doc_id
                    self.__errors.append(dup_message.format(*args))
                else:
                    self._citations[pmid] = Citation(self, row)
            self.__fetch(self._citations)
        return self._citations

    @property
    def errors(self):
        """Renderable version of any errors logged."""

        if not hasattr(self, "_errors"):
            self._errors = None
            if self.__errors:
                self._errors = self.HTMLPage.fieldset("Date Integrity Errors")
                ul = self.HTMLPage.B.UL()
                for error in self.__errors:
                    li = self.HTMLPage.B.LI(error)
                    li.set("class", "error")
                    ul.append(li)
                self._errors.append(ul)
        return self._errors

    @property
    def rows(self):
        """Table rows reporting citations whose statuses have changed."""

        if not hasattr(self, "_rows"):
            self._rows = []
            error_opts = dict(classes="error")
            for pmid in sorted(self.citations):
                citation = self.citations[pmid]
                row = [citation.pmid, citation.doc.id, citation.status]
                changed = False
                if citation.pubmed_article is not None:
                    row.append(citation.pubmed_article.status)
                    if citation.pubmed_article.status != citation.status:
                        changed = True
                        try:
                            citation.update()
                            row.append("updated")
                        except Exception:
                            args = pmid
                            self.logger.exception("Failure updating %s", pmid)
                            cell = self.Reporter.Cell("failed", **error_opts)
                            row.append(cell)
                else:
                    changed = True
                    cell = self.Reporter.Cell("missing", **error_opts)
                    row  += [cell, ""]
                if changed:
                    self._rows.append(row)
        return self._rows

    def __fetch(self, citations):
        """Get the latest for the citations from NLM.

        Attach the PubMed articles to the Citation objects with which
        they belong.

        Pass:
            citations - dictionary of citation docs with non-terminal statuses
        """

        data = dict(db="pubmed", id=",".join(list(citations)), retmode="xml")
        xml = post(self.URL, data).content
        for node in etree.fromstring(xml).findall("PubmedArticle"):
            article = PubmedArticle(node)
            if len(article.pmids) != 1:
                self.__errors.append(f"PMIDs: {article.pmids}")
                continue
            if article.pmid in citations:
                citations[article.pmid].pubmed_article = article
            else:
                error = f"Unexpected article with PMID {article.pmid}"
                self.__errors.append(error)


class Citation:
    """CDR Citation document."""

    COMMENT = "pre-medline citation updated (issue #5150)"
    VAL_TYPES = "schema", "links"
    SAVE_OPTS = dict(
        version=True,
        publishable=True,
        val_types=VAL_TYPES,
        comment=COMMENT,
        reason=COMMENT,
        unlock=True,
    )

    def __init__(self, control, row):
        """Save the caller's values.

        Pass:
            control - access to the current CDR login session
            row - results set row from the database query
        """

        self.__control = control
        self.__row = row

    @property
    def doc(self):
        """`Doc` object for the CDR Citation document."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.__control.session, id=self.__row.doc_id)
        return self._doc

    @property
    def id(self):
        """Unique ID for the CDR Citation document."""
        return self.__row.doc_id

    @property
    def pmid(self):
        """Normalized string for the PubMed ID."""

        if not hasattr(self, "_pmid"):
            self._pmid = self.__row.pmid.strip()
        return self._pmid

    @property
    def pubmed_article(self):
        """Fresh copy of the article from NLM."""

        if hasattr(self, "_pubmed_article"):
            return self._pubmed_article
        return None

    @pubmed_article.setter
    def pubmed_article(self, value):
        """This gets set later."""
        self._pubmed_article = value

    @property
    def status(self):
        """What the CDR thinks the status of this citation is."""
        return self.__row.status

    def update(self):
        """Save a new version with updated information from NLM."""

        node = self.pubmed_article.node
        replacement = prepare_pubmed_article_for_import(node)
        old_node = self.doc.root.find("PubmedArticle")
        self.doc.root.replace(old_node, replacement)
        self.doc.check_out(comment=self.COMMENT)
        self.doc.save(**self.SAVE_OPTS)


class PubmedArticle:
    """Article information retrieved from NLM for one of our Citation docs."""

    def __init__(self, node):
        """Save a reference to the parsed XML node.

        Pass:
            node - parsed PubmedArticle node
        """
        self.__node = node

    @property
    def node(self):
        """Give the caller a copy of the PubmedArticle node."""
        return deepcopy(self.__node)

    @property
    def pmid(self):
        """Pick the latest PubMed ID if there is more than one."""
        return self.pmids and self.pmids[-1].value or None

    @property
    def pmids(self):
        """Sequence of PubMed IDs found in the node."""

        if not hasattr(self, "_pmids"):
            pmids = []
            for child in self.__node.findall("MedlineCitation/PMID"):
                pmids.append(self.PMID(child))
            self._pmids = sorted(pmids)
        return self._pmids

    @property
    def status(self):
        """Current status for the PubMed article."""

        if not hasattr(self, "_status"):
            self._status = None
            node = self.__node.find("MedlineCitation")
            if node is not None:
                self._status = node.get("Status")
        return self._status

    class PMID:
        """PubMed ID with version number (who knew they had more than one?)."""

        def __init__(self, node):
            """Save the node so we can get the ID and version."""
            self.__node = node

        @property
        def version(self):
            """Integer for the ID's version."""

            if not hasattr(self, "_version"):
                try:
                    self._version = int(self._-node.get("Version"))
                except:
                    self._version = 0
            return self._version

        @property
        def value(self):
            """Normalized string for the PubMed ID."""

            if not hasattr(self, "_value"):
                self._value = self.__node.text.strip()
            return self._value

        def __repr__(self):
            """String rendering of the PubMed ID for error reporting."""
            return repr("PMID", self.version, self.value)

        def __lt__(self, other):
            """Suport sorting multiple PubMed IDs by version integer."""
            return self.version < other.version


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
