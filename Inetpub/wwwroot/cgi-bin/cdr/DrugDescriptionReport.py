#----------------------------------------------------------------------
# Report to display DrugInfoSummaries
#
# BZIssue::5264 - [DIS] Formatting Changes to Drug Description Report
# Rewritten July 2015 as part of security sweep.
# JIRA::OCECDR-4453 - Add options to view all single-agent drugs or all combos
#----------------------------------------------------------------------
import cdr
import cdrcgi
import cdrdb
import cgi
import datetime
import json
import lxml.etree as etree

class Control(cdrcgi.Control):
    """
    If the user has asked for a report:
        collect the report options from the individual CGI parameters
        and show the report.
    Otherwise, if the user asked to refine an existing request:
        unpack the remembered options and show the form again with them.
    Otherwise, put up the request form with the default choices.
    """

    METADATA = "/DrugInformationSummary/DrugInfoMetaData"
    COMBO = METADATA + "/DrugInfoType/@Combination"
    REFTYPES = ("NCI", "FDA", "NLM")
    METHODS = (
        ("By Drug Name", "name"),
        ("By Date of Last Publishable Version", "date"),
        ("By Drug Reference Type", "type")
    )
    def __init__(self):
        cdrcgi.Control.__init__(self, "Drug Description Report")
        if not self.session:
            cdrcgi.bail("Not logged in")
        self.drugs = self.load_drugs()
        vals = self.fields.getvalue("vals")
        if vals:
            self.unpack_vals(vals)
        else:
            self.method = self.fields.getvalue("method")
            self.start = self.fields.getvalue("start")
            self.end = self.fields.getvalue("end")
            self.selected_drugs = self.fields.getlist("drugs")
            self.reftype = self.fields.getvalue("reftype")
        self.validate_parms()

    def populate_form(self, form):
        "Add the fields for a DIS report request to the page's form."
        drugs = [
            ("all-drugs", "All Drugs"),
            ("all-single-agent-drugs", "All Single-Agent Drugs"),
            ("all-drug-combinations", "All Drug Combinations")
        ]
        for drug in self.drugs:
            title = drug.name or "[Unnamed Drug CDR%d]" % drug.id
            drugs.append((str(drug.id), title))
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Filter Method"))
        for label, value in self.METHODS:
            checked = self.method == value
            form.add_radio("method", label, value, checked=checked)
        drug_help = "Control-click to select multiple\nShift-click for range."
        form.add("</fieldset>")
        class_string = self.method != "name" and ' class="hidden"' or ""
        form.add('<fieldset id="name-block"%s>' % class_string)
        form.add(form.B.LEGEND("Select Drugs For Report"))
        form.add_select("drugs", "Drug(s)", drugs, multiple=True,
                        default=self.selected_drugs, tooltip=drug_help)
        form.add("</fieldset>")
        class_string = self.method != "date" and ' class="hidden"' or ""
        form.add('<fieldset id="date-block"%s>' % class_string)
        form.add(form.B.LEGEND("Date Range of Last Published Version"))
        form.add_date_field("start", "Start Date", value=self.start)
        form.add_date_field("end", "End Date", value=self.end)
        form.add("</fieldset>")
        class_string = self.method != "type" and ' class="hidden"' or ""
        form.add('<fieldset id="type-block"%s>' % class_string)
        form.add(form.B.LEGEND("Select Drug Reference Type"))
        form.add_radio("reftype", "NCI", "NCI", checked=True)
        form.add_radio("reftype", "FDA", "FDA")
        form.add_radio("reftype", "NLM", "NLM")
        form.add("</fieldset>")
        form.add_css("#drugs { height: 175px; }")
        self.add_script(form)

    def show_report(self):
        """
        Assemble a report with one table per drug information summary.
        There are some string interpolations used here, partly because
        of a bug in ADO/DB which doesn't allow placeholders in subqueries.
        These are safe in this case because of the parameter validations
        performed above.
        """
        query = cdrdb.Query("doc_version v", "v.id", "MAX(v.num)")
        query.group("v.id")
        criteria = ""
        if self.method == "name":
            if "all-drugs" in self.selected_drugs:
                query.join("doc_type t", "t.id = v.doc_type")
                query.join("document d", "d.id = v.id")
                query.where("t.name = 'DrugInformationSummary'")
            elif "all-drug-combinations" in self.selected_drugs:
                criteria = " for drug combinations"
                query.join("query_term c", "c.doc_id = v.id")
                query.where("c.path = '%s'" % self.COMBO)
                query.where("c.value = 'Yes'")
            elif "all-single-agent-drugs" in self.selected_drugs:
                criteria = " for single-agent drugs"
                query.join("doc_type t", "t.id = v.doc_type")
                query.join("document d", "d.id = v.id")
                query.where("t.name = 'DrugInformationSummary'")
                #query.where("d.active_status = 'A'")
                subquery = cdrdb.Query("query_term", "doc_id")
                subquery.where("path = '%s'" % self.COMBO)
                subquery.where("value = 'Yes'")
                query.where(query.Condition("v.id", subquery, "NOT IN"))
            else:
                selected = [int(d) for d in self.selected_drugs]
                query.where(query.Condition("v.id", selected, "IN"))
                criteria = " by name"
        elif self.method == "type":
            path = "/DrugInformationSummary/DrugReference/DrugReferenceType"
            subquery = cdrdb.Query("query_term", "doc_id")
            subquery.where("path = '%s'" % path)
            subquery.where("value = '%s'" % self.reftype)
            query.where(query.Condition("v.id", subquery, "IN"))
            criteria = " with reference type %s" % self.reftype
        elif self.method == "date":
            # Different approach for date range.
            start = self.start
            end = "%s 23:59:59" % self.end
            subquery = cdrdb.Query("publishable_version p",
                                   "p.id", "MAX(p.num) AS num")
            subquery.join("doc_type t", "t.id = p.doc_type")
            subquery.join("document d", "d.id = p.id")
            subquery.where("t.name = 'DrugInformationSummary'")
            subquery.group("p.id")
            subquery.alias("lastp")
            query = cdrdb.Query("doc_version v", "v.id", "v.num")
            query.join(subquery, "lastp.id = v.id", "lastp.num = v.num")
            query.where("v.dt BETWEEN '%s' AND '%s'" % (start, end))
            criteria = (" with last publishable versions "
                        "created %s--%s (inclusive)" % (self.start, self.end))
        else:
            cdrcgi.bail("Internal error") # can't happen, given validation above
        try:
            rows = query.execute(self.cursor, timeout=300).fetchall()
        except Exception, e:
            raise Exception("Database failure: %s" % e)
        summaries = [DrugInfoSummary(self, *row) for row in rows]
        self.buttons[0] = "Back"
        opts = {
            "buttons": self.buttons,
            "action": self.script,
            "subtitle": self.title,
            "session": self.session
        }
        now = str(datetime.datetime.now())[:cdrcgi.DATETIMELEN]
        count = "%d documents found%s" % (len(summaries), criteria)
        page = cdrcgi.Page(self.PAGE_TITLE, **opts)
        page.add(page.B.H2(self.title, page.B.BR(),
                           page.B.SPAN(now, page.B.CLASS("report-date")),
                           page.B.BR(),
                           page.B.SPAN(count, page.B.CLASS("report-count")),
                           page.B.CLASS("center")))
        page.add_hidden_field("vals", self.pack_vals())
        for summary in sorted(summaries):
            summary.show(page)
        self.add_css(page)
        page.send()

    def load_drugs(self):
        "Find all of the DIS docs which have at least one version."
        query = cdrdb.Query("document d", "d.id", "d.title").order(2, 1)
        query.join("doc_type t", "t.id = d.doc_type")
        query.join("doc_version v", "v.id = d.id")
        query.where("t.name = 'DrugInformationSummary'")
        query.unique()
        return [Doc(*row) for row in query.execute(self.cursor).fetchall()]

    def validate_parms(self):
        "Make sure the CGI parameter are reasonable."
        cdrcgi.BAILOUT_DEFAULT = True
        msg = cdrcgi.TAMPERING
        methods = [val for label, val in self.METHODS]
        self.method = self.method or methods[0]
        self.reftype = self.reftype or self.REFTYPES[0]
        if not self.start or not self.end:
            self.start = self.end = str(datetime.date.today())
        if self.start > self.end:
            raise Exception("Date range can't start before it ends! :-)")
        if not self.selected_drugs or "all-drugs" in self.selected_drugs:
            self.selected_drugs = ["all-drugs"]
        elif "all-single-agent-drugs" in self.selected_drugs:
            self.selected_drugs = ["all-single-agent-drugs"]
        elif "all-drug-combinations" in self.selected_drugs:
            self.selected_drugs = ["all-drug-combinations"]
        elif set(self.selected_drugs) - set([str(d.id) for d in self.drugs]):
            raise Exception(msg)
        cdrcgi.valParmVal(self.reftype, val_list=self.REFTYPES, msg=msg)
        cdrcgi.valParmVal(self.method, val_list=methods, msg=msg)
        cdrcgi.valParmDate(self.start, msg=msg)
        cdrcgi.valParmDate(self.end, msg=msg)

    def pack_vals(self):
        "Remember the user's choices so she can come back to them."
        vals = {
            "method": self.method,
            "start": self.start,
            "end": self.end,
            "drugs": self.selected_drugs,
            "reftype": self.reftype
        }
        return json.dumps(vals)

    def unpack_vals(self, packed):
        """
        The user wants to refine an existing report request. Get
        the remembered options.
        """
        try:
            vals = json.loads(packed)
            self.method = vals.get("method")
            self.start = vals.get("start")
            self.end = vals.get("end")
            self.selected_drugs = vals.get("drugs")
            self.reftype = vals.get("reftype")
        except:
            raise
            raise Exception(cdrcgi.TAMPERING)

    @staticmethod
    def add_css(page):
        "Make the report look the way the users want it to."
        page.add_css("""\
.report-date { font-size: .8em; }
.report-count { font-size: .7em; }
.dis, hr { width: 80%; margin: 10px auto; }
hr { margin: 0 auto 25px; }
.dis, .dis tr * { border: none; background: transparent; }
.dis > th { padding-right: 5px; }
.dis th, .dis td { color: black; vertical-align: top; }
.dis th { text-align: left; padding-right: 5px; }
.dis p:first-child { padding-top: 0; margin-top: 0; }
.dis table tbody { border: solid black 1px; }
.dis table, .dis table * { margin: 0; }
.dis table caption {
    padding-left: 0; text-align: left; color: black; font-size: 14px;
}
.dis table td { padding: 3px 3px 0 0; }
.dis table tr td:first-child { padding: 3px 3px 0 3px; }
.dis table tr:last-child td { padding-bottom: 3px; }
@media print {
    .dis, hr { width: 100%; }
    header { display: none; }
 }""")

    @staticmethod
    def add_script(form):
        "Make the request form behave intelligently."
        form.add_script("""\
jQuery(document).ready(function($) {
    $('#drugs option').click(function() {
        switch ($(this).val()) {
        case 'all-drugs':
            $('#drugs option').prop('selected', false);
            $('#drugs option[value="all-drugs"]').prop('selected', true);
            break;
        case 'all-single-agent-drugs':
            $('#drugs option').prop('selected', false);
            $('#drugs option[value="all-single-agent-drugs"]')
                .prop('selected', true);
            break;
        case 'all-drug-combinations':
            $('#drugs option').prop('selected', false);
            $('#drugs option[value="all-drug-combinations"]')
                .prop('selected', true);
            break;
        default:
            $('#drugs option[value="all-drugs"]').prop('selected', false);
            $('#drugs option[value="all-single-agent-drugs"]')
                .prop('selected', false);
            $('#drugs option[value="all-drug-combinations"]')
                .prop('selected', false);
            break;
        }
    });
    check_method($('input[name=method]:checked').val());
});
function check_method(method) {
    jQuery.each(['name', 'date', 'type'], function(i, block) {
        if (block == method)
            jQuery('#' + block + '-block').show();
        else
            jQuery('#' + block + '-block').hide();
    });
}""")

class Doc:
    "One of these for each document potentially eligible for the report."
    def __init__(self, id, title):
        self.id = id
        self.name = title.split(";")[0].strip()

class DrugInfoSummary:
    """
    One of these for each DrugInfoSummary document selected (by
    one of three possible filtering methods) to be included on
    the report.
    """
    def __init__(self, control, doc_id, doc_version):
        self.control = control
        self.doc_id = doc_id
        self.doc_version = doc_version
        self.description = self.summary = None

        # XXX This report used to join on doc_version but take the
        #     XML from the document table. Surely that was a mistake.
        query = cdrdb.Query("doc_version", "title", "xml")
        query.where(query.Condition("id", doc_id))
        query.where(query.Condition("num", doc_version))
        try:
            title, xml = query.execute(control.cursor, timeout=300).fetchone()
        except Exception, e:
            raise Exception("Database failure fetching CDR%d version %d: %s" %
                            (doc_id, doc_version, e))
        try:
            root = etree.XML(xml.encode("utf-8"))
        except Exception, e:
            raise Exception("Failure parsing CDR%d version %d: %s" %
                            (doc_id, doc_version, e))
        self.name = title.split(";")[0].strip()
        for node in root.iter("Description"):
            self.description = u"".join(self.fetch_text(node))
        filters = ["name:Format DIS SummarySection"]
        parm = [("suppress-nbsp", "true")]
        response = cdr.filterDoc("guest", filters, doc_id, parm=parm)
        if isinstance(response, basestring):
            cdrcgi.bail(response)
            self.summary = '<span class="error">UNAVAILABLE</span>'
        else:
            self.summary = response[0]

    def show(self, page):
        """
        Add a table for this summary and a horizontal ruler to the report page.
        """
        parser = cdrcgi.lxml.html.HTMLParser(encoding="utf-8")
        url = "QcReport.py?Session=guest&DocId=%d" % self.doc_id
        doc_id = page.B.TD(page.B.A(str(self.doc_id), href=url))
        summary = cdrcgi.lxml.html.fromstring("<td>%s</td>" % self.summary,
                                              parser=parser)
        page.add('<table class="dis">')
        for th, td in (
            (page.B.TH("CDR ID"), doc_id),
            (page.B.TH("Drug Name"), page.B.TD(self.name)),
            (page.B.TH("Description"), page.B.TD(self.description)),
            (page.B.TH("Summary"), summary)
        ):
            page.add("<tr>")
            page.add(th)
            page.add(td)
            page.add("</tr>")
        page.add("</table>")
        page.add(page.B.HR())

    def __cmp__(self, other):
        return cmp(self.name.lower(), other.name.lower())

    @staticmethod
    def fetch_text(node):
        """
        Recursively assemble a list of all the text content which is
        not inside a Deletion element.
        """
        text = []
        if node.text is not None:
            text.append(node.text)
        for child in node:
            if child.tag != "Deletion":
                text += DrugInfoSummary.fetch_text(child)
        if node.tail is not None:
            text.append(node.tail)
        return text

if __name__ == "__main__":
    "Allow documentation and lint tools to load script without side effects"
    Control().run()
