#!/usr/bin/env python

"""Search for CDR Citation documents.
"""

from functools import cached_property
from lxml import etree
import requests
from cdr import prepare_pubmed_article_for_import
from cdrcgi import AdvancedSearch
from cdrapi.docs import Doc


class CitationSearch(AdvancedSearch):
    """Customize search for this document type."""

    DOCTYPE = "Citation"
    SUBTITLE = DOCTYPE
    FILTER = "set:QC Citation Set"
    PUBMED = "https://www.ncbi.nlm.nih.gov/entrez/"
    MEDLINE_CITATION = "/Citation/PubmedArticle/MedlineCitation"
    PUB_DETAILS = "/Citation/PDQCitation/PublicationDetails"
    PATHS = {
        "title": [
            "/Citation/PubmedArticle/%/Article/%Title",
            "/Citation/PDQCitation/CitationTitle",
        ],
        "author": [
            "/Citation/PDQCitation/AuthorList/Author/%Name",
            "/Citation/PubmedArticle/%/AuthorList/Author/%Name",
        ],
        "pub_in": [
            f"{MEDLINE_CITATION}/MedlineJournalInfo/MedlineTA",
            f"{PUB_DETAILS}/PublishedIn/@cdr:ref[int_val]",
        ],
        "pub_year": [
            f"{MEDLINE_CITATION}/Article/Journal/JournalIssue/PubDate/Year",
            f"{PUB_DETAILS}/PublicationYear",
        ],
        "volume": [
            f"{MEDLINE_CITATION}/Article/Journal/JournalIssue/Volume",
        ],
        "issue": [
            f"{MEDLINE_CITATION}/Article/Journal/JournalIssue/Issue",
        ],
    }

    def __init__(self):
        """Set the stage for showing the search form or the search results."""

        AdvancedSearch.__init__(self)
        for name in self.PATHS:
            setattr(self, name, self.fields.getvalue(name))
        self.search_fields = []
        self.query_fields = []
        for name, paths in self.PATHS.items():
            field = self.QueryField(getattr(self, name), paths)
            self.query_fields.append(field)
            self.search_fields.append(self.text_field(name))

    def run(self):
        """Override the run() method of the base class.

        We need to handle requests to import or update PubMed
        articles from NLM.
        """

        if self.request in ("Import", "Update"):
            try:
                citation = Citation(self)
                citation.save()
                self.show_form(citation.message, citation.error)
            except Exception as e:
                self.session.logger.exception("%s from PubMed", self.request)
                error = f"Unable to import {self.pmid!r} from PubMed: {e}"
                self.show_form(error=error)
        else:
            AdvancedSearch.run(self)

    @cached_property
    def pmid(self):
        """ID of a PubMed article to be imported."""
        return self.fields.getvalue("pmid", "").strip()

    @cached_property
    def cdrid(self):
        """ID of an existing Citation document to be updated."""
        cdrid = self.fields.getvalue("cdrid")
        return Doc.extract_id(cdrid) if cdrid else None

    def add_import_form(self, page):
        """Add another fieldset with fields for importing a PubMed document."""

        help = "Optionally enter the CDR ID of a document to be updated."
        cdrid_field = self.text_field("cdrid", label="CDR ID", tooltip=help)
        cdrid_field.find("input").set("oninput", "chk_cdrid()")
        pmid_field = self.text_field("pmid", label="PMID")
        pmid_field.find("input").set("oninput", "chk_pmid()")
        fieldset = self.fieldset("Import or Update Citation From PubMed")
        fieldset.append(pmid_field)
        fieldset.append(cdrid_field)
        page.form.append(fieldset)
        page.head.append(page.B.SCRIPT(src="/js/CiteSearch.js"))

    def show_form(self, message=None, error=None):
        args = self.session.name, self.SUBTITLE, self.search_fields
        page = self.Form(*args, control=self)
        if self.session.can_do("ADD DOCUMENT", "Citation"):
            self.add_import_form(page)
        pubmed = f"window.open('{self.PUBMED}', 'pm');"
        page.form.append(page.button("Search"))
        page.form.append(page.button("Search PubMed", onclick=pubmed))
        if self.session.can_do("ADD DOCUMENT", "Citation"):
            button = self.button("Import")
            button.set("disabled")
            button.set("onclick", "clear_target()")
            page.form.append(button)
        if message:
            type = "warning" if "validation errors" in message else "success"
            page.add_alert(message, type=type)
        if error:
            page.add_alert(error, type="error")
        page.send()


class Citation:
    """Logic for assembling and saving a new or updated Citation document."""

    EUTILS = "https://eutils.ncbi.nlm.nih.gov"
    EFETCH = f"{EUTILS}/entrez/eutils/efetch.fcgi?db=pubmed&retmode=xml&id="
    ERRORS = "*** IMPORTED WITH ERRORS ***  PUBLISHABLE VERSION NOT CREATED"
    VAL_TYPES = "schema", "links"
    COMMENT = "Saved from the Citation Advanced Search page"
    SAVE_OPTS = dict(
        version=True,
        publishable=True,
        val_types=VAL_TYPES,
        unlock=True,
        comment=COMMENT,
        reason=COMMENT,
    )

    def __init__(self, control):
        """Save the caller's object referencd.

        Most of the work is done while assembling this object's properties.
        """
        self.control = control

    @cached_property
    def error(self):
        """If there were validation errors, log them and show a big warning."""

        if not self.doc.errors:
            return None
        for error in self.doc.errors:
            self.control.session.logger.error(str(error))
        return self.ERRORS

    @cached_property
    def message(self):
        """Prepare a subtitle showing what we just did."""

        cdrid = self.doc.cdr_id
        pmid = self.control.pmid
        if self.doc.errors:
            suffix = "with validation errors"
        else:
            suffix = "with a publishable version"
        if self.control.cdrid:
            return f"Updated {cdrid} from PMID {pmid} ({suffix})"
        return f"Imported PMID {pmid} as {cdrid} ({suffix})"

    def save(self):
        """Save the new or updated Citation document."""
        self.doc.save(**self.SAVE_OPTS)

    @cached_property
    def doc(self):
        """Prepare a `cdrapi.Doc` object for saving in the CDR"""

        # If we're updating an existing Citation doc, fetch and modify it.
        if self.control.cdrid:
            cdrid = self.control.cdrid
            doc = Doc(self.control.session, id=cdrid)
            doc.check_out()
            root = doc.root
            old_node = root.find("PubmedArticle")
            if old_node is None:
                raise Exception(f"{cdrid} is not a PubMed article")
            root.replace(old_node, self.pubmed_article)
            doc.xml = etree.tostring(root)

        # Otherwise, build up a new document and insert NLM's info.
        else:
            pmid = self.control.pmid
            cdrid = self.lookup(pmid)
            if cdrid:
                raise Exception(f"PMID {pmid} already imported as {cdrid}")
            root = etree.Element("Citation")
            details = etree.SubElement(root, "VerificationDetails")
            etree.SubElement(details, "Verified").text = "Yes"
            etree.SubElement(details, "VerifiedIn").text = "PubMed"
            root.append(self.pubmed_article)
            opts = dict(xml=etree.tostring(root), doctype="Citation")
            doc = Doc(self.control.session, **opts)

        # In either case, return the Doc object.
        return doc

    @cached_property
    def pubmed_article(self):
        """Fetch and prepare PubmedArticle element for import into the CDR

        Note that we no longer import everything in the documents we get
        from NLM, but instead cherry-pick just the information we need,
        in order to avoid the whiplash of keeping up with all of their
        DTD changes.
        """

        pmid = self.control.pmid
        url = f"{self.EFETCH}{pmid}"
        self.control.session.logger.info("Fetching %r", url)
        response = requests.get(url)
        root = etree.fromstring(response.content)
        node = root.find("PubmedArticle")
        if node is None:
            args = url, response.content
            self.control.session.logger.error("url=%s response=%s", *args)
            sleep(2)
            response = requests.get(url)
            root = etree.fromstring(response.content)
            if root is None:
                raise Exception(f"PubmedArticle for {pmid} not found")
        return prepare_pubmed_article_for_import(node)

    def lookup(self, pmid):
        """See if we have already imported this article.

        Pass:
            pmid - unique string identifier for the PubMed record

        Return:
            canonical form of the CDR ID for an existing Citation document
            (or None if we don't already have it)
        """

        query = self.control.DBQuery("query_term", "doc_id")
        query.where("path LIKE '/Citation/PubmedArticle/%/PMID'")
        query.where(query.Condition("value", pmid))
        rows = query.execute(self.control.session.cursor).fetchall()
        return f"{rows[0].doc_id:010d}" if rows else None


if __name__ == "__main__":
    CitationSearch().run()
