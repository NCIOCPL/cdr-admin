#!/usr/bin/env python

"""Find ProtocolRef elements in Summary documents, showing the URLs.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc
from cdrapi.settings import Tier
import requests
import lxml.html.builder
from urllib3.exceptions import InsecureRequestWarning
# pylint: disable-next=no-member
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class Control(Controller):
    """Access to the database and report-building utilities."""

    SUBTITLE = "ProtocolRef Links in Summaries"
    LOGNAME = "SummaryProtocolRefLinks"
    HOST = Tier().hosts["APPC"]
    EXAMPLE = (
        f"https://{HOST}/cgi-bin/cdr/SummaryProtocolRefLinks.py"
        "?limit=2"
    )
    INSTRUCTIONS = (
        "This report shows three types of ProtocolRef links found in "
        "publishable Summary documents.",
        (
            "links pointing to the NCI web site (cancer.gov)",
            "links pointing to NLM's ClinicalTrials.gov database",
            "links which are removed by the publishing filters "
            "because of blocked documents",
        ),
        "The report page has two tables. The first table shows the "
        "counts for each of these three link types. The second table "
        "has four columns.",
        (
            "CDR ID - the ID for the Summary document in which the "
            "ProtocolRef element was found",
            "Summary Title - the title of that document",
            "Protocol ID - the primary ID for the trial",
            "Protocol Link - the URL for the page describing the trial "
            "('None' for the third type of SummaryRef element)",
        ),
        "This is a long-running report, usually taking between five and "
        "ten minutes (sometimes a bit longer on the lower tiers), so please "
        "be patient. For testing the script, it is "
        "possible to limit the number of summary documents processed by "
        "manually adding a 'limit' parameter to the URL. For example:",
        lxml.html.builder.A(EXAMPLE, href=EXAMPLE, target="_blank"),
    )

    def populate_form(self, page):
        """Bypass the form, which this report doesn't use.

        Required positional parameter:
          page - instance of the HTMLPage class
        """

        if self.ready:
            self.show_report()
        fieldset = page.fieldset("Instructions")
        for section in self.INSTRUCTIONS:
            if isinstance(section, (list, tuple)):
                items = page.B.UL()
                for item in section:
                    items.append(page.B.LI(item))
                fieldset.append(items)
            else:
                fieldset.append(page.B.P(section))
        page.form.append(fieldset)

    def build_tables(self):
        """Assemble the report's two tables."""

        if not self.ready:
            self.show_form()
            return []
        return self.summary_table, self.details_table

    @cached_property
    def details_table(self):
        """Table with one row for each distinct protocol ref."""

        cols = "CDR ID", "Summary Title", "Protocol ID", "Protocol Link"
        caption = "Links to Clinical Trials"
        return self.Reporter.Table(self.rows, columns=cols, caption=caption)

    @cached_property
    def docs(self):
        """Sequence of Summary documents with ProtocolRef links."""

        if not self.ready:
            return []
        query = self.Query("pub_proc_cg c", "c.id").unique().order("c.id")
        if self.limit:
            query.limit(self.limit)
        query.join("query_term_pub p", "p.doc_id = c.id")
        query.where("path LIKE '/Summary%ProtocolRef%'")
        rows = query.execute(self.cursor).fetchall()
        self.logger.info("Found %d docs with ProtocolRef links", len(rows))
        return [Summary(self, row.id) for row in rows]

    @cached_property
    def limit(self):
        """Throttle for testing."""
        return int(self.fields.getvalue("limit", "0").strip())

    @cached_property
    def prompt(self):
        """True if we should show a form page with instructions."""

        prompt = True if self.fields.getvalue("prompt") else False
        self.logger.info("prompt=%s", prompt)
        return prompt

    @cached_property
    def ready(self):
        """True if we should proceed with generating the report."""

        if self.prompt:
            return False
        try:
            if self.limit < 0:
                message = "Limit must be greater than zero."
                self.alerts.append(dict(message=message, type="error"))
                return False
            elif self.limit > 0:
                message = f"Limited to {self.limit} summaries for testing."
                self.logger.info(message)
                self.alerts.append(dict(message=message, type="info"))
        except Exception:
            value = self.fields.getvalue("limit")
            self.logger.exception("checking limit %r", value)
            message = "Limit must be a positive integer."
            self.alerts.append(dict(message=message, type="error"))
            return False
        return True

    @cached_property
    def rows(self):
        """Values for the details table."""

        rows = []
        for doc in self.docs:
            rows.extend(doc.rows)
        return rows

    @cached_property
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

    @cached_property
    def wide_css(self):
        """Use more horizontal space for the report."""
        return self.Reporter.Table.WIDE_CSS


class Summary:
    """CDR Summary document with protocol links."""

    def __init__(self, control, id):
        """Save the caller's values.

        Pass:
            control - access to the current session and report-building tools
            id - integer for the CDR document ID
        """

        self.control = control
        self.id = id

    @cached_property
    def doc(self):
        """`Doc` object for the summary."""

        self.doc = Doc(self.control.session, id=self.id)
        self.control.logger.info("Processing %s", self.doc.cdr_id)
        return self.doc

    @cached_property
    def rows(self):
        """Values for the report, one row for each link."""

        nct_ids = set()
        protocol_refs = set()
        for node in self.doc.root.iter("ProtocolRef"):
            protocol_id = Doc.get_text(node)
            nct_id = node.get("nct_id", "").strip() or ""
            if nct_id:
                nct_ids.add(nct_id)
            protocol_refs.add((protocol_id, nct_id))
        # opts = dict(timeout=(5, 5), verify=False, allow_redirects=True)
        urls = {}
        for nct_id in nct_ids:
            url = f"https://www.cancer.gov/clinicaltrials/{nct_id}"
            try:
                response = requests.head(url, allow_redirects=True)
                urls[nct_id] = response.url
                args = nct_id, response.url
                self.control.logger.debug("%s -> %s", *args)
            except Exception:
                self.control.logger.exception("Failure for %s", url)
                urls[nct_id] = "*** URL timed out"
        rows = []
        for protocol_id, nct_id in sorted(protocol_refs):
            rows.append([
                self.doc.id,
                self.title,
                protocol_id,
                urls[nct_id] if nct_id else "None",
            ])
        return rows

    @cached_property
    def title(self):
        """String for the Summary document's title."""
        return Doc.get_text(self.doc.root.find("SummaryTitle"))


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
