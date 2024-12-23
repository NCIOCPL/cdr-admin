#!/usr/bin/env python

"""Show the user what the document will look like on the web site.
"""

from argparse import ArgumentParser
from datetime import datetime
from functools import cached_property
from json import loads
from re import search
from sys import stderr
from cdrcgi import Controller
from cdrapi.publishing import DrupalClient
from cdrapi.docs import Doc
from cdrapi.users import Session
import cdrpub
from lxml import etree, html
from lxml.html import builder
import requests
from cdr import TMP


# TODO: Get Acquia to fix their broken certificates.
from urllib3.exceptions import InsecureRequestWarning
# pylint: disable-next=no-member
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
            stderr.write(f"[{datetime.now()}] {progress}\n")

    @cached_property
    def cached_html(self):
        """If True, load HTML from the named file (default is False)."""

        if self.opts is None:
            return self.fields.getvalue("cached")
        return self.opts.cached_html

    @cached_property
    def debugging(self):
        """If True, increase the level of logging (default is False)."""

        if self.opts is None:
            return self.fields.getvalue("DebugLog")
        return self.opts.debug

    @cached_property
    def doctype(self):
        """String for the name of this document's type."""

        doctype = Doc(self.session, id=self.id).doctype.name
        self.show_progress(f"found doctype {doctype}...")
        return doctype

    @cached_property
    def drupal_host(self):
        """Override the default Drupal host name."""

        if self.opts is None:
            return self.fields.getvalue("DrupalHost")
        return self.opts.drupal_host

    @cached_property
    def id(self):
        """CDR ID for the doccument to process."""

        if self.opts is not None:
            id = self.opts.id
        else:
            id = self.fields.getvalue(self.DOCID)
        if not id:
            self.bail("Required document ID missing")
        try:
            id = Doc.extract_id(id)
        except Exception:
            self.bail("Invalid ID")
        if id <= 0:
            self.bail("Invalid ID")
        return id

    @cached_property
    def monitor(self):
        """If True, print progress to the console."""
        return self.opts.monitor if self.opts is not None else False

    @cached_property
    def opts(self):
        """Command-line options for debugging without a browser."""

        if self.fields:
            return None
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
        return parser.parse_args()

    @cached_property
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

    @cached_property
    def password(self):
        """Override for the password used by the PDQ Drupal account."""

        if self.opts is None:
            return self.fields.getvalue("Password")
        return self.opts.password

    @cached_property
    def preserve_links(self):
        """If False (the default), we modify links to work on this server."""

        if self.opts is None:
            return self.fields.getvalue("OrigLinks")
        return self.opts.preserve_links

    @cached_property
    def session(self):
        """Login session, possibly overridden at the command line."""

        if self.opts is not None and self.opts.session:
            return Session(self.opts.session)
        return super().session

    @cached_property
    def version(self):
        """Which version of the document to show."""

        if self.opts is not None:
            version = self.opts.version
        else:
            version = self.fields.getvalue("Version")
        return "" if version == "cwd" else version


class Summary:
    """Base class for PDQ summary documents (cancer and drug information)"""

    SCRIPT = "PublishPreview.py"
    DOCID = Controller.DOCID
    IMAGE_PATH = "/pdq/media/images"
    IMAGE_PATTERN = "pdq/media/images/([0-9-]+)\\.jpg"
    NCI_LOGO = "files/ncids_header/logos/Logo_NCI\\.svg"
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

        self.control = control

    @cached_property
    def client(self):
        """Interface with the CMS server."""

        opts = {}
        if self.control.password:
            opts["auth"] = "PDQ", self.control.password
        if self.control.drupal_host:
            opts["base"] = self.control.drupal_host
        return DrupalClient(self.doc.session, **opts)

    @cached_property
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
            self.control.show_progress("logging on to Drupal CMS...")
            response = requests.post(url, json=data, verify=False)
            cookies = response.cookies
            self.control.show_progress("clearing old temp docs...")
            if isinstance(self.doc.id, int):
                # pylint: disable-next=invalid-unary-operand-type
                self.client.remove(-self.doc.id)
            self.control.show_progress("pushing summary values to Drupal...")
            nid = self.client.push(self.values)
            url = f"{self.client.base}{espanol}/node/{nid}"
            self.control.show_progress("fetching HTML from Drupal server...")
            response = requests.get(url, cookies=cookies, verify=False)
            self.control.show_progress("received response from Drupal...")
            return etree.fromstring(response.content, parser=parser)
        except Exception as e:
            self.control.logger.exception("Failure create publish preview")
            self.control.bail(f"Failure generating preview: {e}")
        finally:
            if nid is not None:
                self.client.remove(self.values["cdr_id"])

    @cached_property
    def doc(self):
        """`Doc` object for the summary being previewed."""

        opts = dict(id=self.control.id, version=self.control.version)
        doc = Doc(self.control.session, **opts)
        self.control.show_progress("fetched document...")
        return doc

    @cached_property
    def page(self):
        """HTML page ready to be returned to the user."""

        if self.control.preserve_links:
            self.control.show_progress("preserving links...")
            return self.cms_doc
        page = self.cms_doc
        self.control.show_progress("fixing links...")
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

        # The NCI Logo sits within a picture element.  Its display
        # needs to be handled differently from the img elements.
        for source in page.iter("source"):
            self.control.show_progress("fixing NCI Logo link...")
            srcset = source.get("srcset", "")
            match = search(self.NCI_LOGO, srcset)
            if match:
                source.set("srcset", f"{self.CANCER_GOV}{srcset}")

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
        script = self.control.script
        for a in page.xpath("//a[@href]"):
            link_type = "unknown"
            fixed = href = a.get("href", "").strip()
            if "Common/PopUps" in href:
                continue
            self.control.logger.debug("@href=%r", href)
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
                                fixed = f"{script}?{self.DOCID}={id:d}#{frag}"
                                link_type = "SummaryFragRef-external"
                        else:
                            fixed = f"{script}?{self.DOCID}={id:d}"
                            link_type = "SummaryRef-external"
                    else:
                        fixed = f"{self.CANCER_GOV}{href}"
                        link_type = "Cancer.gov-link"
                else:
                    link_type = "Dead-link"
                    self.control.logger.info("glossary popup %r", href)
            a.set("href", fixed)
            a.set("ohref", href)
            a.set("type", link_type)
        return page

    @cached_property
    def urls(self):
        """Map of summary URLs to summary document IDs."""

        urls = {}
        session = self.doc.session
        for path in self.URL_PATHS:
            fields = "q.doc_id", "q.value"
            query = self.control.Query("query_term q", *fields)
            query.join("active_doc a", "a.id = q.doc_id")
            query.where(query.Condition("q.path", path))
            for doc_id, url in query.execute(session.cursor).fetchall():
                url = url.replace("https://www.cancer.gov", "")
                url = url.replace("http://www.cancer.gov", "")
                urls[url.lower().strip()] = doc_id
        self.control.logger.info("loaded %d urls", len(urls))
        return urls

    @cached_property
    def values(self):
        """Dictionary of values to be sent to the CMS.

        We use a negative CDR ID to avoid conflicts with live summaries.
        """

        opts = dict(parms=dict(DateFirstPub="", isPP="Y"))
        result = self.doc.filter(self.VENDOR_FILTERS, **opts)
        root = result.result_tree.getroot()
        xsl = Doc.load_single_filter(self.doc.session, self.CMS_FILTER)
        args = self.doc.session, self.doc.id, xsl, root
        values = self.ASSEMBLE(*args)
        values["cdr_id"] = -values["cdr_id"]
        self.control.show_progress("filtered document...")
        return values

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
        dict(
            src="https://code.jquery.com/jquery-3.6.0.min.js",
            integrity="sha256-/xUj+3OJU5yExlq6GSYGSHk7tPXikynS7ogEvDej/m4=",
            crossorigin="anonymous",
        ),
        dict(
            src="https://code.jquery.com/ui/1.13.0/jquery-ui.min.js",
            integrity="sha256-hlKLmzaRlE8SCJC1Kw8zoUbU8BxA+8kR3gseuKfMjxA=",
            crossorigin="anonymous",
            defer=None,
        ),
        dict(
            src=(
                "https://cdnjs.cloudflare.com/ajax/libs/jplayer/2.9.2"
                "/jplayer/jquery.jplayer.min.js"
            ),
        ),
        dict(
            src=(
                "https://www.cancer.gov/app-modules/glossary-app"
                "/glossary-app.v1.2.2/static/js/main.js"
            ),
            defer=None,
            onload=(
                "window.GlossaryApp(window.NCI_glossary_app_root_js_config)"
            ),
        ),
        dict(
            src=(
                "https://www.cancer.gov/profiles/custom/cgov_site/themes"
                "/custom/cgov/gcov_common/dist/js/Common.js"
            ),
            defer=None,
        ),
    )
    CSS = (
        dict(
            href=(
                "https://www.cancer.gov/profiles/custom/cgov_site/themes"
                "/custom/cgov/cgov_common/dist/css/Common.css"
            ),
            rel="stylesheet",
        ),
        dict(
            href=(
                "https://www.cancer.gov/app-modules/glossary-app"
                "/glossary-app.v1.2.2/static/css/main.css"
            ),
            rel="stylesheet",
        ),
    )
    STYLE = """\
dl.dictionary-list figure.image-left-medium { float: none; }
div.results { clear: both; }
dl dt { font-size: 1.75em; }
"""
    NAV = "LEFT NAV GOES HERE"
    JSFUNC = """
        function play_en() {
            var audio = document.getElementById('play-en');
            audio.play();
        }
        function play_es() {
            var audio = document.getElementById('play-es');
            audio.play();
        }"""

    def __init__(self, control):
        """Remember the caller's value.

        Pass:
            control - access to the report parameters and the database
        """

        self.control = control

    @cached_property
    def body(self):
        """DOM object for the HTML page's body."""

        return self.B.BODY(
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

    @cached_property
    def css_link_attrs(self):
        """Possibly overriden CDN links for CSS files."""

        query = self.control.Query("ctl", "val")
        query.where("grp = 'cdn'")
        query.where("name = 'pp-gtn-css'")
        query.where("inactivated IS NULL")
        row = query.execute(self.control.cursor).fetchone()
        if row:
            return loads(row.val)
        return self.CSS

    @cached_property
    def doc(self):
        """`Doc` object for the version to be previewed."""

        id = self.control.id
        version = self.control.version
        return Doc(self.control.session, id=id, version=version)

    @cached_property
    def head(self):
        """DOM object for the HTML page's head."""

        head = self.B.HEAD(self.B.META(charset="utf-8"), id="header")
        compat = self.B.META(content="IE=edge")
        compat.set("http-equiv", "X-UA-Compatible")
        head.append(compat)
        head.append(self.B.TITLE(self.title))
        for url in self.PRECONNECT:
            link = self.B.LINK(rel="preconnect", href=url)
            if not url.endswith("cancer.gov"):
                link.set("crossorigin")
            head.append(link)
        head.append(self.B.SCRIPT(src=self.ADOBE))
        fonts = self.B.LINK(id="gFonts", rel="stylesheet", href=self.FONTS)
        head.append(fonts)
        for name, content in self.META:
            head.append(self.B.META(name=name, content=content))
        for attrs in self.css_link_attrs:
            element = self.B.LINK()
            for key, value in attrs.items():
                element.set(key, value)
            if "rel" not in attrs:
                element.set("rel", "stylesheet")
            head.append(element)
        for attrs in self.script_link_attrs:
            element = self.B.SCRIPT()
            for key, value in attrs.items():
                element.set(key, value)
            head.append(element)
        head.append(self.B.STYLE(self.STYLE))
        head.append(self.B.SCRIPT(self.JSFUNC))
        return head

    @cached_property
    def left_nav(self):
        """Dummy placeholder for the left navigation bar."""

        return self.B.DIV(
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

    @cached_property
    def main(self):
        """HTML div wrapper for the page's main payload."""

        return self.B.DIV(
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

    @cached_property
    def page(self):
        """DOM object for the preview HTML page."""
        return self.B.HTML(self.head, self.body, lang="en", id="htmlEl")

    @cached_property
    def results(self):
        """Sequence of div blocks, one for each language."""

        results = []
        for language in self.control.LANGUAGES:
            for div in self.Result(self, language).divs:
                results.append(div)
        return results

    @cached_property
    def root(self):
        """Top-level element for the document, prepared for export."""

        opts = dict(parms=dict(isPP="Y"))
        result = self.doc.filter(self.VENDOR_FILTERS, **opts)
        return result.result_tree.getroot()

    @cached_property
    def script_link_attrs(self):
        """Optional override of script from database."""

        query = self.control.Query("ctl", "val")
        query.where("grp = 'cdn'")
        query.where("name = 'pp-gtn-js'")
        query.where("inactivated IS NULL")
        row = query.execute(self.control.cursor).fetchone()
        return loads(row.val) if row else self.SCRIPT

    @cached_property
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

            self.term = term
            self.language = language

        @cached_property
        def audio(self):
            """Media link for the term's pronunciation in this language.

            This needs to be an audio tag combined with a button to press.
            """

            if self.audio_url:
                B = self.term.B
                return B.DIV(
                    B.E(
                        "audio",
                        B.CLASS("CDR_audiofile"),
                        id=f"play-{self.langcode}",
                        type="audio/mpeg",
                        src=self.audio_url,
                    ),
                    B.E(
                        "button",
                        B.SPAN(
                            "Listen to pronunciation",
                            B.CLASS("show-for-sr")
                        ),
                        " ",
                        B.CLASS("btnAudio"),
                        onClick=f"play_{self.langcode}()",
                        type="button",
                    ),
                    B.CLASS("pronunciation__audio"),
                )
            return None

        @cached_property
        def audio_url(self):
            """String for the audio link's URL."""

            for node in self.term.root.findall("MediaLink"):
                if node.get("type") == "audio/mpeg":
                    if node.get("language") == self.langcode:
                        try:
                            id = Doc.extract_id(node.get("ref"))
                            return f"GetCdrBlob.py?id={id:d}"
                        except Exception:
                            self.term.control.logger.exception("audio ID")
            return None

        @cached_property
        def definitions(self):
            """Sequence of DD elements for this language."""

            definitions = []
            B = self.term.B
            name = "TermDefinition"
            if self.langcode == "es":
                name = "SpanishTermDefinition"
            for node in self.term.root.findall(f"{name}/DefinitionText"):
                # Definition with inline markup
                # A glossary definition may contain the following inline
                # markup elements: GeneName, ScientificName, Emphasis,
                # ForeignWord, strong, or ExternalRef. We're building the
                # individual element objects and concatenating them to be
                # displayed within the DD element.
                # =======================================================
                if len(node):  # Definition includes inline markup
                    text = []
                    for element in node.iter():
                        if element.tag == 'Emphasis':
                            text.append(B.EM(element.text))
                        elif element.tag == 'ForeignWord':
                            text.append(B.EM(element.text,
                                             B.CLASS("foreign-word")))
                        elif element.tag == 'GeneName':
                            text.append(B.EM(element.text,
                                             B.CLASS("gene-name")))
                        elif element.tag == 'ScientificName':
                            text.append(B.EM(element.text,
                                             B.CLASS("scientific-name")))
                        elif element.tag == 'Strong':
                            text.append(B.B(element.text))
                        elif element.tag == 'ExternalRef':
                            attributes = element.attrib
                            text.append(B.A(element.text,
                                            href=attributes['xref']))
                        else:
                            text.append(element.text)
                        if element.tail:
                            text.append(element.tail)
                # No inline markup
                else:          # Definition is plain text
                    text = Doc.get_text(node, "").strip()

                if text:
                    if isinstance(text, list):
                        dd = B.DD(*text, B.BR(), B.CLASS("definition"))
                    else:
                        dd = B.DD(text, B.BR(), B.CLASS("definition"))
                    related = self.related
                    if related is not None:
                        dd.append(self.related)
                    definitions.append(dd)
            return definitions

        @cached_property
        def divs(self):
            """Sequence of top-level DIV elements for this language."""

            divs = []
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
                    divs.append(div)
            return divs

        @cached_property
        def drugs(self):
            """Links to related drug summary documents."""

            drugs = []
            path = "RelatedInformation/RelatedDrugSummaryRef"
            for node in self.term.root.findall(path):
                language = node.get("UseWith")
                if not language or language == self.langcode:
                    drugs.append(self.Ref(self, node))
            return drugs

        @cached_property
        def dt(self):
            """DT element for the term name."""

            name = self.name or "[MISSING NAME]"
            B = self.term.B
            dfn = B.DFN(name)
            dfn.set("data-cdr-id", str(self.term.doc.id))
            return B.DT(dfn)

        @cached_property
        def external(self):
            """Links to external resources."""

            external = []
            path = "RelatedInformation/RelatedExternalRef"
            for node in self.term.root.findall(path):
                language = node.get("UseWith")
                if not language or language == self.langcode:
                    external.append(self.Ref(self, node))
            return external

        @cached_property
        def images(self):
            """Sequence of `Image` objects for this language."""

            images = []
            for node in self.term.root.findall("MediaLink"):
                if node.get("type", "").startswith("image"):
                    if node.get("language") == self.langcode:
                        if node.get("audience") == "Patients":
                            images.append(self.Image(self, node))
            return images

        @cached_property
        def key(self):
            """String for the term's pronunciation key (English only)."""

            if self.langcode == "en":
                node = self.term.root.find("TermPronunciation")
                return Doc.get_text(node, "").strip()
            return None

        @cached_property
        def langcode(self):
            """String for the two-character ISO language code (en or es)."""
            return "en" if self.language == "English" else "es"

        @cached_property
        def name(self):
            """String for the name of the term in this block's language."""

            tag = "SpanishTermName" if self.langcode == "es" else "TermName"
            return Doc.get_text(self.term.root.find(tag), "").strip()

        @cached_property
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
                children.append(B.DIV(f" {self.key}",
                                      B.CLASS("pronunciation__key")))
            return B.DD(*children, B.CLASS("pronunciation"))

        @cached_property
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

        @cached_property
        def summaries(self):
            """Sequence of references to Cancer Information Summary docs."""

            summaries = []
            path = "RelatedInformation/RelatedSummaryRef"
            for node in self.term.root.findall(path):
                language = node.get("UseWith")
                if not language or language == self.langcode:
                    summaries.append(self.Ref(self, node))
            return summaries

        @cached_property
        def terms(self):
            """Sequence of links to related glossary terms."""

            terms = []
            path = "RelatedInformation/RelatedGlossaryTermRef"
            for node in self.term.root.findall(path):
                language = node.get("UseWith")
                if not language or language == self.langcode:
                    ref = self.Ref(self, node)
                    if ref.link is not None:
                        terms.append(ref)
            return terms

        @cached_property
        def videos(self):
            """Sequence of `Video` objects for this language block."""

            videos = []
            for node in self.term.root.findall("EmbeddedVideo"):
                langcode = node.get("language")
                if not langcode or langcode == self.langcode:
                    audience = node.get("audience")
                    if not audience or audience == "Patients":
                        videos.append(self.Video(self, node))
            return videos

        class Image:
            """Images associated with this glossary term."""

            def __init__(self, result, node):
                """Remember the caller's values.

                Pass:
                    result - block of the page for a specific language
                    node - node in which the image information is stored
                """

                self.node = node
                self.result = result

            @cached_property
            def alt(self):
                """String to be displayed if the image is unavailable."""
                return self.node.get("alt") or ""

            @cached_property
            def caption(self):
                """String to be displayed with the image."""

                for node in self.node.findall("Caption"):
                    langcode = node.get("language")
                    if not langcode or langcode == self.result.langcode:
                        return Doc.get_text(node, "").strip()
                return ""

            @cached_property
            def enlarge(self):
                """String for the button used to enlarge the image."""
                return "Ampliar" if self.result.langcode == "es" else "Enlarge"

            @cached_property
            def figure(self):
                """HTML FIGURE element wrapping the image on the page."""

                B = self.result.term.B
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

            @cached_property
            def id(self):
                """Integer for the image's CDR Media document."""

                try:
                    return Doc.extract_id(self.node.get("ref"))
                except Exception:
                    return None

            @cached_property
            def placement(self):
                """String for the image placement instructions.

                Ignored for now.
                """

                return self.node.get("placement")

            @cached_property
            def suffix(self):
                """String for the image's file name suffix."""

                mime_type = self.node.get("type", "")
                for suffix in ("gif", "png"):
                    if suffix in mime_type:
                        return suffix
                return "jpg"

        class Ref:
            """Link to a related resource."""

            def __init__(self, result, node):
                """Remember the caller's values.

                Pass:
                    result - section for this language's portion of the page
                    node - DOM node containing the link's information
                """

                self.result = result
                self.node = node

            @cached_property
            def item(self):
                """HTML LI element wrapping this link."""

                link = self.link
                if self.link is None:
                    return None
                return self.result.term.B.LI(link)

            @cached_property
            def link(self):
                """HTML A element for the link."""

                B = self.result.term.B
                return B.A(self.text, href=self.url) if self.url else None

            @cached_property
            def text(self):
                """String for the link's display text."""
                return Doc.get_text(self.node, "").strip()

            @cached_property
            def url(self):
                """String for the link's URL."""

                if "External" in self.node.tag:
                    return self.node.get("xref", "")
                if "Glossary" in self.node.tag:
                    href = self.node.get("href", "")
                    return f"PublishPreview.py?{Controller.DOCID}={href}"
                url = self.node.get("url", "")
                return f"https://www.cancer.gov{url}"

        class Video:
            """Embedded video for the glossary term."""

            def __init__(self, result, node):
                """Remember the caller's values.

                Pass:
                    result - section for this language's portion of the page
                    node - DOM node containing the link's information
                """

                self.result = result
                self.node = node

            @cached_property
            def caption(self):
                """String to be displayed with the embedded video."""

                node = self.node.find("Caption")
                return Doc.get_text(node, "").strip()

            @cached_property
            def classes(self):
                """CSS classes to be used for this embedded video."""

                position = "right" if "Right" in self.template else "center"
                size = 75
                if "100" in self.template:
                    size = 100
                elif "50" in self.template:
                    self = 50
                return f"video {position} size{size}"

            @cached_property
            def figure(self):
                """HTML figure element wrapping the embedded video."""

                B = self.result.term.B
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

            @cached_property
            def template(self):
                """String used to indicate how the video should be shown."""
                return self.node.get("template", "Video75NoTitle")

            @cached_property
            def title(self):
                """String for the embedded video's title."""
                return Doc.get_text(self.node.find("VideoTitle"), "").strip()

            @cached_property
            def uid(self):
                """YouTube ID for the video."""
                return self.node.get("unique_id", "")

            @cached_property
            def url(self):
                """String for the URL to display the video."""
                return f"https://www.youtube.com/watch?v={self.uid}"


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
