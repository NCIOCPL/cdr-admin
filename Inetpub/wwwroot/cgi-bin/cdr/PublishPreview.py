#!/usr/bin/env python

"""Show the user what the document will look like on the web site.
"""

from argparse import ArgumentParser
from datetime import datetime
from re import search
from sys import stderr
from cdrcgi import Controller, DOCID, sendPage
from cdrapi.publishing import DrupalClient
from cdrapi.docs import Doc
import cdr2gk
import cdrpub
from lxml import etree, html
import requests
from cdr import TMP

# TODO: Get Acquia to fix their broken certificates.
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


class Control(Controller):
    """Access to the database and page-building facilities."""

    LOGNAME = "PublishPreview"

    def show_form(self):
        """Bypass the form, which isn't used by this script."""
        self.show_report()

    def show_report(self):
        """Override the base class, as this isn't a tabular report."""

        self.show_progress("started...")
        page = html.tostring(self.page, encoding="unicode")
        args = len(page), self.elapsed
        self.show_progress("Complete!")
        self.logger.info("Assembled %d bytes; elapsed: %s", *args)
        sendPage(page)

    def send(self):
        elapsed = (datetime.datetime.now() - self.start).total_seconds()
        page = html.tostring(self.page)
        args = len(page), elapsed
        message = "Assembled %d bytes in %f seconds"
        self.doc.session.logger.info(message, *args)
        sys.stdout.buffer.write(b"Content-type: text/html; charset=utf-8\n\n")
        sys.stdout.buffer.write(page)

    def show_progress(self, progress):
        """If enabled, write processing progress to the console."""

        if self.monitor:
            now = datetime.now()
            stderr.write(f"[{now}] {progress}\n")

    @property
    def cached_html(self):
        """If True, load HTML from the named file (default is False)."""

        if not hasattr(self, "_cached_html"):
            if self.opts is None:
                self._cached_html = self.fields.getvalue("cached")
            else:
                self._cached_html = self.opts.cached_html
        return self._cached_html

    @property
    def debugging(self):
        """If True, increase the level of logging (default is False)."""

        if not hasattr(self, "_debugging"):
            if self.opts is None:
                self._debugging = self.fields.getvalue("DebugLog")
            else:
                self._debugging = self.opts.debug
        return self._debugging

    @property
    def doctype(self):
        """String for the name of this document's type."""

        if not hasattr(self, "_doctype"):
            self._doctype = Doc(self.session, id=self.id).doctype.name
            self.show_progress(f"found doctype {self._doctype}...")
        return self._doctype

    @property
    def drupal_host(self):
        """Override the default Drupal host name."""

        if not hasattr(self, "_drupal_host"):
            if self.opts is None:
                self._drupal_host = self.fields.getvalue("DrupalHost")
            else:
                self._drupal_host = self.opts.drupal_host
        return self._drupal_host

    @property
    def flavor(self):
        """Override the default report flavor for glossary docs."""

        if not hasattr(self, "_flavor"):
            if self.opts is None:
                self._flavor = self.fields.getvalue("Flavor", "GlossaryTerm")
            else:
                self._flavor = self.opts.flavor
        return self._flavor

    @property
    def gk_host(self):
        """Override the default GateKeeper host name."""

        if not hasattr(self, "_gk_host"):
            if self.opts is None:
                self._gk_host = self.fields.getvalue("gkHost")
            else:
                self._gk_host = self.opts.gk_host
        return self._gk_host

    @property
    def id(self):
        """CDR ID for the doccument to process."""

        if not hasattr(self, "_id"):
            if self.opts is None:
                id = self.fields.getvalue(DOCID)
            else:
                id = self.opts.id
            if not id:
                self.bail("Required document ID missing")
            try:
                self._id = Doc.extract_id(id)
            except:
                self.bail("Invalid ID")
        return self._id

    @property
    def monitor(self):
        """If True, print progress to the console."""

        if not hasattr(self, "_monitor"):
            self._monitor = False
            if self.opts is not None:
                self._monitor = self.opts.monitor
        return self._monitor

    @property
    def opts(self):
        """Command-line options for debugging without a browser."""

        if not hasattr(self, "_opts"):
            self._opts = None
            if not self.fields:
                parser = ArgumentParser()
                parser.add_argument("--id", "-i", required=True)
                parser.add_argument("--version", "-v")
                parser.add_argument("--monitor", "-m", action="store_true")
                parser.add_argument("--preserve_links", action="store_true")
                parser.add_argument("--debug", "-d", action="store_true")
                parser.add_argument("--drupal_host")
                parser.add_argument("--flavor", "-f", default="GlossaryTerm")
                parser.add_argument("--gk_host", "-g")
                parser.add_argument("--cached_html", "-c")
                parser.add_argument("--session", "-s")
                self._opts = parser.parse_args()
        return self._opts

    @property
    def page(self):
        """Prepared document, ready to be presented to the user."""

        if self.doctype == "Summary":
            page = CIS(self).page
        elif self.doctype == "DrugInformationSummary":
            page = DIS(self).page
        elif self.doctype == "GlossaryTermName":
            page = GTN(self).page
        else:
            self.bail("Document type not supported")
        if self.debugging:
            with open(f"{TMP}/pp-{self.id}.html", "wb") as fp:
                fp.write(html.tostring(page, encoding="utf-8"))
        return page

    @property
    def preserve_links(self):
        """If False (the default), we modify links to work on this server."""

        if not hasattr(self, "_preserve_links"):
            if self.opts is None:
                self._preserve_links = self.fields.getvalue("OrigLinks")
            else:
                self._preserve_links = self.opts.preserve_links
        return self._preserve_links

    @property
    def session(self):
        """Login session, possibly overridden at the command line."""

        if not hasattr(self, "_session_pp"):
            if self.opts is not None and self.opts.session:
                self._session_pp = Session(self.opts.session)
            else:
                self._session_pp = super().session
        return self._session_pp

    @property
    def version(self):
        """Which version of the document to show."""

        if not hasattr(self, "_version"):
            if self.opts is not None:
                self._version = self.opts.version
            else:
                self._version = self.fields.getvalue("Version")
            if self._version == "cwd":
                self._version = ""
        return self._version


class Summary:
    """Base class for PDQ summary documents (cancer and drug information)"""

    SCRIPT = "PublishPreview.py"
    TIER_SUFFIXES = dict(DEV="-blue-dev", PROD="")
    IMAGE_PATH = "/images/cdr/live"
    URL_PATHS = (
        "/Summary/SummaryMetaData/SummaryURL/@cdr:xref",
        "/DrugInformationSummary/DrugInfoMetaData/URL/@cdr:xref"
    )

    def __init__(self, control):
        """Remember the caller's value.

        Pass:
            control - access to the current login session and the report args
        """

        self.__control = control

    @property
    def client(self):
        """Interface with the CMS server."""

        if not hasattr(self, "_client"):
            self._client = DrupalClient(self.doc.session)
        return self._client

    @property
    def cms_doc(self):
        """Page returned by the Drupal server."""

        parser = etree.HTMLParser()
        nid = None
        espanol = ""
        if self.values.get("language") == "es":
            espanol = "/espanol"
        url = f"{self.client.base}/user/login?_format=json"
        name, password = self.client.auth
        data = {"name": name, "pass": password}
        try:
            self.__control.show_progress("logging on to Drupal CMS...")
            response = requests.post(url, json=data, verify=False)
            cookies = response.cookies
            self.__control.show_progress("pushing summary values to Drupal...")
            nid = self.client.push(self.values)
            url = f"{self.client.base}{espanol}/node/{nid}"
            self.__control.show_progress("fetching HTML from Drupal server...")
            response = requests.get(url, cookies=cookies, verify=False)
            self.__control.show_progress("received response from Drupal...")
            return etree.fromstring(response.content, parser=parser)
        except Exception as e:
            cdrcgi.bail(f"Failure generating preview: {e}")
        finally:
            if nid is not None:
                self.client.remove(self.values["cdr_id"])

    @property
    def doc(self):
        """`Doc` object for the summary being previewed."""

        if not hasattr(self, "_doc"):
            opts = dict(id=self.__control.id, version=self.__control.version)
            self._doc = Doc(self.__control.session, **opts)
            self.__control.show_progress("fetched document...")
        return self._doc

    @property
    def page(self):
        """HTML page ready to be returned to the user."""

        if not hasattr(self, "_page"):
            if self.__control.preserve_links:
                self.__control.show_progress("preserving links...")
                self._page = self.cms_doc
                return self._page
            page = self.cms_doc
            self.__control.show_progress("fixing links...")
            for script in page.iter("script"):
                url = script.get("src", "")
                if url and not url.startswith("https:"):
                    if not url.startswith("http"):
                        url = f"{self.client.base}{url}"
                    src = f"proxy.py?url={url}"
                    script.set("src", src)
            for link in page.findall("head/link"):
                url = link.get("href", "")
                if not url.startswith("https://"):
                    if not url.startswith("http"):
                        url = f"{self.client.base}{url}"
                    href = f"proxy.py?url={url}"
                    link.set("href", href)
            suffix = self.TIER_SUFFIXES.get(self.doc.session.tier.name, "-qa")
            image_host = f"www{suffix}.cancer.gov"
            replacement = f"https://{image_host}{self.IMAGE_PATH}"
            for img in page.iter("img"):
                src = img.get("src", "")
                if src.startswith(self.IMAGE_PATH):
                    src = src.replace(self.IMAGE_PATH, replacement)
                    img.set("src", src)
                elif not src.startswith("http"):
                    img.set("src", f"{self.client.base}{src}")
            script = self.__control.script
            for a in page.xpath("//a[@href]"):
                if "nav-item-xxtitle" in (a.getparent().get("class", "")):
                    continue
                link_type = "unknown"
                fixed = href = (a.get("href", "")).strip()
                if "Common/PopUps" in href:
                    continue
                self.__control.logger.debug("@href=%r", href)
                if href.startswith("http"):
                    link_type = "ExternalLink"
                elif href.startswith("#cit"):
                    link_type = "CitationLink"
                else:
                    id = self.extract_id_from_url(href)
                    if href.startswith("#"):
                        link_type = "SummaryFragRef-internal-frag"
                    elif href.startswith("/"):
                        if id:
                            if "#" in href:
                                frag = href.split("#")[1]
                                if id == self.doc.id:
                                    fixed = f"#{frag}"
                                    link_type = "SummaryFragRef-internal+uri"
                                else:
                                    fixed = f"{script}?{DOCID}={id:d}#{frag}"
                                    link_type = "SummaryFragRef-external"
                            else:
                                fixed = f"{script}?{DOCID}={id:d}"
                                link_type = "SummaryRef-external"
                        else:
                            fixed = f"{self.client.base}{href}"
                            link_type = "Cancer.gov-link"
                    else:
                        link_type = "Dead-link"
                        self.__control.logger.info("glossary popup %r", href)
                a.set("href", fixed)
                a.set("ohref", href)
                a.set("type", link_type)
            self._page = page
        return self._page

    @property
    def urls(self):
        """Map of summary URLs to summary document IDs."""

        if not hasattr(self, "_urls"):
            self._urls = dict()
            session = self.doc.session
            for path in self.URL_PATHS:
                fields = "q.doc_id", "q.value"
                query = self.__control.Query("query_term q", *fields)
                query.join("active_doc a", "a.id = q.doc_id")
                query.where(query.Condition("q.path", path))
                for doc_id, url in query.execute(session.cursor).fetchall():
                    url = url.replace("https://www.cancer.gov", "")
                    url = url.replace("http://www.cancer.gov", "")
                    self._urls[url.lower().strip()] = doc_id
            self.__control.logger.info("loaded %d urls", len(self._urls))
        return self._urls

    @property
    def values(self):
        """Dictionary of values to be sent to the CMS.

        We use a negative CDR ID to avoid conflicts with live summaries.
        """

        if not hasattr(self, "_values"):
            opts = dict(parms=dict(DateFirstPub="", isPP="Y"))
            result = self.doc.filter(self.VENDOR_FILTERS, **opts)
            root = result.result_tree.getroot()
            xsl = Doc.load_single_filter(self.doc.session, self.CMS_FILTER)
            args = self.doc.session, self.doc.id, xsl, root
            self._values = self.ASSEMBLE(*args)
            self._values["cdr_id"] = -self._values["cdr_id"]
            self.__control.show_progress("filtered document...")
        return self._values

    def extract_id_from_url(self, url):
        """
        If the URL matches a PDQ summary return its CDR ID
        """

        self.doc.session.logger.debug("checking URL %r", url)
        url = url.split("#")[0].rstrip("/").lower()
        if url:
            doc_id = self.urls.get(url)
            if doc_id:
                self.doc.session.logger.debug("found %d", doc_id)
            return doc_id
        return None


class CIS(Summary):
    VENDOR_FILTERS = "set:Vendor Summary Set"
    CMS_FILTER = "Cancer Information Summary for Drupal CMS"
    ASSEMBLE = cdrpub.Control.assemble_values_for_cis


class DIS(Summary):
    VENDOR_FILTERS = "set:Vendor DrugInfoSummary Set"
    CMS_FILTER = "Drug Information Summary for Drupal CMS"
    ASSEMBLE = cdrpub.Control.assemble_values_for_dis


class GTN:
    """GlossaryTermName CDR document."""

    VENDOR_FILTERS = "set:Vendor GlossaryTerm Set"
    CIS_URL = "/Summary/SummaryMetaData/SummaryURL/@cdr:xref"
    DIS_URL = "/DrugInformationSummary/DrugInfoMetaData/URL/@cdr:xref"
    GATEKEEPER_ERROR_MESSAGES = (
        ("Validation Error",
        "Top-level section _\d* is missing a required Title."),
        ("DTD Error", "The element '\w*' has invalid child element"),
    )

    def __init__(self, control):
        """Save the caller's value.

        Pass:
            control - access to the database and the current login session
        """

        self.__control = control

    @property
    def doc(self):
        """`Doc` object for the GlossaryTermName document."""

        if not hasattr(self, "_doc"):
            version = self.__control.version or "lastp"
            if version == "cwd":
                version = None
            opts = dict(id=self.__control.id, version=version)
            self._doc = Doc(self.__control.session, **opts)
            self.__control.show_progress("fetched document...")
        return self._doc

    @property
    def filtered_doc(self):
        """Parsed XML document prepared as we do for export."""

        result = self.doc.filter(self.VENDOR_FILTERS, isPP="Y")
        root = result.result_tree.getroot()
        self.__control.show_progress("filtered document...")
        return root

    @property
    def gatekeeper_doc(self):
        """Document returned by the GateKeeper SOAP service."""

        if self.__control.cached_html:
            root = html.parse(self.__control.cached_html).getroot()
            self.__control.show_progress("loaded cached html")
            return root
        else:
            xml = etree.tostring(self.filtered_doc, encoding="unicode")
            cdr2gk.DEBUGLEVEL = 0
            if self.__control.debugging:
                cdr2gk.DEBUGLEVEL = 3
                self.__control.show_progress("gatekeeper debugging enabled...")
            self.__control.show_progress("submitting doc to GateKeeper...")
            flavor = self.__control.flavor
            host = self.__control.gk_host
            try:
                response = cdr2gk.pubPreview(xml, flavor, host=host)
            except Exception as e:
                self.__control.logger.exception("GateKeeper failure")
                self.__show_gatekeeper_error(str(e))
            self.__control.show_progress("received GateKeeper response...")
            return html.fromstring(response.xmlResult)

    @property
    def page(self):
        """Publish preview page ready for delivery."""

        root = self.gatekeeper_doc
        root.find("head/title").text = f"Publish Preview: CDR{self.doc.id}"
        if self.__control.preserve_links:
            self.__control.show_progress("preserving original links...")
        else:
            self.__transform_links(root)
        return root

    def __lookup_url(self, url):
        """Find the document a URL belongs to."""

        url = url.split("#")[0].rstrip("/")
        query = self.__control.Query("query_term u", "u.doc_id")
        query.join("active_doc d", "d.id = u.doc_id")
        query.where(f"u.path IN ('{self.CIS_URL}', '{self.DIS_URL}')")
        query.where(query.Condition("u.value", url, "LIKE"))
        rows = query.execute(self.__control.cursor).fetchall()
        return rows[0].doc_id if rows else None

    def __show_gatekeeper_error(self, error):
        """Explain what went wrong with GateKeeper and exit.

        Pass:
            error - string from raised exception
        """

        message = "Unspecified error"
        for error_type, pattern in self.GATEKEEPER_ERROR_MESSAGES:
            matches = search(pattern, error)
            if matches:
                message = f"{error_type}: {matches.group()}"
                break
        extra = message, "Complete Error message below:", error
        cdrcgi.bail("Error in PubPreview:", extra=extra)

    def __transform_links(self, root):
        """Modify the links so that they will work locally."""

        self.__control.show_progress("fixing links...")
        cgov = self.__control.session.tier.hosts["CG"]
        for link in root.xpath("//a[@href]"):
            url = link.get("href", "").strip()
            id = self.__lookup_url(url)
            classes = link.get("class", "")
            if "CDR_audiofile" in classes:
                id = Doc.extract_id(url.replace(".mp3", ""))
                link.set("href", f"GetCdrBlob.py?id={id}")
            elif url.startswith("http"):
                link.set("type", "ExternalLink")
            elif "#cit" in url:
                link.set("type", "CitationLink")
            elif url.startswith("#") and id == self.doc.id:
                link.set("href", f"#{url.split('#')[1]}")
                link.set("type", "SummaryFragRef-internal-frag")
            elif url.startswith("/"):
                if id:
                    if id == self.doc.id and "#" in url:
                        link.set("href", f"#{url.split('#')[1]}")
                        link.set("type", "SummaryFragRef-internal+url")
                    elif "#" in url:
                        fragment = url.split("#")[1]
                        new_url = f"PublishPreview.py?DocId={id}#{fragment}"
                        link.set("href", new_url)
                        link.set("type", "SummaryFragRef-external")
                    else:
                        link.set("href", f"PublishPreview.py?DocId={id}")
                        link.set("type", "SummaryRef-external")
                else:
                    link.set("href", f"http://{cgov}{url}")
            elif "=" in url:
                link.set("href", f"PublishPreview.py?DocId=url.split('=')[1]")
                link.set("type", "related-link")
            else:
                continue
            link.set("ohref", url)
        for script in root.findall("head/script"):
            src = script.get("src", "")
            if src.startswith("http://"):
                script.set("src", f"proxy.py?url={src}")
        for link in root.findall("head/link"):
            href = link.get("href", "")
            if href.startswith("http://"):
                href = href.replace("cancer.gov//", "cancer.gov/")
                link.set(f"proxy.py?url={href}")
        path = "//a[starts-with(@onclick, 'javascript:popWindow')]"
        for link in root.xpath(path):
            link.set("href", "")
            link.set("onclick", "return false")
        for link in root.xpath("//*[starts-with(@src, 'http')]"):
            src = link.get("src")
            if "://cdr" in src:
                link.set("src", "/" + src.split("//")[1].split("/", 1)[1])


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
