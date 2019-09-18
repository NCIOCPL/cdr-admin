#----------------------------------------------------------------------
# Gather information for reports on ExternalRef elements.
#
# Can be used to find broken links or to compare html/head/title
# elements of linked-to web pages with stored versions in
# ExternalRef/@SourceTitle attributes.
#
# BZIssue::5244 - URL Check report not working
# BZIssue::None - (JIRA::OCECDR-3651) - External Refs report
# JIRA::OCECDR-3800 - Appscan vulnerability remediation
#----------------------------------------------------------------------
import cgi
import cdr
import cdrcgi
from cdrbatch import CdrBatch

class Control(cdrcgi.Control):
    BROKEN_URLS = "Broken URLs"
    PAGE_TITLE_MISMATCHES = "Page Title Mismatches"
    REPORT_TYPES = (BROKEN_URLS, PAGE_TITLE_MISMATCHES)
    DOCTYPES = (
        "Citation",
        "ClinicalTrialSearchString",
        "DrugInformationSummary",
        "GlossaryTermConcept",
        "MiscellaneousDocument",
        "Summary"
    )
    METHODS = "doctype", "id"
    def __init__(self):
        cdrcgi.Control.__init__(self, "URL Check")
        self.boards = self.get_boards()
        self.timeouts = self.Timeouts(self.fields)
        self.report_type = self.fields.getvalue("report-type")
        self.method = self.fields.getvalue("method") or "doctype"
        self.email = self.fields.getvalue("email")
        self.doc_id = self.fields.getvalue("cdr-id")
        self.doctype = self.fields.getvalue("doctype") or "Citation"
        self.board = self.fields.getlist("board")
        self.audience = self.fields.getvalue("audience")
        self.language = self.fields.getvalue("language")
        self.redirects = self.fields.getvalue("redirects") and True or False
        self.certs = self.fields.getvalue("certs") and True or False
        self.quick = self.fields.getvalue("quick") and True or False
        self.debug = self.fields.getvalue("debug") and True or False
        self.show_all = self.fields.getvalue("show-all") and True or False
        self.throttles = self.Throttles(self.fields)
        if not self.report_type:
            self.report_type = self.BROKEN_URLS
        self.validate_audience()
        self.validate_language()
        self.validate_boards()
        cdrcgi.valParmEmail(self.email, reveal=False, empty_ok=True)
        cdrcgi.valParmVal(self.method, valList=self.METHODS,
                          msg=cdrcgi.TAMPERING)
        cdrcgi.valParmVal(self.doctype, valList=self.DOCTYPES,
                          msg=cdrcgi.TAMPERING)
        cdrcgi.valParmVal(self.report_type, valList=self.REPORT_TYPES,
                          msg=cdrcgi.TAMPERING)
        if not cdr.canDo(self.session, "RUN LONG REPORT"):
            cdrcgi.bail("Not authorized to run batch reports")
    def get_args(self):
        args = {
            "report_type": self.report_type,
            "connect_timeout": self.timeouts.connect,
            "read_timeout": self.timeouts.read,
            "check_certs": self.certs,
        }
        if self.debug:
            args["debug"] = True
        if self.report_type == self.BROKEN_URLS:
            args["show_redirects"] = self.redirects
        else:
            args["show_all"] = self.show_all
        if self.method == "id":
            try:
                args["doc_id"] = cdr.exNormalize(self.doc_id)[1]
            except:
                args["doc_id"] = None
            if not args["doc_id"]:
                cdrcgi.bail("Valid CDR ID required")
        else:
            args["doc_type"] = self.doctype
            if self.doctype in ("Summary", "GlossaryTermConcept"):
                if self.audience:
                    args["audience"] = self.audience
                if self.language:
                    args["language"] = self.language
                if self.doctype == "Summary" and "all" not in self.board:
                    args["boards"] = self.board
        if self.quick:
            args["throttle"] = True
            args["max_urls"] = self.throttles.urls
            args["max_time"] = self.throttles.seconds
        return args

    def show_report(self):
        command = "lib/Python/CdrLongReports.py"
        args = self.get_args()
        job = CdrBatch(jobName=self.report_type, command=command,
                       args=args.items(), email=self.email)
        if self.quick:
            if self.report_type == self.BROKEN_URLS:
                from CdrLongReports import BrokenExternalLinks as Report
            else:
                from CdrLongReports import PageTitleMismatches as Report
            report = Report(job).create_html_report()
            print("Content-type: text/html\n\n%s" % report)
        else:
            if not self.email:
                cdrcgi.bail("Missing required email address")
            try:
                job.queue()
            except Exception as e:
                cdrcgi.bail("Could not start job: " + str(e))
            job.show_status_page(self.session, self.PAGE_TITLE, self.title,
                                 self.script, self.REPORTS_MENU)
    class Throttles:
        def __init__(self, fields):
            defaults = { "urls": 100, "seconds": 30 }
            for key in defaults:
                name = "max-%s" % key
                try:
                    value = int(fields.getvalue(name) or defaults[key])
                except:
                    value = defaults[key]
                setattr(self, key, value)
    class Timeouts:
        def __init__(self, fields):
            try:
                self.connect = int(fields.getvalue("connect-timeout") or "5")
                self.read = int(fields.getvalue("read-timeout") or "30")
            except:
                cdrcgi.bail("timeout value must be an integer")
    def populate_form(self, form):
        email = self.email or cdr.getEmail(self.session) or ""
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Report Type"))
        for jt in self.REPORT_TYPES:
            checked = jt == self.BROKEN_URLS
            form.add_radio("report-type", jt, jt, checked=checked)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Selection Method"))
        form.add_radio("method", "By Document Type", "doctype", checked=True)
        form.add_radio("method", "By CDR ID", "id")
        form.add("</fieldset>")
        form.add("<fieldset class='by-doctype-block'>")
        form.add(form.B.LEGEND("Document Type"))
        for doctype in self.DOCTYPES:
            checked = doctype == "Citation"
            form.add_radio("doctype", doctype, doctype, checked=checked)
        form.add("</fieldset>")
        self.add_board_fieldset(form)
        self.add_audience_fieldset(form, include_any=True)
        self.add_language_fieldset(form, include_any=True)
        form.add("<fieldset class='by-id-block hidden'>")
        form.add(form.B.LEGEND("Document ID"))
        form.add_text_field("cdr-id", "CDR ID")
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Miscellaneous Options"))
        form.add_checkbox("certs", "Report HTTPS certificates with problems?",
                          "check", checked=True)
        form.add_checkbox("redirects", "Report redirected URLs?", "report",
                          wrapper_classes="broken-urls")
        form.add_checkbox("show-all", "Include matching page titles?",
                          "include", wrapper_classes="hidden title-check")
        quick_tip = ("Check a subset of the URLs directly "
                     "instead of queuing a batch report.")
        form.add_checkbox("quick", "Quick sample report", "yes",
                          tooltip=quick_tip)
        form.add_checkbox("debug", "Log debugging information", "debug")
        form.add("</fieldset>")
        form.add("<fieldset id='throttle-block' class='hidden'>")
        form.add(form.B.LEGEND("Report Limits"))
        form.add_text_field("max-urls", "Max URLs", value="100",
                            tooltip="Check up to this many URLS")
        form.add_text_field("max-seconds", "Max Seconds", value="60",
                            tooltip="Stop checking after this many seconds")
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Timeouts"))
        form.add_text_field("connect-timeout", "Connect", value="5",
                            tooltip="Number of seconds to wait for connection")
        form.add_text_field("read-timeout", "Read", value="30",
                            tooltip="Number of seconds to wait for page")
        form.add("</fieldset>")
        form.add("<fieldset id='email-block'>")
        form.add(form.B.LEGEND("Email (Required)"))
        form.add_text_field("email", "Address(es)", value=email,
                            tooltip="Separate multiple addresses with a space")
        form.add("</fieldset>")
        form.add_script("""\
function check_set(name, val) {
    var all_selector = "#" + name + "-all";
    var ind_selector = "#" + name + "-set .ind";
    if (val == "all") {
        if (jQuery(all_selector).prop("checked"))
            jQuery(ind_selector).prop("checked", false);
        else
            jQuery(all_selector).prop("checked", true);
    }
    else if (jQuery(ind_selector + ":checked").length > 0)
        jQuery(all_selector).prop("checked", false);
    else
        jQuery(all_selector).prop("checked", true);
}
function check_board(board) { check_set("board", board); }
function check_method(method) {
    switch (method) {
        case "id":
            jQuery(".by-doctype-block").hide();
            jQuery(".by-board-block").hide();
            jQuery(".by-id-block").show();
            break;
        case "doctype":
            jQuery(".by-doctype-block").show();
            jQuery(".by-id-block").hide();
            check_doctype();
            break;
    }
}
function check_doctype(doctype) {
    if (jQuery("#doctype-summary").prop("checked") ||
            jQuery("#doctype-glossarytermconcept").prop("checked"))
        jQuery(".by-board-block").show();
    else
        jQuery(".by-board-block").hide();
    if (jQuery("#doctype-summary").prop("checked"))
        jQuery("#board-set").show();
    else
        jQuery("#board-set").hide();
}
function check_quick(setting) {
    if (jQuery("#quick-yes").prop("checked")) {
        jQuery("#throttle-block").show();
        jQuery("#email-block").hide();
    }
    else {
        jQuery("#throttle-block").hide();
        jQuery("#email-block").show();
    }
}
function check_report_type(type) {
    if (type == "%s") { // broken URLs report
        jQuery(".broken-urls").show();
        jQuery(".title-check").hide();
    }
    else {
        jQuery(".broken-urls").hide();
        jQuery(".title-check").show();
    }
}
jQuery(function() {
    check_method(jQuery("input[name='method']:checked").val());
    check_quick(jQuery("input[name='quick']:checked").val());
    check_report_type(jQuery("input[name='report-type']:checked").val());
});""" % self.BROKEN_URLS)
Control().run()
exit(0)
#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
title     = "CDR Administration"
section   = "URL Check"
script    = "CheckUrls.py"
SUBMENU   = 'Report Menu'
buttons   = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
email     = fields.getvalue('Email')
docType   = fields.getvalue('DocType')
audience  = fields.getvalue('Audience') or ''
language  = fields.getvalue('Language') or ''
jobType   = fields.getvalue('JobType')
doc_types = (
    ("", ""),
    ("GlossaryTermConcept", "Glossary Term Concept"),
    ("Summary", "Summary"),
    ("InScopeProtocol", "In-Scope Protocol"),
    ("CTGovProtocol", "CT.gov Protocol"),
    ("DrugInformationSummary", "Drug Information Summary"),
    ("Person", "Person"),
    ("ClinicalTrialSearchString", "Clinical Trials Search String"),
    ("Citation", "Citation"),
    ("MiscellaneousDocument", "Miscellaneous Document"),
    ("Organization", "Organization"),
)
audiences = (
    ("", ""),
    ("HP", "HP"),
    ("Pat", "Patient"),
)
languages = (
    ("", ""),
    ("EN", "English"),
    ("ES", "Spanish"),
)
job_types = (
    ("UrlErrs", "URL Errors", True),
    ("TitleMismatch", "Page Title Mismatches", False),
    ("AllTitles", "All Page Titles", False),
)
instructions = (
    "This report requires a while to complete. "
    "When the report processing has completed, email notification "
    "will be sent to the addresses specified below.  At least "
    "one email address must be provided.  If more than one "
    "address is specified, separate the addresses with a blank. "
    "The Document Type field is also required."
)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Put up the request interface if appropriate.
#----------------------------------------------------------------------
if not email or not email.strip() or not docType or not jobType:
    page = cdrcgi.Page(title, subtitle=section, buttons=buttons,
                       action=script, session=session)
    page.add(page.B.FIELDSET(page.B.P(instructions)))
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Required Fields"))
    page.add_select("DocType", "DocType", doc_types)
    page.add_text_field("Email", "Email", value=cdr.getEmail(session) or "")
    page.add("</fieldset>")
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Required for Summary or Glossary"))
    page.add_select("Audience", "Audience", audiences)
    page.add_select("Language", "Language", languages)
    page.add("</fieldset>")
    page.add("<fieldset>")
    page.add(page.B.LEGEND("Select Type of Report"))
    for value, label, checked in job_types:
        page.add_radio("JobType", label, value, checked=checked)
    page.add("</fieldset>")
    page.send()

#----------------------------------------------------------------------
# Validate the form values. The expectation is that any bogus values
# will come from someone tampering with the form, so no need to provide
# the hacker with any useful diagnostic information.
#----------------------------------------------------------------------
for value, values in ((docType, doc_types), (audience, audiences),
                      (language, languages), (jobType, job_types)):
    if value not in [v[0] for v in values]:
        cdrcgi.bail("Corrupted form value")
if jobType == 'UrlErrs' and docType in ('Summary', 'GlossaryTermConcept'):
    if not audience:
        cdrcgi.bail('Audience not specified')
    if not language:
        cdrcgi.bail('Language not specified')

#----------------------------------------------------------------------
# If we get here, we're ready to queue up a request for the report.
#----------------------------------------------------------------------
args = [('docType', docType),
        ('audience', audience),
        ('language', language),
        ('jobType', jobType)]
command = 'lib/Python/CdrLongReports.py'
batch = cdrbatch.CdrBatch(jobName="URL Check", command=command,
                          email=email.strip(), args=args)
try:
    batch.queue()
except Exception as e:
    cdrcgi.bail("Could not start job: " + str(e))
batch.show_status_page(session, title, section, script, SUBMENU)
