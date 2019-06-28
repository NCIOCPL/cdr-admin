"""
Transform a CDR document using an XSL/T filter and send it back to
the browser.
"""

import cgi
import datetime
import re
import sys

from lxml import etree
import lxml.html
import requests

import cdr
import cdrcgi
import cdr2gk
from cdrapi.settings import Tier
from cdrapi import db
from cdrapi.docs import Doc
from cdrapi.users import Session
from cdrapi.publishing import DrupalClient
import cdrpub

# TODO: Get Acquia to fix their broken certificates.
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

TIER = Tier()

class Summary:
    """
    Base class for PDQ summary documents (cancer and drug information)
    """

    SCRIPT = "PublishPreviewNew.py"
    PROXY = "/cgi-bin/cdr/proxy.py"
    TIER_SUFFIXES = dict(DEV="-blue-dev", PROD="")
    IMAGE_PATH = "/images/cdr/live"
    URL_PATHS = (
        "/Summary/SummaryMetaData/SummaryURL/@cdr:xref",
        "/DrugInformationSummary/DrugInfoMetaData/URL/@cdr:xref"
    )

    def __init__(self, doc, debug=False):
        self.client = DrupalClient(doc.session)
        self.start = datetime.datetime.now()
        self.url = self.client.base
        self.doc = doc
        self.urls = self.load_urls()
        suffix = self.TIER_SUFFIXES.get(doc.session.tier.name, "-qa")
        self.image_host = "www{}.cancer.gov".format(suffix)
        url = "{}/user/login?_format=json".format(self.url)
        name, password = self.client.auth
        data = {"name": name, "pass": password}
        response = requests.post(url, json=data, verify=False)
        self.cookies = response.cookies
        opts = dict(parms=dict(DateFirstPub="", isPP="Y"))
        result = doc.filter(self.VENDOR_FILTERS, **opts)
        root = result.result_tree
        xsl = Doc.load_single_filter(doc.session, self.CMS_FILTER)
        values = self.ASSEMBLE(doc.session, doc.id, xsl, root)
        if debug:
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
                if False:
                    values["language"] = "en"
                    nid = self.client.push(values)
                    values["nid"] = nid
                    values["language"] = "es"
            nid = self.client.push(values)
            url = "{}{}/node/{}".format(self.url, espanol, nid)
            response = requests.get(url, cookies=self.cookies, verify=False)
            page = etree.fromstring(response.content, parser=parser)
            self.postprocess(page)
            return page
        except Exception as e:
            cdrcgi.bail("Failure generating preview: {}".format(e))
        finally:
            if nid is not None:
                self.client.remove(values["cdr_id"])

    def postprocess(self, page):
        for script in page.iter("script"):
            if script.text is None:
                script.text = u" "
            url = script.get("src")
            if url is not None and not url.startswith(u"https:"):
                if not url.startswith(u"http"):
                    url = u"{}{}".format(self.url, url)
                src = u"{}?url={}".format(self.PROXY, url)
                script.set(u"src", src)
        for link in page.findall("head/link"):
            url = link.get("href")
            if url is not None and not url.startswith("https://"):
                if not url.startswith(u"http"):
                    url = u"{}{}".format(self.url, url)
                href = u"{}?url={}".format(self.PROXY, url)
                link.set("href", href)
        replacement = "https://{}{}".format(self.image_host, self.IMAGE_PATH)
        for img in page.iter("img"):
            src = img.get("src")
            if src.startswith(self.IMAGE_PATH):
                src = src.replace(self.IMAGE_PATH, replacement)
                img.set("src", src)
            elif not src.startswith("http"):
                img.set("src", u"{}{}".format(self.url, src))
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
                                args = self.SCRIPT, cdrcgi.DOCID, doc_id, frag
                                fixed = "{}?{}={:d}#{}".format(*args)
                                link_type = "SummaryFragRef-external"
                        else:
                            args = self.SCRIPT, cdrcgi.DOCID, doc_id
                            fixed = "{}?{}={:d}".format(*args)
                            link_type = "SummaryRef-external"
                    else:
                        fixed = "{}{}".format(self.url, href)
                        # fixed = u"{}?url={}".format(self.PROXY, fixed)
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
            query = db.Query("query_term q", "q.doc_id", "q.value")
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
        page = lxml.html.tostring(self.page)
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

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
title   = "CDR Publish Preview"
fields  = cgi.FieldStorage() or None

if not fields:
    session    = 'guest'
    docId      = len(sys.argv) > 1 and sys.argv[1] or None
    docVersion = len(sys.argv) > 2 and sys.argv[2] or None
    preserveLnk= len(sys.argv) > 3 and sys.argv[3] or 'No'
    dbgLog     = len(sys.argv) > 4 and sys.argv[4] or None
    flavor     = len(sys.argv) > 5 and sys.argv[5] or None
    cgHost     = len(sys.argv) > 6 and sys.argv[6] or None
    cachedHtml = len(sys.argv) > 7 and sys.argv[7] or None
    monitor    = True

    if not docId:
       print 'Command line options'
       print 'PublishPreview.py docId docVersion preserveLink(Y/N) debugLog(T/F) flavor cgHost filename'
       sys.exit(1)
else:
    session    = cdrcgi.getSession(fields)   or cdrcgi.bail("Not logged in")
    docId      = fields.getvalue(cdrcgi.DOCID) or cdrcgi.bail("No Document",
                                                           title)
    docVersion = fields.getvalue("Version")
    preserveLnk= fields.getvalue("OrigLinks") or 'No'
    flavor     = fields.getvalue("Flavor")
    dbgLog     = fields.getvalue("DebugLog")
    cgHost     = fields.getvalue("cgHost")
    cachedHtml = fields.getvalue("cached")
    monitor    = False

#----------------------------------------------------------------------
# Debugging output.
#----------------------------------------------------------------------
def showProgress(progress):
    if monitor:
        now = datetime.datetime.now()
        sys.stderr.write("[{}] {}\n".format(now, progress))
showProgress("Started...")


#----------------------------------------------------------------------
# Retrieve the CDR-ID from the SummaryURL value
#
# Get rid of this if we can, or do it like we do for publish preview
# of summary document, if this is needed for Glossary Terms.
#----------------------------------------------------------------------
def getCdrIdFromPath(url):
    # For the SQL query we need to remove the fragment from the URL
    # and remove a trailing slash (/) that was added in older versions
    # of the GK code
    # A URL could contain a single quote('), i.e. in the string
    # "Hodgkin's".  If this appears the quote has to be doubled in
    # order for the SELECT statement to run successfully.
    # ----------------------------------------------------------------
    ### print '*** ', url
    baseUrl = url.split('#')[0]
    if baseUrl:
        if baseUrl[-1] == '/':
            baseUrl = baseUrl[:-1]

        try:
            conn = db.connect()
            cursor = conn.cursor()
            cursor.execute("""\
          SELECT doc_id
            FROM query_term
            JOIN active_doc a
              ON a.id = doc_id
           WHERE (path = '/Summary/SummaryMetaData/SummaryURL/@cdr:xref'
                 OR
                 path = '/DrugInformationSummary/DrugInfoMetaData/URL/@cdr:xref'
                 )
             AND value like '%s'""" % ('%' + baseUrl.replace("'", "''")))
            row = cursor.fetchone()
        except Exception as e:
            cdrcgi.bail("Database failure: {}".format(e))
        # If the passed url is not found in the query_term table it's not a
        # PDQ document and we'll return None
        try:
            return row[0]
        except:
            return None
    # If we don't have a URL we'll return None
    else:
        return None


#----------------------------------------------------------------------
# For testing, we can skip filtering and the SOAP service.
#----------------------------------------------------------------------
if cachedHtml:
    try:
        fp = open(cachedHtml, "rb")
        cgHtml = fp.read()
        fp.close()
        showProgress("Fetched cached HTML...")
        intId = cdr.exNormalize(docId)[1]
    except:
        cdrcgi.bail("failure reading {!r}".format(cachedHtml))

#----------------------------------------------------------------------
# Map for finding the filters for a given document type.
#----------------------------------------------------------------------
filterSets = {
    'DrugInformationSummary': ['set:Vendor DrugInfoSummary Set'],
    'GlossaryTerm'          : ['set:Vendor GlossaryTerm Set'],
    'GlossaryTermName'      : ['set:Vendor GlossaryTerm Set'],
    'Person'                : ['set:Vendor GeneticsProfessional Set'],
    'Summary'               : ['set:Vendor Summary Set']
}

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
if not cachedHtml:
    try:
        conn = db.connect(user="CdrGuest")
        cursor = conn.cursor()
        showProgress("Connected to CDR database...")
    except Exception as e:
        cdrcgi.bail("Database connection failure: {}".format(e))

    #----------------------------------------------------------------------
    # Determine the document type and version.
    #----------------------------------------------------------------------
    # We are covering three situations here.
    # a) No Version parameter is given
    #    The original behavior will be performed, namely to display the
    #    latest publishable version of the document if it exists.
    # b) The Version parameter is set to 'cwd'
    #    The current working document will be displayed
    # c) The Version parameter is set and it is not 'cwd'
    #    This means that the specified version is to be displayed in the
    #    publish preview display.
    # -------------------------------------------------------------------
    try:
        intId  = Doc.extract_id(docId)

        # We need to select the document type
        # -----------------------------------
        cursor.execute("""\
            SELECT doc_type.name
              FROM doc_type
              JOIN document
                ON document.doc_type = doc_type.id
             WHERE document.id = ?""", (intId,))

        row = cursor.fetchone()
        if not row:
            cdrcgi.bail("Unable to find specified document %s" % docId)

        docType = row[0]

        # If the document is a Person document we need to ensure that
        # it is a GeneticsProf document.
        # -----------------------------------------------------------
        if docType == 'Person':
            cursor.execute("""\
                SELECT doc_id
                  FROM query_term
                 WHERE path = '/Person/ProfessionalInformation' +
                              '/GeneticsProfessionalDetails'    +
                              '/AdministrativeInformation'      +
                              '/Directory/Include'
                   AND doc_id = ?""", (intId,))
            row = cursor.fetchone()
            if not row:
                err = "%s not a GeneticsProfessional Document" % docId
                cdrcgi.bail("**** Error: %s" % err)

        # Next we need to identify the version to be displayed
        # ----------------------------------------------------
        if not docVersion:
            cursor.execute("""\
            SELECT max(doc_version.num)
              FROM doc_version
             WHERE doc_version.id = ?
               AND doc_version.publishable = 'Y' """, (intId,))

            row = cursor.fetchone()
            if not row:
                cdrcgi.bail("No publishable version for %s" % docId)
            docVer = row[0]
        elif docVersion != 'cwd':
            cursor.execute("""\
            SELECT doc_version.num
              FROM doc_version
             WHERE doc_version.id = ?
               AND doc_version.num = ? """, (intId, docVersion,))

            row = cursor.fetchone()
            if not row:
                cdrcgi.bail("Unable to find specified version %s for %s" %
                            (docVersion, docId))
            docVer = row[0]
        else:
            docVer = None

    except cdrdb.Error, info:
        cdrcgi.bail('Failure finding specified version for %s: %s' %
                    (docId, info[1][0]))
    showProgress("Fetched document version: %s..." % row[0])

    # Branch off to the new code using the Drupal CMS for summaries.
    if "Summary" in docType:
        session = Session(session)
        debug = dbgLog and True or False
        doc = Doc(session, id=docId, version=docVer)
        summary = CIS(doc, debug) if docType == "Summary" else DIS(doc, debug)
        summary.send()
        exit(0)

    # Note: The values for flavor listed here are not the only values possible.
    #       These values are the default values but XMetaL macros may pass
    #       additional values for the flavor attribute.
    #       Currently, the additional values are implemented:
    #         Protocol_Patient
    #         Summary_Patient       (unused)
    #         CTGovProtocol_Patient (unused)
    # -------------------------------------------------------------------------
    if not flavor:
        flavor = {
            "Summary":                "Summary",
            "DrugInformationSummary": "DrugInfoSummary",
            "GlossaryTerm":           "GlossaryTerm",
            "GlossaryTermName":       "GlossaryTerm",
            "Person":                 "GeneticsProfessional"
        }.get(docType)
        if not flavor:
            cdrcgi.bail("Publish preview only available for Summary, "
                        "DrugInfoSummary, Glossary and GP documents")
    showProgress("DocumentType: %s..." % docType)
    showProgress("Using flavor: %s..." % flavor)
    showProgress("Preserving links: %s..." % preserveLnk)
    if preserveLnk.lower() in ("yes", "y"):
        convert = False
    else:
        convert = True

    #----------------------------------------------------------------------
    # Filter the document.
    # Submit the parameter 'isPP' to allow simulating reports that behave
    # differently for PP and publishing, i.e. denormalization of Glossary
    # links in the Drug Info Summaries.
    #----------------------------------------------------------------------
    if docType not in filterSets:
        cdrcgi.bail("Don't have filters set up for %s documents yet" % docType)
    opts = dict(docId=docId, parm=[["isPP", "Y"]], docVer=docVer)
    doc = cdr.filterDoc(session, filterSets[docType], **opts)

    if isinstance(doc, tuple):
        doc = doc[0]
    showProgress("Document filtering complete...")
    pattern1 = re.compile("<\?xml[^?]+\?>", re.DOTALL)
    pattern2 = re.compile("<!DOCTYPE[^>]+>", re.DOTALL)
    doc = pattern1.sub("", doc)
    doc = pattern2.sub("", doc)
    showProgress("Doctype declaration stripped...")

    cdr2gk.DEBUGLEVEL = 0
    try:
        if dbgLog:
            try:
                level = int(dbgLog)
            except:
                level = 1
            cdr2gk.DEBUGLEVEL = level
            showProgress("Debug logging turned on...")
        showProgress("Submitting request to Cancer.gov...")
        resp = cdr2gk.pubPreview(doc, flavor, host=cgHost)
        cgHtml = resp.xmlResult
        showProgress("Response received from Cancer.gov...")
    except Exception as e:
        #cdrcgi.bail('Error in PubPreview:' + str(e))
        # List of previously identified Percussion errors to catch
        # --------------------------------------------------------
        errMsgs = {
                    "Unknown Error":"Unspecified Error",
                    "Validation Error":
                     "Top-level section _\d* is missing a required Title.",
                    "DTD Error":
                     "The element '\w*' has invalid child element"
                  }

        # If we identified one of the known errors display it in
        # "user friendly" format and exit
        # ----------------------------------------------------
        for errType, pattern in errMsgs.items():
            regex = re.compile(pattern)
            matches = re.search(regex, str(e))
            if matches:
                extraLines = ["{}: {}".format(errType, matches.group()),
                              'Complete Error message below:',
                              str(e)]
                cdrcgi.bail('Error in PubPreview:', extra=extraLines)

        # Nothing in our known list of error. Display default message
        # -----------------------------------------------------------
        extraLines = ['%s' % errMsgs['Unknown Error'],
                          'Complete Error message below:',
                          str(e)]
        cdrcgi.bail('Error in PubPreview:', extra=extraLines)
    showProgress("Done...")

#----------------------------------------------------------------------
# Show it.
#----------------------------------------------------------------------
showProgress("Continue with local substitutions...")

# The output from Cancer.gov is modified to add the CDR-ID to the title
# We are also adding a style to work around a IE6 bug that causes the
# document printed to be cut of on the right by shifting the entire
# document to the left
# We also need to modify the image links so that they are pulled from
# the CDR server.
# ---------------------------------------------------------------------

# cdrcgi.sendPage("%s" % resp.xmlResult)
# Include the CDR-ID of the document to the HTML title
# ----------------------------------------------------
showProgress("Replacing title element...")
pattern3 = re.compile('<title>CDR Preview', re.DOTALL)
html = pattern3.sub('<title>Publish Preview: CDR%s' % intId, cgHtml)
if not html:
    cdrcgi.bail('No HTML output to process: %s'% cgHtml)
    sys.exit(0)

# Parsing HTML document in order to manipulate links within the doc
# -----------------------------------------------------------------
myHtml = lxml.html.fromstring(html)

# Removing the hostname from the fragment links to create a local
# anchor target (Example: #Section_50).  This allows links within
# the document to work properly (SummaryFragmentRefs).
# Other links are deactivated (Glossary, Summary) so that the
# user isn't constantly bringing up an error page.
# ---------------------------------------------------------------
if convert:
    showProgress("Converting local links...")

    # Modify SummaryRef links
    # These links used to be identified by the inlinetype attribute
    # but that has changed with the NVCG update of Cancer.gov
    # -------------------------------------------------------------
    for x in myHtml.xpath('//a[@href]'):
        # The SummaryRef links don't contain an href attribute
        # because Percussion isn't able to add this to the PP
        # output.  Without the href attribute the text is not
        # displayed as an anchor (underlined).  Setting an
        # empty href to satisfy the display style
        #
        # The above changed with NVCG.
        # ----------------------------------------------------
        if not 'href' in x.attrib:
            x.set('href', '')
            iLink = x.get('objectid')

            # Fragment Link
            if iLink.find('#') > 0:
                # Fragment Ref for this doc
                if iLink.find(str(intId)) > 0:
                    #link = '#Section_%s' % iLink.split('#_')[1]
                    myId = iLink.split('#_')[1]
                    link = '#_%s' % myId
                    # If the ID doesn't exist it's a TOC ID
                    try:
                        dada = myHtml.get_element_by_id('_%s' % myId)
                    except:
                        link = '#_%s_toc' % myId
                # Fragment Ref for another doc
                else:
                    link  = '/cgi-bin/cdr/PublishPreview.py?Session=guest'
                    link += '&DocId=%s' % x.get('objectid')
            # Link to summary
            else:
                link  = '/cgi-bin/cdr/PublishPreview.py?Session=guest'
                link += '&DocId=%s' % x.get('objectid')

            x.set('href', link)

        # Those links that do contain a link need to be modified
        # to only display the ID (or NAME) target.
        # With this change the local links will work.
        # Note: The first part of the 'if' broke after the last
        #       PP update on Percussion.  The links to internal
        #       targets are now set with the if block below
        # ------------------------------------------------------
        else:
            link = x.get('href')
            cdrId = getCdrIdFromPath(link)
            ###print '     ', cdrId, link
            #print type(cdrId), cdrId, link
            #showProgress(link)
            # External links starting with http (no change)
            if link.find('http') > -1:
                x.set('href', link)
                x.set('type', 'ExternalLink')
            # Internal fragment link - citations (no change)
            elif link.find('#cit') == 0:
                x.set('href', link)
                x.set('ohref', link)
                x.set('type', 'CitationLink')
            # Internal fragment link - SummaryRefs
            elif link.find('#') == 0 and cdrId == intId:
                newLink = '#%s' % link.split('#')[1]
                x.set('href', newLink)
                x.set('ohref', link)
                x.set('type', 'SummaryFragRef-internal-frag')
            # Retrieving CDR-ID or adding server name to URL
            elif link and link[0] == '/':
                if cdrId:
                    if cdrId == intId and link.find('#') > -1:
                        newLink = '#%s' % link.split('#')[1]
                        x.set('href', newLink)
                        x.set('ohref', link)
                        x.set('type', 'SummaryFragRef-internal+url')
                    elif link.find('#') > -1:
                        ppLink  = '/cgi-bin/cdr/PublishPreview.py?Session=guest'
                        ppLink += '&DocId=%d#%s' % (cdrId, link.split('#')[1])
                        x.set('href', ppLink)
                        x.set('ohref', link)
                        x.set('type', 'SummaryFragRef-external')
                    else:
                        ppLink  = '/cgi-bin/cdr/PublishPreview.py?Session=guest'
                        ppLink += '&DocId=%d' % cdrId
                        x.set('href', ppLink)
                        x.set('ohref', link)
                        x.set('type', 'SummaryRef-external')
                else:
                # A link on the Cancer.gov website not PDQ, i.e. a
                # ProtocolRef
                    newLink = 'http://%s%s' % (TIER.hosts['CG'], link)
                    x.set('href', newLink)
                    x.set('ohref', link)
                    x.set('type', 'Cancer.gov-link')
                    #showProgress(newLink)
            # Resetting the glossary links so we don't follow
            # a dead end.
            else:
                #x.set('onclick', 'return false')
                ppLink  = '/cgi-bin/cdr/PublishPreview.py?Session=guest'
                ppLink += '&DocId=%s' % link.split('=')[1]
                x.set('href', ppLink)
                x.set('ohref', link)
                x.set('type', 'related-link')
                #showProgress('   Link disabled')

    # Redirect the audio files to the local server to ensure that
    # new (not yet published) audio files can be previewed
    # -----------------------------------------------------------
    for media in myHtml.cssselect('a.CDR_audiofile'):
        link = media.get('href')
        cdrid = re.search('\d+', link.replace('.mp3', '')).group(0)
        mediaUrl = '%s/cgi-bin/cdr/GetCdrBlob.py?id=%s' % (cdr.CBIIT_NAMES[2],
                                                           cdrid)
        media.set('href', mediaUrl)

    # Make the Glossary links dead
    # Glossary links are identified by this specific class
    # ----------------------------------------------------
    for gloss in myHtml.cssselect('a.Summary-GlossaryTermRef'):
        gloss.set('href', '')
        gloss.set('onclick', 'return false')
    for gloss in myHtml.cssselect('a.definition'):
        gloss.set('href', '')
        gloss.set('onclick', 'return false')

    #------------------------------------------------------------------
    # Inject proxy links for http://... URLs, because modern browsers
    # balk at serving up mixed content.
    # Force script tags to close explicitly; see:
    # https://mailman-mail5.webfaction.com/pipermail/lxml/2012-June/006434.html
    #------------------------------------------------------------------
    proxy = "%s/cgi-bin/cdr/proxy.py" % cdr.CBIIT_NAMES[2]
    proxy = "/cgi-bin/cdr/proxy.py"
    for script in myHtml.findall("head/script"):
        script.text = " "
        src = script.get("src")
        if src is not None and src.startswith("http://"):
            src = "%s?url=%s" % (proxy, src)
            script.set("src", src)
    for link in myHtml.findall("head/link"):
        href = link.get("href")
        if href is not None and href.startswith("http://"):
            href = href.replace("cancer.gov//", "cancer.gov/")
            href = "%s?url=%s" % (proxy, href)
            link.set("href", href)

    #------------------------------------------------------------------
    # Disable popup links: they don't work in this context.
    #------------------------------------------------------------------
    for link in myHtml.xpath("//a[starts-with(@onclick, "
                             "'javascript:popWindow')]"):
        link.set('href', '')
        link.set('onclick', 'return false')

else:
    showProgress("Preserving original links...")

# Without the include_meta_content_type parameter all meta elements
# will be dropped from the head.
# Using method = 'xml' because the document is defined as XHTML
# -----------------------------------------------------------------
html = lxml.html.tostring(myHtml.getroottree(),
                          include_meta_content_type = True,
                          encoding = 'utf-8',
                          method = 'xml')

#----------------------------------------------------------------------
# Clean up from the kludge above to force explicit </script> closing
# tags.
#----------------------------------------------------------------------
html = html.replace("> </script>", "></script>")

#----------------------------------------------------------------------
# Cancer.gov doesn't know we're running a secure web server now.
#----------------------------------------------------------------------
html = re.sub("http://cdr", "https://cdr", html)

# CBIIT doesn't allow access to www.cancer.gov which holds all the current
# CSS.  We need to pick that up from www.qa.cancer.gov instead
# Strangely, access is allowed from the DEV tier.  Can't test yet on STAGE
# since STAGE is not setup yet.
# ------------------------------------------------------------------------
if TIER.name in ('QA', 'STAGE'):
    pattern6 = re.compile('http://www.cancer.gov/')
    html = pattern6.sub('http://%s/' % TIER.hosts['CG'], html)

if not TIER.name == 'PROD':
    pattern7 = re.compile('https://cdr.cancer.gov/cgi-bin/cdr/GetCdrImage.py')
    html = pattern7.sub("%s/cgi-bin/cdr/GetCdrImage.py" % cdr.CBIIT_NAMES[2],
                        html)

# Write out the HTML file for debugging purposes
# ----------------------------------------------
if dbgLog:
    fp = open(cdr.WORK_DRIVE + ":/tmp/pp-%s.html" % docId, "wb")
    fp.write(html)
    fp.close()

cdrcgi.sendPage("%s" % html.decode('utf-8'))
