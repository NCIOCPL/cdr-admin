#----------------------------------------------------------------------
# Original interface for editing CDR filter documents.  Now used for
# viewing and comparing filters only.
#
# BZIssue::2561
# BZIssue::3716
# Rewritten July 2015 as part of a security sweep.
#----------------------------------------------------------------------
import cdr
import cdrcgi
import cgi
import difflib
import requests
import lxml.etree as etree
from cdrapi import db
from cdrapi.settings import Tier
from html import escape as html_escape

class Control(cdrcgi.Control):
    """
    Logic for displaying a CDR filter document or comparing it
    with the corresponding copy on another tier's CDR server.
    """

    LOGNAME = "filters"
    TIERS = ("PROD", "STAGE", "QA", "DEV")
    TIER = Tier().name
    VIEW = "View"
    COMPARE = "Compare"
    FILTERS = "Filters"
    REQUESTS = (VIEW, COMPARE, FILTERS, cdrcgi.Control.ADMINMENU,
                cdrcgi.Control.LOG_OUT)

    def __init__(self):
        "Collect and validate the CGI parameters for this request."
        cdrcgi.Control.__init__(self)
        self.base = None
        self.full = self.fields.getvalue("full") == "full"
        self.normalize = self.fields.getvalue("normalize") == "normalize"
        self.filter = Filter(self)
        self.other_tier = self.fields.getvalue("tier")
        if self.other_tier:
            if self.other_tier not in self.TIERS:
                cdrcgi.bail()
            elif self.other_tier == self.TIER:
                cdrcgi.bail()
            host = "cdr"
            if self.other_tier != "PROD":
                host += "-%s" % self.other_tier.lower()
            self.base = "https://%s.cancer.gov/cgi-bin/cdr" % host
        if self.request not in self.REQUESTS:
            cdrcgi.bail()
        elif self.request == self.FILTERS:
            cdrcgi.navigateTo("EditFilters.py", self.session)

    def show_form(self):
        """
        We override the base class's version of this method so we
        can fork for the version of the form which shows the document
        and the one which compares it with a version on another tier's
        server.
        """
        if self.request == self.COMPARE:
            self.compare()
        self.show()

    def show(self):
        "Show the XML for the filter on our own tier."
        banner = "View CDR Filter"
        page = self.create_page(banner, self.REQUESTS[1:])
        pre = page.B.PRE(self.filter.xml.strip().replace("\n", cdrcgi.NEWLINE))
        page.add(pre)
        page.send()

    def compare(self):
        """
        Show the differences between our version of the filter and
        the copy on another tier's CDR server.
        """
        banner = "Compare Filter With Another Tier"
        page = self.create_page(banner, self.REQUESTS)
        if not self.other_tier:
            cdrcgi.bail()
        try:
            f1 = self.fix(self.filter.xml.encode("utf-8"))
            f2 = self.fix(self.get_filter())
            if self.other_tier_lower():
                filters = (f1, f2)
                tiers = (self.TIER, self.other_tier)
            else:
                filters = (f2, f1)
                tiers = (self.other_tier, self.TIER)
            differ = difflib.Differ()
            #changes = False
            pattern = (u'<span class="%%s">%%s %s on CDR %%s server</span>\n' %
                       html_escape(self.filter.title))
            lines = [
                pattern % ("deleted", "-", tiers[0]),
                pattern % ("added", "+", tiers[1]),
                "\n"
            ]
            for line in differ.compare(*filters):
                line = html_escape(line)
                if not line.startswith(" "):
                    changes = True
                if line.startswith("-"):
                    lines.append(self.wrap_line(line, "deleted"))
                elif line.startswith("+"):
                    lines.append(self.wrap_line(line, "added"))
                elif line.startswith("?"):
                    lines.append(self.wrap_line(line, "pointer"))
                elif self.full:
                    lines.append(line)
            lines = "".join(lines).replace("\n", cdrcgi.NEWLINE)
            page.add("<pre>%s</pre>" % lines)
        except:
            self.logger.exception("filter comparison failure")
            page.add('<p class="error">Filter &ldquo;%s&rdquo; '
                     'not found on CDR %s server</p>' %
                     (html_escape(self.filter.title), self.other_tier))
        page.add_css("""\
body     { background-color: #fafafa; }
.deleted { background-color: #FAFAD2; } /* Light goldenrod yellow */
.added   { background-color: #F0E68C; } /* Khaki */
.pointer { background-color: #87CEFA; } /* Light sky blue */}""")
        page.send()

    def create_page(self, banner, buttons):
        "Common logic to build the page for viewing and for comparing."
        opts = {
            "buttons": buttons,
            "session": self.session,
            "action": self.script,
            "banner": banner,
            "subtitle": u"%s (%s)" % (self.filter.title, self.filter.cdr_id)
        }
        page = cdrcgi.Page(self.PAGE_TITLE, **opts)
        page.add_hidden_field(cdrcgi.DOCID, str(self.filter.doc_id))
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Select Stage For Filter Comparison"))
        default = self.other_tier or (cdr.isProdHost() and "DEV" or "PROD")
        for tier in self.TIERS:
            if tier != self.TIER:
                checked = tier == default
                page.add_radio("tier", tier, tier, checked=checked)
        page.add("</fieldset>")
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Comparison Options"))
        page.add_checkbox("full", "Show all lines?", "full", checked=self.full,
                          tooltip="Leave unchecked to see just the changes.")
        page.add_checkbox("normalize", "Parse documents to normalize them?",
                          "normalize", checked=self.normalize,
                          tooltip="Not usually recommended, unless the "
                          "formatting%sof one of the documents has been "
                          "seriously mangled." % cdrcgi.NEWLINE)
        page.add("</fieldset>")
        page.add_css("""\
pre {
    border: solid grey 2px; font-size: 12px; padding: 5px; margin-top: 25px;
}
@media print {
    h1, fieldset { display: none; }
    h2 { font-size: 2em; }
    pre { border: none; }
}""")
        return page

    def get_filter(self):
        """
        Get the other tier's server to give us the XML for its version
        of our filter. Fastest way is the get-filter.py script, but
        we have a fallback on screen scraping some HTML to find out
        which document ID belongs to our filter on that server if
        the more efficient script isn't available.
        """
        try:
            url = "%s/get-filter.py" % self.base
            data = { "title": self.filter.title }
            response = requests.post(url, data=data, timeout=5)
            if response.ok:
                return response.content
        except:
            pass
        filters = self.get_filters()
        doc_id = filters.get(self.filter.title.lower())
        if not doc_id:
            raise Exception("%r not found" % self.filter.title)
        url = "%s/ShowDocXml.py?DocId=%d" % (self.base, doc_id)
        response = requests.get(url, timeout=15)
        if response.ok:
            return response.content
        raise Exception(response.reason)

    def get_filters(self):
        """
        Get the other server to give us the list of all of its CDR
        filters. We only need this if the server doesn't have the
        get-filter.py script installed and working.
        """
        url = "%s/EditFilters.py?Session=guest" % self.base
        response = requests.get(url, timeout=10)
        root = cdrcgi.lxml.html.fromstring(response.content)
        table = [t for t in root.iter("table")][1]
        filters = {}
        for node in table.findall("tr"):
            cells = node.findall("td")
            if len(cells) != 2:
                continue
            try:
                cdr_id = "".join(cells[0].itertext()).strip()
            except:
                continue
            title = cells[1].text
            if cdr_id is not None and cdr_id.startswith("CDR"):
                filter_id = cdr.exNormalize(cdr_id)[1]
                filters[title.lower()] = filter_id
        return filters

    def other_tier_lower(self):
        """
        Find out if the tier with which our copy of the filter is being
        compared is "lower" than ours, where "lower" means "further from
        production." If it is we'll make our copy the "before" copy and
        the other one the "after" version. Otherwise, we'll switch them.
        """
        return self.TIERS.index(self.other_tier) > self.TIERS.index(self.TIER)

    def fix(self, me):
        "Prepare the XML for a filter document for comparison"
        if self.normalize:
            xml = etree.tostring(etree.XML(me), pretty_print=True)
        else:
            xml = me
        return xml.replace("\r", "").strip().splitlines(1)

    @staticmethod
    def wrap_line(line, line_class):
        "Add coloring to diff lines so user can tell where they came from"
        return '<span class="%s">%s</span>' % (line_class, line)

class Filter:
    "Collect document ID, title, and XML for the filter being viewed/compared"
    def __init__(self, control):
        try:
            doc_ids = cdr.exNormalize(control.fields.getvalue(cdrcgi.DOCID))
            self.cdr_id, self.doc_id, self.id_frag = doc_ids
        except:
            cdrcgi.bail()
        query = db.Query("document d", "d.title", "d.xml")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where("t.name = 'Filter'")
        query.where(query.Condition("d.id", self.doc_id))
        rows = query.execute(control.cursor).fetchall()
        if not rows:
            cdrcgi.bail()
        self.title, self.xml = rows[0]

if __name__ == "__main__":
    "Allow documentation and lint to import this without side effects"
    Control().run()
