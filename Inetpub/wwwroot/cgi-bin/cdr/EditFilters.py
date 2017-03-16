#----------------------------------------------------------------------
# Menu of existing filters.
# BZIssue::3716
#----------------------------------------------------------------------
import cdr
import cdrcgi
import cdrdb
import cgi
import urllib

class Control(cdrcgi.Control):
    COMPARE = "Compare With PROD"
    PARAMS = "Filter Params"
    BUTTONS = (PARAMS, cdrcgi.MAINMENU, cdrcgi.Control.LOG_OUT)
    def __init__(self):
        cdrcgi.Control.__init__(self, "Manage Filters")
        if not self.session:
            cdrcgi.bail("Unknown or expired CDR session")
        elif self.request == self.COMPARE:
            cdrcgi.navigateTo("FilterDiffs.py", self.session)
        elif self.request and self.request not in self.BUTTONS:
            cdrcgi.bail()
        elif self.request == self.PARAMS:
            cdrcgi.navigateTo("GetXsltParams.py", self.session)
        self.buttons = self.BUTTONS
        if not cdr.isProdHost():
            self.buttons = (self.COMPARE,) + self.BUTTONS
    def populate_form(self, form):
        try:
            query = cdrdb.Query("document d", "d.id", "d.title").order(2)
            query.join("doc_type t", "t.id = d.doc_type")
            query.where("t.name = 'Filter'")
            docs = query.execute(self.cursor).fetchall()
        except:
            cdrcgi.bail("Database temporarily unavailable")
        self.add_table(form, docs)
        self.add_table(form, sorted(docs), True)
        form.add_css("""\
#idsort td, #titlesort td { background-color: #e8e8e8; }
#idsort td a, #titlesort td a { color: black; } /* text-decoration: none; }*/
.clickable { cursor: pointer; }""")
        form.add_script("""\
function toggle(show, hide) {
    jQuery(show).show();
    jQuery(hide).hide();
}""")
    def add_table(self, form, docs, resorted=False):
        if resorted:
            form.add('<table id="idsort" class="hidden">')
            form.add(form.B.CAPTION("%d CDR Filters (Sorted By CDR ID)" %
                                    len(docs)))
            form.add("<tr>")
            form.add(form.B.TH("CDR ID"))
            form.add(form.B.TH("Filter Title", form.B.CLASS("clickable"),
                               onclick="toggle('#titlesort','#idsort');"))
        else:
            form.add('<table id="titlesort">')
            form.add(form.B.CAPTION("%d CDR Filters (Sorted By Title)" %
                                    len(docs)))
            form.add("<tr>")
            form.add(form.B.TH("CDR ID", form.B.CLASS("clickable"),
                               onclick="toggle('#idsort','#titlesort');"))
            form.add(form.B.TH("Filter Title"))
        form.add("</tr>")
        parms = {
            cdrcgi.SESSION: self.session,
            cdrcgi.REQUEST: "View",
            "full": "full"
        }
        for doc_id, title in docs:
            parms[cdrcgi.DOCID] = cdr_id = cdr.normalize(doc_id)
            url = "EditFilter.py?%s" % urllib.urlencode(parms)
            form.add("<tr>")
            form.add(form.B.TD(form.B.A(cdr_id, href=url)))
            form.add(form.B.TD(title))
            form.add("</tr>")
Control().run()
