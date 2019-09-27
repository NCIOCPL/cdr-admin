#!/usr/bin/python

"""
Menu for testing publish preview on representative PDQ summaries.
"""

# Standard library modules.
import cgi
import datetime

# Third-party modules.
import requests
from lxml import etree, html

# Custom modules.
from cdrapi.db import Query
from cdrapi.docs import Doc
from cdrapi.users import Session
from cdrapi.publishing import DrupalClient
from cdrapi.settings import Tier
from cdrcgi import Page, bail
import cdrpub


class Control:
    """
    Processing control for new publish preview prototype
    """

    TIER = Tier()
    PP = "PublishPreview.py"
    URL = "http://ncigovcdode36.prod.acquia-sites.com"
    URL = "https://{}".format(TIER.hosts["DRUPAL"])
    CIS = {
        # Summary Type:
        "Adult Treatment": {
            # Topic: [HP English, Spanish], [Patient English, Spanish]
            "Breast": [[62787, 256668], [62955, 256762]],
            "Gastric": [[62911, 256670], [271446, 256764]],
            "Merkel Cell": [[62884, 256759], [441548, 470863]],
        },
        "Ped Treatment": {
            "Brain Stem Glioma": [[62761, 256675], [62962, 600419]],
            "Retinoblastoma": [[62846, 256693], [258033, 448617]],
        },
        "Genetics": {
            "Breast and Gynecologic": [[62855, None]],
            "Prostate": [[299612, None]],
        },
        "Integrative, alternative, and complementary therapies": {
            "High-Dose Vitamin C": [[742114, 773659], [742253, 773656]],
            "Mistletoe Extracts": [[269596, 778124], [449678, 778123]],
            "Bovine Shark Cartilage": [[62974, 789591], [446198, 789592]],
        },
        "Prevention": {
            "Breast": [[62779, 744468], [257994, 744469]],
            "Lung": [[62824, 733624], [62825, 729199]],
        },
        "Screening": {
            "Breast": [[62751, 744470], [257995, 744471]],
            "Lung": [[62832, 700433], [258019, 700560]],
        },
        "Supportive": {
            "Fatigue": [[62734, 256627], [62811, 256650]],
            "Pruritus": [[62748, 256645], [62805, 256622]],
        },
    }
    DIS = {
        "Bevacizumab": 487564,
        "BEP": 682526,
        "Blinatumomab": 767077,
    }
    CSS = """\
a { color: black; text-decoration: none; }
a:hover { color: maroon; }
"""

    def __init__(self):
        fields = cgi.FieldStorage()
        self.id = fields.getvalue("id")
        self.session = Session("guest")
        self.debug_level = int(fields.getvalue("debug") or "0")
        self.url = self.URL

    def run(self):
        self.show() if self.id else self.pick()

    def show(self):
        doc = Doc(self.session, id=self.id)
        if doc.doctype.name == "Summary":
            summary = CIS(self, doc)
        else:
            summary = DIS(self, doc)
        summary.send()

    def add_link(self, page, doc_id, title):
        url = f"{self.PP}?DocId={doc_id:d}"
        opts = dict(href=url, target="_blank")
        a = html.builder.A(title, **opts)
        page.add(a)
        page.add(html.builder.BR())

    def pick(self):
        page = Page("Publish Preview", subtitle="Prototype for Drupal CMS")
        page.add("<fieldset>")
        page.add(html.builder.LEGEND("Drugs"))
        for title in sorted(self.DIS):
            self.add_link(page, self.DIS[title], title + " Drug Summary")
        page.add("</fieldset>")
        for summary_type in sorted(self.CIS):
            topics = self.CIS[summary_type]
            page.add("<fieldset>")
            page.add(html.builder.LEGEND(summary_type))
            for topic in sorted(topics):
                audience = "HP"
                for pair in topics[topic]:
                    language = "English"
                    for doc_id in pair:
                        if doc_id is not None:
                            args = audience, topic, language
                            title = "{} {} Summary ({})".format(*args)
                            self.add_link(page, doc_id, title)
                        language = "Spanish"
                    audience = "Patient"
            page.add("</fieldset>")
        page.add_css(self.CSS)
        page.send()


class Summary:
    """
    Base class for PDQ summary documents (cancer and drug information)
    """

    PP = Control.PP
    PROXY = "/cgi-bin/cdr/proxy.py"
    TIER_SUFFIXES = dict(DEV="-blue-dev", PROD="")
    IMAGE_PATH = "/images/cdr/live"
    URL_PATHS = (
        "/Summary/SummaryMetaData/SummaryURL/@cdr:xref",
        "/DrugInformationSummary/DrugInfoMetaData/URL/@cdr:xref"
    )

    def __init__(self, control, doc):
        self.start = datetime.datetime.now()
        self.control = control
        self.url = control.url
        self.doc = doc
        if control.debug_level >= 2:
            doc.session.logger.setLevel("DEBUG")
        self.urls = self.load_urls()
        self.client = DrupalClient(doc.session)
        suffix = self.TIER_SUFFIXES.get(doc.session.tier.name, "-qa")
        self.image_host = "www{}.cancer.gov".format(suffix)
        url = "{}/user/login?_format=json".format(self.url)
        name, password = self.client.auth
        data = {"name": name, "pass": password}
        response = requests.post(url, json=data)
        self.cookies = response.cookies
        opts = dict(parms=dict(DateFirstPub=""))
        result = doc.filter(self.VENDOR_FILTERS, **opts)
        root = result.result_tree
        xsl = Doc.load_single_filter(doc.session, self.CMS_FILTER)
        values = self.ASSEMBLE(doc.session, doc.id, xsl, root)
        if control.debug_level >= 1:
            doc.session.logger.setLevel("DEBUG")
        self.page = self.generate_preview(values)

    def generate_preview(self, values):
        parser = etree.HTMLParser()
        values["cdr_id"] = -values["cdr_id"]
        nid = None
        try:
            espanol = ""
            if values.get("language") == "es":
                espanol = "/espanol"
                #values["short_title"] = "Excelente!"
                if False:
                    values["language"] = "en"
                    nid = self.client.push(values)
                    values["nid"] = nid
                    values["language"] = "es"
            #values["title"] = "muy bien"
            nid = self.client.push(values)
            url = "{}{}/node/{}".format(self.url, espanol, nid)
            response = requests.get(url, cookies=self.cookies)
            page = etree.fromstring(response.content, parser=parser)
            self.postprocess(page)
            return page
        except Exception as e:
            bail("Failure generating preview: {}".format(e))
        finally:
            if nid is not None:
                self.client.remove(values["cdr_id"])

    def postprocess(self, page):
        for script in page.iter("script"):
            if script.text is None:
                script.text = " "
            url = script.get("src")
            if url is not None and not url.startswith("https:"):
                if not url.startswith("http"):
                    url = "{}{}".format(self.url, url)
                src = "{}?url={}".format(self.PROXY, url)
                script.set("src", src)
        for link in page.findall("head/link"):
            url = link.get("href")
            if url is not None and not url.startswith("https://"):
                if not url.startswith("http"):
                    url = "{}{}".format(self.url, url)
                href = "{}?url={}".format(self.PROXY, url)
                link.set("href", href)
        replacement = "https://{}{}".format(self.image_host, self.IMAGE_PATH)
        for img in page.iter("img"):
            src = img.get("src")
            if src.startswith(self.IMAGE_PATH):
                src = src.replace(self.IMAGE_PATH, replacement)
                img.set("src", src)
        for a in page.xpath("//a[@href]"):
            if "nav-item-xxtitle" in (a.getparent().get("class") or ""):
                continue
            link_type = "unknown"
            fixed = href = (a.get("href") or "").strip()
            if "Common/PopUps" in href:
                continue
            self.doc.session.logger.debug("@href=%r", href)
            if href.startswith("http"):
                link_type = "ExternalLink"
            elif href.startswith("#cit"):
                link_type = "CitationLink"
            else:
                doc_id = self.extract_id_from_url(href)
                if href.startswith("#"): # and doc_id == self.doc.id:
                    link_type = "SummaryFragRef-internal-frag"
                elif href.startswith("/"):
                    if doc_id:
                        if "#" in href:
                            frag = href.split("#")[1]
                            if doc_id == self.doc.id:
                                fixed = "#" + frag
                                link_type = "SummaryFragRef-internal+uri"
                            else:
                                fixed = f"{self.PP}?DocId={doc_id:d}#{frag}"
                                link_type = "SummaryFragRef-external"
                        else:
                            fixed = f"{self.PP}?DocId={doc_id:d}"
                            link_type = "SummaryRef-external"
                    else:
                        fixed = f"{self.url}{href}"
                        # fixed = f"{self.PROXY}?url={fixed}"
                        link_type = "Cancer.gov-link"
                else:
                    link_type = "Dead-link"
                    self.doc.session.logger.info("glossary popup %r", href)
                    # a.set("onclick", "return false")
            a.set("href", fixed)
            a.set("ohref", href)
            a.set("type", link_type)

    def load_urls(self):
        urls = dict()
        session = self.doc.session
        for path in self.URL_PATHS:
            query = Query("query_term q", "q.doc_id", "q.value")
            query.join("active_doc a", "a.id = q.doc_id")
            query.where(query.Condition("q.path", path))
            for doc_id, url in query.execute(session.cursor).fetchall():
                url = url.replace("https://www.cancer.gov", "")
                url = url.replace("http://www.cancer.gov", "")
                urls[url.lower().strip()] = doc_id
        session.logger.info("loaded %d urls", len(urls))
        return urls

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

    def send(self):
        elapsed = (datetime.datetime.now() - self.start).total_seconds()
        page = html.tostring(self.page)
        args = len(page), elapsed
        message = "Assembled %d bytes in %f seconds"
        self.doc.session.logger.info(message, *args)
        print("Content-type: text/html; charset=utf-8")
        print("")
        print(page)


class CIS(Summary):
    VENDOR_FILTERS = "set:Vendor Summary Set"
    CMS_FILTER = "Cancer Information Summary for Drupal CMS"
    ASSEMBLE = cdrpub.Control.assemble_values_for_cis


class DIS(Summary):
    VENDOR_FILTERS = "set:Vendor DrugInfoSummary Set"
    CMS_FILTER = "Drug Information Summary for Drupal CMS"
    ASSEMBLE = cdrpub.Control.assemble_values_for_dis


Control().run()
