#!/usr/bin/env python
"""JSON API for fetching information for the CDR Citation documents.
"""

from collections import defaultdict
from functools import cached_property
from json import dumps
from cdrcgi import Controller


class Control(Controller):
    """Top-level logic for the script."""

    SUBTITLE = "get-citations API service"
    LOGNAME = "testing"
    CITATION_PATH = "/Citation/PubmedArticle/MedlineCitation"
    JOURNAL_PATH = f"{CITATION_PATH}/Article/Journal"

    def run(self):
        """Overridden because this is not a standard report."""

        path = "/Citation/PubmedArticle/MedlineCitation/Article/ArticleTitle"
        query = self.Query("query_term t", "t.doc_id", "t.value").order(1)
        query.join("document d", "d.id = t.doc_id")
        query.where(f"t.path = '{path}'")
        query.where("d.val_status = 'V' and d.active_status = 'A'")
        docs = []
        for id, title in query.execute(self.cursor).fetchall():
            pmids = self.pmids.get(id) or []
            journals = self.journals.get(id) or []
            years = self.years.get(id) or []
            if len(pmids) == 1 and len(journals) == 1 and len(years) == 1:
                if not self.limit or len(docs) < self.limit:
                    doc = dict(
                        id=id,
                        title=title,
                        pmid=pmids[0],
                        journal=journals[0],
                        year=years[0]
                    )
                    docs.append(doc)
        self.send_page(dumps(docs, indent=2), mime_type="application/json")

    @cached_property
    def journals(self):
        """Dictionary of journal titles indexed by CDR Citation doc IDs."""

        path = f"{self.CITATION_PATH}/MedlineJournalInfo/MedlineTA"
        query = self.Query("query_term", "doc_id", "value")
        query.where(f"path = '{path}'")
        journals = defaultdict(list)
        for id, journal in query.execute(self.cursor).fetchall():
            journals[id].append(journal.strip())
        return journals

    @cached_property
    def limit(self):
        """Optional throttle on the number of terms to return."""
        return int(self.fields.getvalue("limit", "0"))

    @cached_property
    def pmids(self):
        """Dictionary of PubMed IDs for CDR Citation documents."""

        query = self.Query("query_term", "doc_id", "value")
        query.where(f"path = '{self.CITATION_PATH}/PMID'")
        pmids = defaultdict(list)
        for id, pmid in query.execute(self.cursor).fetchall():
            pmid = pmid.strip()
            if pmid.isdigit():
                pmids[id].append(pmid)
        return pmids

    @cached_property
    def years(self):
        """Years of publication indexed by CDR Citation doc IDs."""

        path = f"{self.JOURNAL_PATH}/JournalIssue/PubDate/Year"
        query = self.Query("query_term", "doc_id", "value")
        query.where(f"path = '{path}'")
        years = defaultdict(list)
        for id, year in query.execute(self.cursor).fetchall():
            year = year.strip()
            if year.isdigit():
                years[id].append(year)
        return years


if __name__ == "__main__":
    """Only execute if invoked directly, not imported as a module."""

    control = Control()
    try:
        control.run()
    except Exception as e:
        message = "Failure getting citations"
        control.logger.exception(message)
        control.send_page(f"{message}: {e}", text_type="plain")
