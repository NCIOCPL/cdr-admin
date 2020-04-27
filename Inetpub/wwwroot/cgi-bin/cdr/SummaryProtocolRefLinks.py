#!/usr/bin/env python

"""Find ProtocolRef elements in Summary documents, showing the URLs.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class Control(Controller):
    """Access to the database and report-building utilities."""

    SUBTITLE = "ProtocolRef Links in Summaries"
    LOGNAME = "SummaryProtocolRefLinks"

    def show_form(self):
        """Bypass the form, which this report doesn't use."""
        self.show_report()

    def build_tables(self):
        """Assemble the report's two tables."""
        return self.summary_table, self.details_table

    @property
    def details_table(self):
        """Table with one row for each distinct protocol ref."""

        cols = "CDR ID", "Summary Title", "Protocol ID", "Protocol Link"
        caption = "Links to Clinical Trials"
        return self.Reporter.Table(self.rows, columns=cols, caption=caption)

    @property
    def docs(self):
        """Sequence of Summary documents with ProtocolRef links."""

        query = self.Query("pub_proc_cg c", "c.id").unique().order("c.id")
        query.join("query_term_pub p", "p.doc_id = c.id")
        query.where("path LIKE '/Summary%ProtocolRef%'")
        rows = query.execute(self.cursor).fetchall()
        self.logger.info("Found %d docs with ProtocolRef links", len(rows))
        return [Summary(self, row.id) for row in rows]

    @property
    def rows(self):
        """Values for the details table."""

        if not hasattr(self, "_rows"):
            self._rows = []
            for doc in self.docs:
                self._rows.extend(doc.rows)
        return self._rows

    @property
    def summary_table(self):
        """Table with counts for each url category."""

        ctgov = cgov = other = 0
        for id, title, protocol, url in self.rows:
            url = url.lower()
            if "clinicaltrials.gov" in url:
                ctgov += 1
            elif "cancer.gov" in url:
                cgov += 1
            else:
                other += 1
        rows = (
            ("clinicaltrials.gov", ctgov),
            ("cancer.gov", cgov),
            ("None", other),
        )
        caption = "Total Count by Link Type"
        columns = "Protocol Links Including ...", "Count"
        return self.Reporter.Table(rows, columns=columns, caption=caption)


class Summary:
    """CDR Summary document with protocol links."""

    def __init__(self, control, id):
        """Save the caller's values.

        Pass:
            control - access to the current session and report-building tools
            id - integer for the CDR document ID
        """

        self.__control = control
        self.__id = id

    @property
    def doc(self):
        """`Doc` object for the summary."""

        if not hasattr(self, "_doc"):
            self._doc = Doc(self.__control.session, id=self.__id)
            self.__control.logger.info("Processing %s", self._doc.cdr_id)
        return self._doc

    @property
    def rows(self):
        """Values for the report, one row for each link."""

        if not hasattr(self, "_rows"):
            nct_ids = set()
            protocol_refs = set()
            for node in self.doc.root.iter("ProtocolRef"):
                protocol_id = Doc.get_text(node)
                nct_id = node.get("nct_id", "").strip() or ""
                if nct_id:
                    nct_ids.add(nct_id)
                protocol_refs.add((protocol_id, nct_id))
            opts = dict(timeout=(5,5), verify=False, allow_redirects=True)
            urls = {}
            for nct_id in nct_ids:
                url = f"https://www.cancer.gov/clinicaltrials/{nct_id}"
                try:
                    response = requests.head(url, allow_redirects=True)
                    urls[nct_id] = response.url
                    args = nct_id, response.url
                    self.__control.logger.debug("%s -> %s", *args)
                except:
                    self.__control.logger.exception("Failure for %s", url)
                    urls[nct_id] = "*** URL timed out"
            self._rows = []
            for protocol_id, nct_id in sorted(protocol_refs):
                self._rows.append([
                    self.doc.id,
                    self.title,
                    protocol_id,
                    urls[nct_id] if nct_id else "None",
                ])
        return self._rows

    @property
    def title(self):
        """String for the Summary document's title."""

        if not hasattr(self, "_title"):
            self._title = Doc.get_text(self.doc.root.find("SummaryTitle"))
        return self._title


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
