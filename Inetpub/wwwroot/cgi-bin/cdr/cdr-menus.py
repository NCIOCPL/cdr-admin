#----------------------------------------------------------------------
# Show CDR Admin menu hierarchy.
#----------------------------------------------------------------------
import cdr
import re
import urllib
import requests
import urlparse
import lxml.etree as etree
import lxml.html as html
import lxml.html.builder as B
import time
from cdrapi.settings import Tier

TIER = Tier()
USER = "menuwalker"
PASSWORD = cdr.getpw("menuwalker")
SESSION = str(cdr.login(USER, PASSWORD))

class Item:
    total = 0
    unique = set()
    childless = set()
    leaves = set([
        "../scheduler",
        "activelogins.py",
        "activityreport.py",
        "boardinvitationhistory.py",
        "boardmeetingdates.py",
        "boardmembermailerreqform.py",
        "boardroster.py",
        "boardrosterfull.py",
        "cdrfilter.html",
        "cdrfilter.py",
        "cdrreport.py",
        "changestosummaries.py",
        "checkedoutdocs.py",
        "checkurls.py",
        "citationsaddedtoprotocols.py",
        "citationsinsummaries.py",
        "citesearch.py",
        "countbydoctype.py",
        "countrysearch.py",
        "datedactions.py",
        "datelastmodified.py",
        "db-tables.py",
        "del-some-docs.py",
        "diseasediagnosisterms.py",
        "dislists.py",
        "dissearch.py",
        "diswithmarkup.py",
        "documentsmodified.py",
        "docversionhistory.py",
        "drugagentreport.py",
        "drugdescriptionreport.py",
        "drugindicationsreport.py",
        "drugreviewreport.py",
        "editactions.py",
        "editdoctypes.py",
        "editexternmap.py",
        "editfilters.py",
        "editfiltersets.py",
        "editgroups.py",
        "editlinkcontrol.py",
        "editquerytermdefs.py",
        "editusers.py",
        "externmapfailures.py",
        "failbatchjob.py",
        "ftpaudio.py",
        "gatekeeperstatus.py",
        "geneticconditionmenumappingreport.py",
        "geneticsprofuploadfiles.py",
        "getbatchstatus.py",
        "getbatchstatus.py",
        "globalchangelink.py",
        "glossaryconceptdocsmodified.py",
        "glossaryconceptfull.py",
        "glossarynamedocsmodified.py",
        "glossaryprocessingstatusreport.py",
        "glossarytermaudioreview.py",
        "glossarytermaudioreviewreport.py",
        "glossarytermlinks.py",
        "glossarytermphrases.py",
        "glossarytermsearch.py",
        "gpmailerreqform.py",
        "gppubnotification.py",
        "help.py",
        "helpsearch.py",
        "inactivepersonsorgs.py",
        "interventionandprocedureterms.py",
        "invaliddocs.py",
        "linkeddocs.py",
        "listgpemailers",
        "listgpemailers.py",
        "logout.py",
        "log-tail.py",
        "maileractivitystatistics.py",
        "mailercheckinreport.py",
        "mailerhistory.py",
        "manage-pdq-data-partners.py",
        "mediacaptioncontent.py",
        "medialinks.py",
        "medialists.py",
        "mediasearch.py",
        "mediatrackingreport.py",
        "menuhierarchy.py",
        "messageloggedinusers.py",
        "miscsearch.py",
        "modifiedpubmeddocs.py",
        "modwithoutpubversion.py",
        "newcitations.py",
        "newdocreport.py",
        "newdocswithpubstatus.py",
        "newlypublishabletrials.py",
        "newlypublishedtrials2.py",
        "orgprotocolreview.py",
        "orgsearch2.py",
        "ospreport.py",
        "pdqboards.py",
        "personlocsearch.py",
        "personprotocolreview.py",
        "personsatorg.py",
        "personsearch.py",
        "politicalsubunitsearch.py",
        "post-translated-summary.py",
        "preferredprotorgs.py",
        "pronunciationbywordstem.py",
        "pronunciationrecordings.py",
        "protocolslinkedtoterms.py",
        "protownershiptransfer.py",
        "protownershiptransferorg.py",
        "protsearch.py",
        "publishing.py",
        "pubstatsbydate.py",
        "pubstatus.py",
        "qcreport.py",
        "recentctgovprotocols.py",
        "recordingtrackingreport.py",
        "replacecwdwithversion.py",
        "replacecwdwithversion.py",
        "replacecwdreport.py",
        "replacedocwithnewdoc.py",
        "republish.py",
        "reverifyjob.py",
        "runicrdbstatreport.py",
        "runpcibstatreport.py",
        "semantictypereport.py",
        "showglobalchangetestresults.py",
        "stub.py",
        "summarieslists.py",
        "summariestocreport.py",
        "summarieswithmarkup.py",
        "summarieswithnonjournalarticlecitations.py",
        "summarieswithprotocollinks.py",
        "summarychanges.py",
        "summarycitations.py",
        "summarycomments.py",
        "summarycrd.py",
        "summarydatelastmodified.py",
        "summarymailerreport.py",
        "summarymailerreqform.py",
        "summarymetadata.py",
        "summarysearch.py",
        "summarysectioncleanup.py",
        "summarytypechangereport.py",
        "termhierarchytree.py",
        "termncitdiseaseupdateall.py",
        "termncitdrugupdateall.py",
        "termsearch.py",
        "termusage.py",
        "unblockdoc.py",
        "unchangeddocs.py",
        "unverifiedcitations.py",
        "updatepremedlinecitations.py",
        "upload-zip-code-file.py",
        "warehouseboxnumberreport.py",
        #"globalchangemenu.py",
    ])
    def __init__(self, label, url):
        self.label = label
        self.url = url
        self.parsed = urlparse.urlparse(url)
        self.script = self.parsed.path.split("/")[-1] or self.parsed.path
        if self.script.endswith("/scheduler/"):
            self.script = "../scheduler"
        self.parms = urlparse.parse_qs(self.parsed.query)
        Item.total += 1
        Item.unique.add(url.lower())
    def is_leaf(self):
        lower = self.script.lower()
        if lower in self.leaves:
            return True
        for name in ("request", "ocecdr-"):
            if re.match(r"^%s\d+\.py$" % name, lower):
                return True
        return self.script.lower().startswith("ocecdr-")
    @staticmethod
    def join_parms(query):
        parms = []
        for name in query:
            value = query[name]
            if not isinstance(value, basestring):
                value = value[0]
            parms.append("%s=%s" % (name, value))
        return "&".join(parms)
    def menu(self):
        parms = dict(self.parms)
        if "Session" in parms:
            del parms["Session"]
        parms = self.join_parms(parms)
        script = self.script
        if parms:
            script += "?%s" % parms
        label = B.SPAN("%s - " % self.label, B.CLASS("label"))
        script_span = B.SPAN(script, B.CLASS("script"))
        li = B.LI(label, script_span)
        if not self.is_leaf():
            items = self.get_items()
            if items:
                ol = B.OL()
                for item in items:
                    ol.append(item.menu())
                    #ol.append(B.LI("%s (%s)" % (item.label, item.script)))
                li.append(ol)
            else:
                Item.childless.add(script)
                Item.leaves.add(self.script)
        return li
    def get_items(self):
        host = TIER.hosts["APPC"]
        query = { "Session": SESSION }
        for k in self.parms:
            val = self.parms[k]
            if val:
                if not isinstance(val, basestring):
                    val = val[0]
                if val:
                    query[k] = val
        query = self.join_parms(query)
        url = "https://%s/cgi-bin/cdr/%s?%s" % (host, self.script, query)
        if self.parsed.fragment:
            url += "#%s" % self.parsed.fragment
        items = []
        try:
            doc = requests.get(url, timeout=5).content
            root = html.fromstring(doc)
            for ol in root.iter("ol", "ul"):
                for a in ol.findall("li/a"):
                    items.append(Item(a.text, a.get("href")))
        except Exception, e:
            pass
        return items

TOP = (
    Item("Board Managers", "BoardManagers.py"),
    Item("CIAT/CIPS Staff", "CiatCipsStaff.py"),
    Item("Developers/System Administrators", "DevSA.py"),
    Item("Guest", "GuestUsers.py")
)
CSS = """\
* { font-family: Arial, sans-serif; }
h1 { font-size: 18pt; }
h2 { font-size: 14pt; }
span.label { font-weight: bold; }
span.script { font-style: italic; }
footer p { font-size: 8pt; color: green; font-style: italic; }"""
ol = B.OL()
start = time.time()
for item in TOP:
    ol.append(item.menu())
elapsed = time.time() - start
page = B.HTML(
    B.HEAD(
        B.META(charset="utf-8"),
        B.TITLE("CDR Menu Hierarchy"),
        B.STYLE(CSS)
    ),
    B.BODY(
        B.H1("CDR Menu Hierarchy"),
        B.H2("Total Menu Items: %d (%d Unique)" % (Item.total,
                                                   len(Item.unique))),
        ol,
        B.E("footer", (B.P("Elapsed time: %.3f seconds" % elapsed))),
        etree.Comment("\n".join(list(Item.childless)))
    )
)
print "Content-type: text/html\n"
print etree.tostring(page, method="html", doctype="<!DOCTYPE html>",
                     pretty_print=True, encoding="utf-8")
