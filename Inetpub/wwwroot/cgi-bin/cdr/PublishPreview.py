#!/usr/bin/env python

"""Show the user what the document will look like on the web site.
"""

from argparse import ArgumentParser
from datetime import datetime
from re import search
from sys import stderr
from cdrcgi import Controller, DOCID
from cdrapi.publishing import DrupalClient
from cdrapi.docs import Doc
import cdrpub
from lxml import etree, html
from lxml.html import builder
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
        self.send_page(page)

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
                parser.add_argument("--password", "-p")
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
    def password(self):
        """Override for the password used by the PDQ Drupal account."""

        if not hasattr(self, "_password"):
            if self.opts is None:
                self._password = self.fields.getvalue("Password")
            else:
                self._password = self.opts.password
        return self._password

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
    IMAGE_PATH = "/pdq/media/images"
    IMAGE_PATTERN = "pdq/media/images/([0-9-]+)\\.jpg"
    CANCER_GOV = "https://www.cancer.gov"
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
            opts = {}
            if self.__control.password:
                opts["auth"] = "PDQ", self.__control.password
            if self.__control.drupal_host:
                opts["base"] = self.__control.drupal_host
            self._client = DrupalClient(self.doc.session, **opts)
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
            self.__control.bail(f"Failure generating preview: {e}")
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
                if url and not (url.startswith("https:") or
                                url.startswith("//")):
                    script.set("osrc", url)
                    if not url.startswith("http"):
                        url = f"{self.client.base}{url}"
                    src = f"proxy.py?url={url}"
                    script.set("src", src)
            for link in page.findall("head/link"):
                url = link.get("href", "")
                if not (url.startswith("https://") or url.startswith("//")):
                    link.set("ohref", url)
                    if not url.startswith("http"):
                        url = f"{self.client.base}{url}"
                    href = f"proxy.py?url={url}"
                    link.set("href", href)
            replacement = f"{self.CANCER_GOV}{self.IMAGE_PATH}"
            for img in page.iter("img"):
                src = img.get("src", "")
                img.set("osrc", src)
                match = search(self.IMAGE_PATTERN, src)
                if match:
                    img.set("src", f"GetCdrImage.py?pp=Y&id={match.group(1)}")
                elif src.startswith(self.IMAGE_PATH):
                    src = src.replace(self.IMAGE_PATH, replacement)
                    img.set("src", src)
                elif not (src.startswith("http") or src.startswith("//")):
                    img.set("src", f"{self.CANCER_GOV}{src}")
            script = self.__control.script
            for a in page.xpath("//a[@href]"):
                link_type = "unknown"
                fixed = href = a.get("href", "").strip()
                if "Common/PopUps" in href:
                    continue
                self.__control.logger.debug("@href=%r", href)
                match = search(self.IMAGE_PATTERN, href)
                if match:
                    link_type = "ImageLink"
                    fixed = f"GetCdrImage.py?pp=Y&id={match.group(1)}"
                elif href.startswith("http"):
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
                            fixed = f"{self.CANCER_GOV}{href}"
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
    """GlossaryTermName document."""

    MEDIA = "/PublishedContent/Media/CDR/media/"
    VENDOR_FILTERS = "set:Vendor GlossaryTerm Set"
    JSON_FILTER = "Glossary Term JSON"
    IMAGE_LOCATION = "[__imagelocation]"
    AUDIO_LOCATION = "[__audiolocation]"
    B = builder
    PRECONNECT = (
        "https://cdnjs.cloudflare.com",
        "https://ajax.googleapis.com",
        "https://fonts.gstatic.com",
        "https://static.cancer.gov",
    )
    FONTS = "https://fonts.googleapis.com/css"
    FONTS = f"{FONTS}?family=Noto+Sans:400,400i,700,700i"
    META = (
        ("content-language", "en"),
        ("english-linking-policy",
         "https://www.cancer.gov/global/web/policies/exit"),
        ("espanol-linking-policy",
         "https://www.cancer.gov/espanol/global/politicas/salda"),
        ("publishpreview", "undefined"),
        ("apple-mobile-web-app-title", "Cancer.gov"),
        ("application-name", "Cancer.gov"),
        ("theme-color", "#ffffff")
    )
    ADOBE = (
        "//assets.adobedtm.com/f1bfa9f7170c81b1a9a9ecdcc6c5215ee0b03c84"
        "/satelliteLib-5b3dcf1f2676c378b518a1583ef5355acd83cd3d.js"
    )
    SCRIPT = (
        ("https://ajax.googleapis.com/ajax/libs/jquery/3.1.1/jquery.min.js",
         False),
        ("https://ajax.googleapis.com/ajax/libs/jqueryui/1.12.1"
         "/jquery-ui.min.js",
         True),
        ("https://cdnjs.cloudflare.com/ajax/libs/jplayer/2.9.2"
         "/jplayer/jquery.jplayer.min.js", False),
        ("https://cancer.gov/PublishedContent/js/cdeConfig.js", False),
        ("https://cancer.gov/PublishedContent/js/Common.js", True),
        ("https://cancer.gov/PublishedContent/js/InnerPage.js", True),
        ("https://cancer.gov/PublishedContent/js/DictionaryPage.js", True),
    )
    CSS = (
        "https://cancer.gov/PublishedContent/Styles/Common.css",
        "https://cancer.gov/PublishedContent/Styles/InnerPage.css",
        "/stylesheets/fonts.css",
    )
    STYLE = "dl.dictionary-list figure.image-left-medium { float: none; }"
    STYLE = "div.results { clear: both; }"
    NAV = "LEFT NAV GOES HERE"


    def __init__(self, control):
        """Remember the caller's value.

        Pass:
            control - access to the report parameters and the database
        """

        self.__control = control

    @property
    def body(self):
        """DOM object for the HTML page's body."""

        if not hasattr(self, "_body"):
            self._body = self.B.BODY(
                self.B.DIV(
                    self.B.DIV(self.B.CLASS("fixedtotop")),
                    self.B.DIV(id="headerzone"),
                    self.B.DIV(
                        self.B.DIV(
                            self.B.DIV(
                                self.left_nav,
                                self.main,
                                self.B.CLASS("row"),
                            ),
                            self.B.CLASS(
                                "row general-page-body-container collapse"
                            ),
                        ),
                        self.B.CLASS("main-content"),
                        id="content",
                        tabindex="0",
                    ),
                    id="page",
                ),
                self.B.CLASS("nciappmodulepage"),
                id="Body1",
            )
        return self._body

    @property
    def control(self):
        """Access to the report parameters and the database."""
        return self.__control

    @property
    def doc(self):
        """`Doc` object for the version to be previewed."""

        if not hasattr(self, "_doc"):
            id = self.control.id
            version = self.control.version
            self._doc = Doc(self.control.session, id=id, version=version)
        return self._doc

    @property
    def head(self):
        """DOM object for the HTML page's head."""

        if not hasattr(self, "_head"):
            self._head = self.B.HEAD(self.B.META(charset="utf-8"), id="header")
            compat = self.B.META(content="IE=edge")
            compat.set("http-equiv", "X-UA-Compatible")
            self._head.append(compat)
            self._head.append(self.B.TITLE(self.title))
            for url in self.PRECONNECT:
                link = self.B.LINK(rel="prevcocnnect", href=url)
                if not url.endswith("cancer.gov"):
                    link.set("crossorigin")
                self._head.append(link)
            self._head.append(self.B.SCRIPT(src=self.ADOBE))
            fonts = self.B.LINK(id="gFonts", rel="stylesheet", href=self.FONTS)
            self._head.append(fonts)
            for name, content in self.META:
                self._head.append(self.B.META(name=name, content=content))
            for url in self.CSS:
                self._head.append(self.B.LINK(href=url, rel="stylesheet"))
            for url, defer in self.SCRIPT:
                script = self.B.SCRIPT(src=url, type="text/javascript")
                if defer:
                    script.set("defer")
                self._head.append(script)
            self._head.append(self.B.STYLE(self.STYLE))
        return self._head

    @property
    def left_nav(self):
        """Dummy placeholder for the left navigation bar."""

        if not hasattr(self, "_left_nav"):
            self._left_nav = self.B.DIV(
                self.B.DIV(
                    self.B.DIV(
                        self.B.UL(
                            self.B.LI(
                                self.B.DIV(self.B.A(self.NAV, href="#")),
                                self.B.CLASS("level-0 has-children"),
                            ),
                        ),
                        self.B.CLASS("section-nav"),
                    ),
                    self.B.CLASS("slot-item only-SI"),
                ),
                self.B.CLASS("medium-3 columns local-navigation"),
                id="nvcgSlSectionNav",
            )
        return self._left_nav

    @property
    def main(self):
        """HTML div wrapper for the page's main payload."""

        if not hasattr(self, "_main"):
            self._main = self.B.DIV(
                self.B.E(
                    "article",
                    self.B.DIV(
                        self.B.DIV(
                            self.B.DIV(
                                *self.results,
                                self.B.CLASS("slot-item last-SI"),
                            ),
                            id="cgvBody",
                        ),
                        self.B.CLASS("resize-content"),
                    ),
                ),
                self.B.CLASS("medium-9 columns contentzone has-section-nav"),
                id="main",
                tabindex="0",
                role="main",
            )
        return self._main

    @property
    def page(self):
        """DOM object for the preview HTML page."""

        if not hasattr(self, "_page"):
            attrs = dict(lang="en", id="htmlEl")
            self._page = self.B.HTML(self.head, self.body, **attrs)
        return self._page

    @property
    def results(self):
        """Sequence of div blocks, one for each language."""

        if not hasattr(self, "_results"):
            self._results = []
            for language in self.control.LANGUAGES:
                for div in self.Result(self, language).divs:
                    self._results.append(div)
        return self._results

    @property
    def root(self):
        """Top-level element for the document, prepared for export."""

        if not hasattr(self, "_root"):
            result = self.doc.filter(self.VENDOR_FILTERS)
            self._root = result.result_tree.getroot()
        return self._root

    @property
    def title(self):
        """String for the head's title element."""
        return f"Publish Preview: CDR{self.doc.id}"


    class Result:
        """Portion of the display specific to one language."""

        def __init__(self, term, language):
            """Remember the caller's values

            Pass:
                term - the `GTN` object for this preview
                language - the language for this block
            """

            self.__term = term
            self.__language = language

        @property
        def audio(self):
            """Media link for the term's pronunciation in this language."""

            if self.audio_url:
                B = self.term.B
                return B.A(
                    B.SPAN("listen", B.CLASS("hidden")),
                    B.CLASS("CDR_audiofile"),
                    href=self.audio_url,
                    type="ExternalLink",
                )
            return None

        @property
        def audio_url(self):
            """String for the audio link's URL."""

            if not hasattr(self, "_audio_url"):
                self._audio_url = id = None
                for node in self.term.root.findall("MediaLink"):
                    if node.get("type") == "audio/mpeg":
                        if node.get("language") == self.langcode:
                            try:
                                id = Doc.extract_id(node.get("ref"))
                                break
                            except Exception:
                                self.term.control.logger.exception("audio ID")
                if id:
                    self._audio_url = f"GetCdrBlob.py?id={id:d}"
            return self._audio_url

        @property
        def definitions(self):
            """Sequence of DD elements for this language."""

            if not hasattr(self, "_definitions"):
                self._definitions = []
                B = self.term.B
                name = "TermDefinition"
                if self.langcode == "es":
                    name = "SpanishTermDefinition"
                for node in self.term.root.findall(f"{name}/DefinitionText"):
                    text = Doc.get_text(node, "").strip()
                    if text:
                        dd = B.DD(text, B.BR(), B.CLASS("definition"))
                        related = self.related
                        if related is not None:
                            dd.append(self.related)
                        self._definitions.append(dd)
            return self._definitions

        @property
        def divs(self):
            """Sequence of top-level DIV elements for this language."""

            if not hasattr(self, "_divs"):
                self._divs = []
                if self.name:
                    B = self.term.B
                    for definition in self.definitions:
                        dl = B.DL(self.dt, B.CLASS("dictionary-list"))
                        div = B.DIV(B.BR(), dl, B.CLASS("results"))
                        div.set("data-dict-type", "term")
                        pronunciation = self.pronunciation
                        if pronunciation is not None:
                            dl.append(self.pronunciation)
                        dl.append(definition)
                        self._divs.append(div)
            return self._divs

        @property
        def drugs(self):
            """Links to related drug summary documents."""

            if not hasattr(self, "_drugs"):
                self._drugs = []
                path = "RelatedInformation/RelatedDrugSummaryRef"
                for node in self.term.root.findall(path):
                    language = node.get("UseWith")
                    if not language or language == self.langcode:
                        self._drugs.append(self.Ref(self, node))
            return self._drugs

        @property
        def dt(self):
            """DT element for the term name."""

            name = self.name or "[MISSING NAME]"
            B = self.term.B
            dfn = B.DFN(name)
            dfn.set("data-cdr-id", str(self.term.doc.id))
            return B.DT(dfn)

        @property
        def external(self):
            """Links to external resources."""

            if not hasattr(self, "_external"):
                self._external = []
                path = "RelatedInformation/RelatedExternalRef"
                for node in self.term.root.findall(path):
                    language = node.get("UseWith")
                    if not language or language == self.langcode:
                        self._external.append(self.Ref(self, node))
            return self._external

        @property
        def images(self):
            """Sequence of `Image` objects for this language."""

            if not hasattr(self, "_images"):
                self._images = []
                for node in self.term.root.findall("MediaLink"):
                    if node.get("type", "").startswith("image"):
                        if node.get("language") == self.langcode:
                            self._images.append(self.Image(self, node))
            return self._images

        @property
        def key(self):
            """String for the term's pronunciation key (English only)."""

            if not hasattr(self, "_key"):
                self._key = None
                if self.langcode == "en":
                    node = self.term.root.find("TermPronunciation")
                    self._key = Doc.get_text(node, "").strip()
            return self._key

        @property
        def langcode(self):
            """String for the two-character ISO language code (en or es)."""

            if not hasattr(self, "_langcode"):
                self._langcode = "en" if self.__language == "English" else "es"
            return self._langcode

        @property
        def name(self):
            """String for the name of the term in this block's language."""

            if not hasattr(self, "_name"):
                tag = "TermName"
                if self.langcode == "es":
                    tag = "SpanishTermName"
                node = self.term.root.find(tag)
                self._name = Doc.get_text(node, "").strip()
            return self._name

        @property
        def pronunciation(self):
            """DD element for the term name's pronunciation (if present)."""

            audio = self.audio
            if not self.key and audio is None:
                return None
            B = self.term.B
            children = []
            if audio is not None:
                children = [audio]
            if self.key:
                children.append(f" {self.key}")
            return B.DD(*children, B.CLASS("pronunciation"))

        @property
        def related(self):
            """DIV block for related resources (if any)."""

            terms = self.terms
            cis = self.summaries
            dis = self.drugs
            external = self.external
            images = self.images
            videos = self.videos
            if not (terms or cis or dis or external or images or videos):
                return None
            B = self.term.B
            div = B.DIV(B.CLASS("related-resources"))
            if terms or cis or dis or external:
                h6 = "More Information"
                if self.langcode == "es":
                    h6 = "M\xe1s informaci\xf3n"
                div.append(B.H6(h6))
            for collection in (external, cis, dis):
                items = []
                for ref in collection:
                    item = ref.item
                    if item is not None:
                        items.append(item)
                if items:
                    div.append(B.UL(*items, B.CLASS("no-bullets")))
            if terms:
                label = "Definition of: "
                items = [B.SPAN(label, B.CLASS("related-definition-label"))]
                separator = None
                for term in terms:
                    if separator:
                        items.append(separator)
                    items.append(term.link)
                    separator = ", "
                div.append(B.P(*items))
            for image in images:
                div.append(image.figure)
            for video in videos:
                div.append(video.figure)
            return B.DIV(div, id="pnlRelatedInfo")

        @property
        def summaries(self):
            """Sequence of references to Cancer Information Summary docs."""

            if not hasattr(self, "_summaries"):
                self._summaries = []
                path = "RelatedInformation/RelatedSummaryRef"
                for node in self.term.root.findall(path):
                    language = node.get("UseWith")
                    if not language or language == self.langcode:
                        self._summaries.append(self.Ref(self, node))
            return self._summaries

        @property
        def term(self):
            """Access to the glossary term being previewed."""
            return self.__term

        @property
        def terms(self):
            """Sequence of links to related glossary terms."""

            if not hasattr(self, "_terms"):
                self._terms = []
                path = "RelatedInformation/RelatedGlossaryTermRef"
                for node in self.term.root.findall(path):
                    language = node.get("UseWith")
                    if not language or language == self.langcode:
                        ref = self.Ref(self, node)
                        if ref.link is not None:
                            self._terms.append(ref)
            return self._terms

        @property
        def videos(self):
            """Sequence of `Video` objects for this language block."""

            if not hasattr(self, "_videos"):
                self._videos = []
                for node in self.term.root.findall("EmbeddedVideo"):
                    langcode = node.get("language")
                    if not langcode or langcode == self.langcode:
                        self._videos.append(self.Video(self, node))
            return self._videos


        class Image:
            """Images associated with this glossary term."""

            def __init__(self, result, node):
                """Remember the caller's values.

                Pass:
                    result - block of the page for a specific language
                    node - node in which the image information is stored
                """

                self.__node = node
                self.__result = result

            @property
            def alt(self):
                """String to be displayed if the image is unavailable."""

                if not hasattr(self, "_alt"):
                    self._alt = self.__node.get("alt") or ""
                return self._alt

            @property
            def caption(self):
                """String to be displayed with the image."""

                if not hasattr(self, "_caption"):
                    self._caption = ""
                    for node in self.__node.findall("Caption"):
                        langcode = node.get("language")
                        if not langcode or langcode == self.__result.langcode:
                            self._caption = Doc.get_text(node, "").strip()
                return self._caption

            @property
            def enlarge(self):
                """String for the button used to enlarge the image."""

                if not hasattr(self, "_enlarge"):
                    self._enlarge = "Enlarge"
                    if self.__result.langcode == "es":
                        self._enlarge = "Ampliar"
                return self._enlarge

            @property
            def figure(self):
                """HTML FIGURE element wrapping the image on the page."""

                B = self.__result.term.B
                href = f"GetCdrImage.py?id=CDR{self.id}-750.{self.suffix}"
                src = f"GetCdrImage.py?id=CDR{self.id}-571.{self.suffix}"
                return B.E(
                    "figure",
                    B.A(
                        self.enlarge,
                        B.CLASS("article-image-enlarge no-resize"),
                        target="_blank",
                        href=href,
                    ),
                    B.IMG(src=src, alt=self.alt),
                    B.E(
                        "figcaption",
                        B.DIV(
                            B.P(self.caption),
                            B.CLASS("caption-container no-resize"),
                        ),
                    ),
                    B.CLASS("image-left-medium"),
                )

            @property
            def id(self):
                """Integer for the image's CDR Media document."""

                if not hasattr(self, "_id"):
                    try:
                        self._id = Doc.extract_id(self.__node.get("ref"))
                    except:
                        self._id = None
                return self._id

            @property
            def placement(self):
                """String for the image placement instructions.

                Ignored for now.
                """

                if not hasattr(self, "_placement"):
                    self._placement = self.__node.get("placement")
                return self._placement

            @property
            def suffix(self):
                """String for the image's file name suffix."""

                if not hasattr(self, "_suffix"):
                    type = self.__node.get("type")
                    if "gif" in type:
                        self._suffix = "gif"
                    elif "png" in type:
                        self._suffix = "png"
                    else:
                        self._suffix = "jpg"
                return self._suffix


        class Ref:
            """Link to a related resource."""

            def __init__(self, result, node):
                """Remember the caller's values.

                Pass:
                    result - section for this language's portion of the page
                    node - DOM node containing the link's information
                """

                self.__result = result
                self.__node = node

            @property
            def item(self):
                """HTML LI element wrapping this link."""

                link = self.link
                if self.link is None:
                    return None
                return self.__result.term.B.LI(link)

            @property
            def link(self):
                """HTML A element for the link."""

                if self.url:
                    B = self.__result.term.B
                    return B.A(self.text, href=self.url)
                return None

            @property
            def text(self):
                """String for the link's display text."""

                if not hasattr(self, "_text"):
                    self._text = Doc.get_text(self.__node, "").strip()
                return self._text

            @property
            def url(self):
                """String for the link's URL."""

                if not hasattr(self, "_url"):
                    if "External" in self.__node.tag:
                        self._url = self.__node.get("xref", "")
                    elif "Glossary" in self.__node.tag:
                        href = self.__node.get("href", "")
                        self._url = f"PublishPreview.py?{DOCID}={href}"
                    else:
                        url = self.__node.get("url", "")
                        self._url = f"https://cancer.gov{url}"
                return self._url


        class Video:
            """Embedded video for the glossary term."""

            def __init__(self, result, node):
                """Remember the caller's values.

                Pass:
                    result - section for this language's portion of the page
                    node - DOM node containing the link's information
                """

                self.__result = result
                self.__node = node

            @property
            def caption(self):
                """String to be displayed with the embedded video."""

                if not hasattr(self, "_caption"):
                    node = self.__node.find("Caption")
                    self._caption = Doc.get_text(node, "").strip()
                return self._caption

            @property
            def classes(self):
                """CSS classes to be used for this embedded video."""

                if not hasattr(self, "_classes"):
                    size = 75
                    if "100" in self.template:
                        size = 100
                    elif "50" in self.template:
                        self = 50
                    position = "center"
                    if "Right" in self.template:
                        position = "right"
                    self._classes = f"video {position} size{size}"
                return self._classes

            @property
            def figure(self):
                """HTML figure element wrapping the embedded video."""

                B = self.__result.term.B
                figure = B.E("figure", B.CLASS(self.classes))
                if "NoTitle" not in self.template and self.title:
                    figure.append(B.H4(self.title))
                div = B.DIV(
                    B.NOSCRIPT(
                        B.P(
                            B.A(
                                "View this video on YouTube.",
                                href=self.url,
                                target="_blank",
                                title=self.title,
                            )
                        ),
                    ),
                    B.CLASS("flex-video widescreen"),
                    id=f"ytplayer-{self.uid}",
                )
                div.set("data-video-id", self.uid)
                if self.title:
                    div.set("data-video-title", self.title)
                figure.append(div)
                if self.caption:
                    classes = B.CLASS("caption-container no-resize")
                    caption = B.E("figcaption", self.caption, classes)
                    figure.append(caption)
                return figure

            @property
            def template(self):
                """String used to indicate how the video should be shown."""

                if not hasattr(self, "_template"):
                    default = "Video75NoTitle"
                    self._template = self.__node.get("template", default)
                return self._template

            @property
            def title(self):
                """String for the embedded video's title."""

                if not hasattr(self, "_title"):
                    node = self.__node.find("VideoTitle")
                    self._title = Doc.get_text(node, "").strip()
                return self._title

            @property
            def uid(self):
                """YouTube ID for the video."""

                if not hasattr(self, "_uid"):
                    self._uid = self.__node.get("unique_id", "")
                return self._uid

            @property
            def url(self):
                """String for the URL to display the video."""

                if not hasattr(self, "_url"):
                    self._url = f"https://www.youtube.com/watch?v={self.uid}"
                return self._url


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
