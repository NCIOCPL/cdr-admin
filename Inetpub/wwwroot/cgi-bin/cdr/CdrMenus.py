#!/usr/bin/env python

"""Show CDR Admin menu hierarchy.
"""

import cdr
import re
import requests
import urllib.parse
import lxml.html as html
import lxml.html.builder as B
from cdrcgi import Controller


class Control(Controller):
    """Program logic."""

    SUBTITLE = "CDR Admin Menu Hierarchy"
    LOGNAME = "CdrMenus"
    USER = "menuwalker"
    PASSWORD = cdr.getpw("menuwalker")
    SESSION = str(cdr.login(USER, PASSWORD))

    def run(self):
        """Override the base class version: no menu and no tables."""

        if not self.request:
            try:
                self.show_report()
            except Exception as e:
                self.logger.exception("Report failed")
                self.bail(e)
        else:
            Controller.run(self)

    def show_report(self):
        """Override, because this is not a tabular report."""

        menus = self.menus
        title = f"Total Menu Items {Item.total} ({len(Item.unique)} unique)"
        self.report.page.form.append(B.H3(title))
        self.report.page.form.append(menus)
        self.report.page.add_css("h3 { color: black; }")
        self.report.send()

    @property
    def menus(self):
        """Hierarchical ordered list for the menu structure."""

        if not hasattr(self, "_menus"):
            self._menus = B.OL()
            for item in self.top:
                self._menus.append(item.menu)
        return self._menus

    @property
    def no_results(self):
        """Suppress the message we'd get with no tables."""
        return None

    @property
    def top(self):
        """Menu items on the parent-less main admin menu."""

        if not hasattr(self, "_top"):
            self._top = (
                Item(self, "Board Managers", "BoardManagers.py"),
                Item(self, "CIAT/CIPS Staff", "CiatCipsStaff.py"),
                Item(self, "Developers/System Administrators", "DevSA.py"),
                Item(self, "Guest", "GuestUsers.py"),
            )
        return self._top


class Item:
    """One item in the CDR Admin menu hierarchy."""

    total = 0
    unique = set()
    childless = set()
    non_leaves = set([
        "advancedsearch.py",
        "boardmanagers.py",
        "cdrdocumentation.py",
        "ciatcipsstaff.py",
        "citationreports.py",
        "devsa.py",
        "druginforeports.py",
        "generalreports.py",
        "geographicreports.py",
        "globalchangemenu.py",
        "glossarytermreports.py",
        "guestusers.py",
        "mailerreports.py",
        "mailers.py",
        "mediareports.py",
        "personandorgreports.py",
        "publishreports.py",
        "reports.py",
        "summaryandmiscreports.py",
        "terminologyreports.py",
    ])
    leaves = set([
        "../scheduler",
        "activelogins.py",
        "activityreport.py",
        "boardinvitationhistory.py",
        "boardmeetingdates.py",
        "boardmembermailerreqform.py",
        "boardroster.py",
        "boardrosterfull.py",
        "cdrmenus.py",
        "cdrfilter.html",
        "cdrfilter.py",
        "changestosummaries.py",
        "checkedoutdocs.py",
        "checkurls.py",
        "citationsaddedtoprotocols.py",
        "citationsinsummaries.py",
        "citesearch.py",
        "clear-filesweeper-lockfile.py",
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
        "drugdatelastmodified.py",
        "drugdescriptionreport.py",
        "drugindicationsreport.py",
        "drugreviewreport.py",
        "edit-value-table.py",
        "editactions.py",
        "editconfig.py",
        "editcontrolvalues.py",
        "editdoctypes.py",
        "editexternalmap.py",
        "editfilters.py",
        "editfiltersets.py",
        "editgroups.py",
        "editlinkcontrol.py",
        "editquerytermdefs.py",
        "editusers.py",
        "externmapfailures.py",
        "failbatchjob.py",
        "fetch-tier-settings.py",
        "ftpaudio.py",
        "gatekeeperstatus.py",
        "geneticconditionmenumappingreport.py",
        "geneticsprofuploadfiles.py",
        "getbatchstatus.py",
        "getbatchstatus.py",
        "getschema.py",
        "globalchangelink.py",
        "glossary-servers.py",
        "glossary-translation-job-report.py",
        "glossary-translation-jobs.py",
        "glossaryconceptdocsmodified.py",
        "glossaryconceptfull.py",
        "glossarynamedocsmodified.py",
        "glossaryprocessingstatusreport.py",
        "glossarytermaudioreview.py",
        "glossarytermaudioreviewreport.py",
        "glossarytermconceptsearch.py",
        "glossarytermlinks.py",
        "glossarytermnamesearch.py",
        "glossarytermphrases.py",
        "glossarytermsearch.py",
        "gpmailerreqform.py",
        "gppubnotification.py",
        "help.py",
        "helpsearch.py",
        "inactivepersonsorgs.py",
        "inactivityreport.py",
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
        "media-translation-job-report.py",
        "media-translation-jobs.py",
        "mediacaptioncontent.py",
        "medialinks.py",
        "medialists.py",
        "mediasearch.py",
        "mediatrackingreport.py",
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
        "post-schema.py",
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
        "setnextjobid.py",
        "showcdrdocument.py",
        "showglobalchangetestresults.py",
        "showsummaryincludes.py",
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
        "summaryprotocolreflinks.py",
        "summarysearch.py",
        "summarysectioncleanup.py",
        "summarystandardwording.py",
        "summarytypechangereport.py",
        "termhierarchytree.py",
        "termncitdiseaseupdateall.py",
        "termncitdrugupdateall.py",
        "termsearch.py",
        "termusage.py",
        "translation-job-report.py",
        "translation-jobs.py",
        "unblockdoc.py",
        "unchangeddocs.py",
        "unverifiedcitations.py",
        "updatepremedlinecitations.py",
        "upload-zip-code-file.py",
        "urllistreport.py",
        "warehouseboxnumberreport.py",
        "xmetal-icons.py",
    ])

    def __init__(self, control, label, url):
        """Save the caller's values, bump up the count, and cache the item.

        Pass:
            control - access to logging
            label - string for the menu item's display identification
            url - how the menu item is invoked
        """

        self.__control = control
        self.__label = label
        self.__url = url
        Item.total += 1
        Item.unique.add(url.lower())

    @property
    def control(self):
        """Access to the logger, and for passing to child constructors."""
        return self.__control

    @property
    def is_leaf(self):
        """Boolean: True if we don't need to recurse further."""

        if not hasattr(self, "_is_leaf"):
            self._is_leaf = False
            lower = self.script.lower()
            if lower in self.leaves:
                self._is_leaf = True
            elif lower in self.non_leaves:
                self._is_leaf = False
            else:
                for name in ("request", "ocecdr-"):
                    if re.match(rf"^{name}\d+\.py$", lower):
                        self._is_leaf = True
                        break
                if not self._is_leaf:
                    self.logger.info("is %s a new leaf?", self.url)
        return self._is_leaf

    @property
    def label(self):
        """String for the menu item's display identification."""
        return self.__label

    @property
    def logger(self):
        """For logging our menu spelunking."""
        return self.control.logger

    @property
    def menu(self):
        """HTML list item, possibly with a nested list for children."""

        if not hasattr(self, "_menu"):
            parms = dict(self.parms)
            if "Session" in parms:
                del parms["Session"]
            parms = self.join_parms(parms)
            script = self.script
            if parms:
                script += f"?{parms}"
                if "??" in script:
                    args = script, self.script
                    self.logger.warning("script=%s self.script=%s", *args)
                    self.logger.warning("self.parms=%s", self.parms)
            label = B.SPAN(f"{self.label} - ", B.CLASS("label"))
            script_span = B.SPAN(script, B.CLASS("script"))
            self._menu = B.LI(label, script_span)
            if not self.is_leaf:
                if self.items:
                    ol = B.OL()
                    for item in self.items:
                        ol.append(item.menu)
                    self._menu.append(ol)
                else:
                    Item.childless.add(script)
                    Item.leaves.add(self.script)
        return self._menu

    @property
    def parms(self):
        """Dictionary of the URL's parameter values."""

        if not hasattr(self, "_parms"):
            self._parms = urllib.parse.parse_qs(self.parsed.query)
        return self._parms

    @property
    def parsed(self):
        """The articulated components of the URL."""

        if not hasattr(self, "_parsed"):
            self._parsed = urllib.parse.urlparse(self.url)
        return self._parsed

    @property
    def script(self):
        """File name of the script which generates the page."""

        if not hasattr(self, "_script"):
            self._script = self.parsed.path.split("/")[-1] or self.parsed.path
            if self._script.endswith("/scheduler/"):
                self._script = "../scheduler"
        return self._script

    @property
    def url(self):
        """How the menu item is invoked."""
        return self.__url

    @property
    def items(self):
        """Children of this item, if it is itself a menu."""

        if not hasattr(self, "_items"):
            host = self.control.session.tier.hosts["APPC"]
            query = { "Session": self.control.SESSION }
            for k in self.parms:
                val = self.parms[k]
                if val:
                    if not isinstance(val, str):
                        val = val[0]
                    if val:
                        query[k] = val
            query = self.join_parms(query)
            url = f"https://{host}/cgi-bin/cdr/{self.script}?{query}"
            if self.parsed.fragment:
                url += f"#{self.parsed.fragment}"
            if "??" in url:
                self.logger.warning("self.parms=%s url=%s", self.parms, url)
            items = []
            try:
                doc = requests.get(url, timeout=5).content
                root = html.fromstring(doc)
                for ol in root.iter("ol", "ul"):
                    for a in ol.findall("li/a"):
                        items.append(Item(self.control, a.text, a.get("href")))
            except Exception as e:
                pass
            self._items = items
        return self._items

    @staticmethod
    def join_parms(query):
        """Serialize the query parameters for invoking the url."""

        parms = []
        for name in query:
            value = query[name]
            if not isinstance(value, str):
                value = value[0]
            parms.append(f"{name}={value}")
        return "&".join(parms)


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
