#!/usr/bin/env python

"""Refresh citations from NLM.

Update premedline citations that have had their statuses changed
since they were last imported or updated.
"""

from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from functools import cached_property
from time import sleep
from cdrcgi import Controller
from cdrapi.docs import Doc
from cdr import prepare_pubmed_article_for_import
from lxml import etree
from requests import post


class Control(Controller):
    """Access to the current login session and report-building tools."""

    SUBTITLE = "Citation Status Changes"
    LOGNAME = "UpdatePreMedlineCitations"
    SUBMIT = "Update"
    URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    COLUMNS = "PMID", "CDR ID", "Old Status", "New Status", "Notes"
    PMID_PATH = "/Citation/PubmedArticle/MedlineCitation/PMID"
    STATUS_PATH = "/Citation/PubmedArticle/MedlineCitation/@Status"
    STATUSES = "In-Process", "Publisher", "In-data-review"
    CAPTION = "{:d} Pre-Medline Citations Examined -- {:d} Statuses Changed"
    INSTRUCTIONS = (
        "This utility checks to see if any of the Citation documents in "
        "the CDR with a pre-Medline status have a new status at NLM, so that "
        "the documents can be refreshed. Note that the report will be "
        "displayed in a new browser tab after a successful refresh of the "
        "citation statuses, in order to preserve the menu links on this "
        "page, but the displayed list of available updates will no longer be "
        "valid, so you should refresh this form at that point in order to "
        "view an accurate list of what is available to be refreshed."
    )

    def build_tables(self):
        """Assemble the table showing what we did and return it."""

        if not self.session.can_do("MODIFY DOCUMENT", "Citation"):
            self.bail("You must be authorized to replace Citation documents "
                      "to run this script.")
        opts = dict(caption=self.caption, columns=self.COLUMNS)
        return self.Reporter.Table(self.rows, **opts)

    def populate_form(self, page):
        """Show what the update will do.

        Required positional argument:
          page - HTMLPage class instance
        """

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)
        if not self.changed:
            message = (
                "No pre-Medline citations found with updated statuses "
                "available."
            )
            self.alerts.append(dict(message=message, type="info"))
        else:
            for pmid in sorted(self.skipped):
                page.form.append(page.hidden_field("skipped", pmid))
            fieldset = page.fieldset("Available For Refresh")
            available = page.B.UL()
            for citation in self.changed:
                available.append(page.B.LI(citation.description))
            fieldset.append(available)
            page.form.append(fieldset)

    @cached_property
    def buttons(self):
        """Only show the Update button if there are changes to import."""
        return [self.SUBMIT] if self.changed else []

    @cached_property
    def caption(self):
        """String to be displayed immediately above the table."""
        return self.CAPTION.format(len(self.citations), len(self.rows))

    @cached_property
    def changed(self):
        """Determine which citation have changed at NLM."""

        changed = []
        for pmid in sorted(self.citations):
            citation = self.citations[pmid]
            if citation.pubmed_article is not None:
                if citation.pubmed_article.status != citation.status:
                    changed.append(citation)
            else:
                message = (
                    f"Unable to fetch PubMed article {citation.pmid} "
                    f"for CDR{citation.doc.id} with status {citation.status}."
                )
                self.alerts.append(dict(message=message, type="warning"))
                self.skipped.add(pmid)
        return changed

    @cached_property
    def citations(self):
        """Dictionary (by PMID) of citations with non-terminal statuses."""

        # Find the Citation documents with the target statuses.
        start = datetime.now()
        fields = "p.doc_id", "p.value AS pmid", "s.value AS status"
        query = self.Query("query_term p", *fields).order("p.doc_id")
        query.join("query_term s", "s.doc_id = p.doc_id")
        query.where(query.Condition("p.path", self.PMID_PATH))
        query.where(query.Condition("s.path", self.STATUS_PATH))
        query.where(query.Condition("s.value", self.STATUSES, "IN"))
        rows = query.unique().execute(self.cursor).fetchall()

        # Do a preliminary pass to find docs which show up more than once.
        citations = defaultdict(list)
        for row in rows:
            citations[row.doc_id].append((row.pmid, row.status))
        for doc_id in citations:
            if len(citations[doc_id]) > 1:
                pmids = set()
                statuses = set()
                for pmid, status in citations[doc_id]:
                    pmids.add(pmid)
                    statuses.add(status)
                for pmid in pmids:
                    self.skipped.add(pmid)
                pmids = "; ".join(sorted(pmids))
                statuses = "; ".join(sorted(statuses))
                message = (
                    f"CDR{doc_id} found multiple times with PMID(s) "
                    f"{pmids} and status(es) {statuses}. Skipping check."
                )
                self.logger.warning(message)
                self.alerts.append(dict(message=message, type="warning"))

        # Now do the real pass to pack up the citations for checking.
        citations = {}
        for row in rows:
            pmid = row.pmid.strip().upper()
            if pmid in self.skipped:
                self.logger.info("skipping PMID %s", pmid)
                continue
            if pmid in self.duplicates:
                duplicates = sorted(self.duplicates[pmid] - {row.doc_id})
                if len(duplicates) == 1:
                    why = f"CDR{duplicates[0]} also has that PubMed ID"
                else:
                    if len(duplicates) == 2:
                        docs = " and ".join([f"CDR{d}" for d in duplicates])
                    else:
                        docs = ", ".join([f"CDR{d}" for d in duplicates[:-1]])
                        docs += f", and CDR{duplicates[-1]}"
                    why = f"{docs} also have that PubMed ID"
                message = (
                    f"Skipping Citation CDR{row.doc_id} with PMID {pmid} "
                    f"because {why}."
                )
                self.alerts.append(dict(message=message, type="warning"))
                self.skipped.add(pmid)
            else:
                citations[pmid] = Citation(self, row)
        self.__fetch(citations)
        elapsed = datetime.now() - start
        self.logger.info("loaded %d citations in %s", len(citations), elapsed)
        return citations

    @cached_property
    def duplicates(self):
        """Find PMIDs claimed by more than one CDR document."""

        query = self.Query("query_term", "COUNT(*) n", "value")
        query.where(query.Condition("path", self.PMID_PATH))
        query.group("value")
        query.having("COUNT(*) > 1")
        rows = query.execute(self.cursor).fetchall()
        pmids = [row.value.strip().upper() for row in rows]
        query = self.Query("query_term", "doc_id", "value")
        query.where(query.Condition("path", self.PMID_PATH))
        query.where(query.Condition("value", pmids, "IN"))
        duplicates = defaultdict(set)
        for doc_id, pmid in query.execute(self.cursor).fetchall():
            duplicates[pmid.strip().upper()].add(doc_id)
        return duplicates

    @cached_property
    def rows(self):
        """Table rows reporting citations whose statuses have changed."""

        rows = []
        for citation in self.changed:
            row = [
                citation.pmid,
                citation.doc.id,
                citation.status,
                citation.pubmed_article.status,
            ]
            try:
                citation.update()
                row.append("updated")
            except Exception as e:
                message = f"Failure updating {citation.pmid}: {e}"
                self.logger.exception(message)
                self.alerts.append(dict(message=message, type="error"))
                row.append(self.Reporter.Cell("failed", classes="error"))
            rows.append(row)
        return rows

    @cached_property
    def skipped(self):
        """PubMed IDs which we won't try to refresh."""
        return {pmid for pmid in self.fields.getlist("skipped")}

    def __fetch(self, citations, retries=3):
        """Get the latest for the citations from NLM.

        Attach the PubMed articles to the Citation objects with which
        they belong.

        Pass:
            citations - dictionary of citation docs with non-terminal statuses
        """

        data = dict(db="pubmed", id=",".join(list(citations)), retmode="xml")
        xml = post(self.URL, data).content
        fetched = 0
        for node in etree.fromstring(xml).findall("PubmedArticle"):
            fetched += 1
            article = PubmedArticle(node)
            if len(article.pmids) != 1:
                message = f"NLM article has multiple IDs {article.pmids}."
                self.alerts.append(dict(message=message, type="warning"))
            elif article.pmid in citations:
                citations[article.pmid].pubmed_article = article
            else:
                message = f"Got unexpected article with PMID {article.pmid}"
                self.alerts.append(dict(message=message, type="warning"))
        if fetched < len(citations):
            args = len(citations), fetched
            self.logger.warning("expected %d articles, got %d", *args)
            if not fetched:
                self.logger.warning("retries=%d response=%s", retries, xml)
                if retries > 0:
                    sleep(5-retries)
                    self.__fetch(citations, retries-1)


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

    @cached_property
    def description(self):
        """Describe a citation available for refresh for the form."""

        return (
            f"Citation {self.pmid} (CDR{self.id}): status {self.status} "
            f"will become {self.pubmed_article.status}."
        )

    @cached_property
    def doc(self):
        """`Doc` object for the CDR Citation document."""
        return Doc(self.__control.session, id=self.__row.doc_id)

    @cached_property
    def id(self):
        """Unique ID for the CDR Citation document."""
        return self.__row.doc_id

    @cached_property
    def pmid(self):
        """Normalized string for the PubMed ID."""
        return self.__row.pmid.strip()

    @cached_property
    def pubmed_article(self):
        """Fresh copy of the article from NLM (set later)."""
        return None

    @cached_property
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
        """Give the caller an uncached copy of the PubmedArticle node."""
        return deepcopy(self.__node)

    @cached_property
    def pmid(self):
        """Pick the latest PubMed ID if there is more than one."""
        return self.pmids and self.pmids[-1].value or None

    @cached_property
    def pmids(self):
        """Sequence of PubMed IDs found in the node."""

        pmids = []
        for child in self.__node.findall("MedlineCitation/PMID"):
            pmids.append(self.PMID(child))
        return sorted(pmids)

    @cached_property
    def status(self):
        """Current status for the PubMed article."""

        node = self.__node.find("MedlineCitation")
        return node.get("Status") if node is not None else None

    class PMID:
        """PubMed ID with version number (who knew they had more than one?)."""

        def __init__(self, node):
            """Save the node so we can get the ID and version."""
            self.__node = node

        @cached_property
        def version(self):
            """Integer for the ID's version."""

            try:
                return int(self.__node.get("Version"))
            except Exception:
                return 0

        @cached_property
        def value(self):
            """Normalized string for the PubMed ID."""
            return self.__node.text.strip()

        def __repr__(self):
            """String rendering of the PubMed ID for error reporting."""
            return repr("PMID", self.version, self.value)

        def __lt__(self, other):
            """Suport sorting multiple PubMed IDs by version integer."""
            return self.version < other.version


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
