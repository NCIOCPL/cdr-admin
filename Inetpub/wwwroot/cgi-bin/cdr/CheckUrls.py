#!/usr/bin/env python

"""Gather information for reports on ExternalRef elements.

Can be used to find broken links or to compare html/head/title
elements of linked-to web pages with stored versions in
ExternalRef/@SourceTitle attributes.
"""

from sys import stdout
from cdrapi.docs import Doc
from cdrcgi import Controller
from cdrbatch import CdrBatch


class Control(Controller):
    """Top-level program logic controller."""

    SUBTITLE = "URL Check"
    BROKEN_URLS = "Broken URLs"
    PAGE_TITLE_MISMATCHES = "Page Title Mismatches"
    LONG_REPORTS = "lib/Python/CdrLongReports.py"
    REPORT_TYPES = BROKEN_URLS, PAGE_TITLE_MISMATCHES
    INCLUDE_ANY_AUDIENCE_CHECKBOX = True
    INCLUDE_ANY_LANGUAGE_CHECKBOX = True
    DOCTYPES = (
        "Citation",
        "ClinicalTrialSearchString",
        "DrugInformationSummary",
        "GlossaryTermConcept",
        "MiscellaneousDocument",
        "Summary"
    )
    METHODS = (
        ("doctype", "By Document Type", True),
        ("id", "By CDR ID", False),
    )
    OPTS = (
        ("certs", "Report HTTPS certificates with problems?", True, False),
        ("redirects", "Report redirected URLs?", False, False),
        ("show-all", "Include matching page titles?", False, True),
        ("quick", "Quick sample report", False, False),
        ("debug", "Log debugging information", False, False),
    )
    QUICK_TIP = (
        "Check a subset of the URLs directly "
        "instead of queuing a batch report."
    )
    REPORT_LIMITS = (
        ("URLs", 100, "Check up to this many URLs"),
        ("Seconds", 60, "Stop checking after this many seconds"),
    )
    TIMEOUTS = (
        ("Connect", 5, "Number of seconds to wait for connection"),
        ("Read", 30, "Number of seconds to wait for page"),
    )

    def populate_form(self, page):
        """Add the fields to the form.

        Pass:
            page - HTMLPage object where we place the fields.
        """

        # Don't waste the user's time if this report isn't allowed.
        if not self.session.can_do("RUN LONG REPORT"):
            self.bail("Not authorized to run batch reports")

        # The top two blocks of radio buttons are always available.
        fieldset = page.fieldset("Report Type")
        for rt in self.REPORT_TYPES:
            opts = dict(value=rt, label=rt, checked=rt==self.BROKEN_URLS)
            fieldset.append(page.radio_button("report-type", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Selection Method")
        for value, label, checked in self.METHODS:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("method", **opts))
        page.form.append(fieldset)

        # These are only shown when the selection method is document type.
        fieldset = page.fieldset("Document Type")
        fieldset.set("class", "by-doctype-block")
        for doctype in self.DOCTYPES:
            checked = doctype == "Citation"
            opts = dict(value=doctype, label=doctype, checked=checked)
            fieldset.append(page.radio_button("doctype", **opts))
        page.form.append(fieldset)

        # The availability of these depends on the selected document type.
        self.add_board_fieldset(page)
        self.add_audience_fieldset(page)
        self.add_language_fieldset(page)

        # Suppress this block if selecting documents by type (the default).
        fieldset = page.fieldset("Document ID")
        fieldset.set("class", "by-id-block")
        fieldset.set("hidden")
        fieldset.append(page.text_field("cdr-id", label="CDR ID"))
        page.form.append(fieldset)

        # Always visible, but some in the block are conditionally hidden.
        fieldset = page.fieldset("Miscellaneous Options")
        for value, label, checked, hidden in self.OPTS:
            opts = dict(value=value, label=label, checked=checked)
            opts["wrapper_classes"] = [f"opts-{value}-wrapper"]
            if hidden:
                opts["wrapper_classes"].append("hidden")
            if value == "quick":
                opts["tooltip"] = self.QUICK_TIP
            fieldset.append(page.checkbox("opt", **opts))
        page.form.append(fieldset)

        # Options available only for the "quick" (testing) version.
        fieldset = page.fieldset("Report Limits")
        fieldset.set("id", "throttle-block")
        fieldset.set("class", "hidden")
        for what, value, tooltip in self.REPORT_LIMITS:
            opts = dict(label=f"Max {what}", value=value, tooltip=tooltip)
            fieldset.append(page.text_field(f"max-{what.lower()}", **opts))
        page.form.append(fieldset)

        # These are always available.
        fieldset = page.fieldset("Timeouts")
        for what, value, tooltip in self.TIMEOUTS:
            opts = dict(label=what, value=value, tooltip=tooltip)
            fieldset.append(page.text_field(f"{what.lower()}-timeout", **opts))
        page.form.append(fieldset)

        # Not used for the "quick" version of the report.
        fieldset = page.fieldset("Email (Required)")
        fieldset.set("id", "email-block")
        opts = dict(value=self.email, label="Address(es)")
        opts["tooltip"] = "Separate multiple addresses with a space"
        fieldset.append(page.text_field("email", **opts))
        page.form.append(fieldset)

        # Use client-side scripting to hide/show fields.
        page.head.append(page.B.SCRIPT(src="../../js/CheckUrls.js"))

    def show_report(self):
        """Batch report, so we override the base class version."""

        if not self.session.can_do("RUN LONG REPORT"):
            self.bail("Not authorized to run batch reports")
        opts = dict(
            jobName=self.report_type,
            command=self.LONG_REPORTS,
            args=self.args,
            email=" ".join(self.email),
        )
        job = CdrBatch(**opts)
        if self.quick:
            if self.report_type == self.BROKEN_URLS:
                from CdrLongReports import BrokenExternalLinks as Report
            else:
                from CdrLongReports import PageTitleMismatches as Report
            report = Report(job).create_html_report()
            stdout.buffer.write(b"Content-type: text/html\n\n")
            stdout.buffer.write(report.encode("utf-8"))
        else:
            if not self.email:
                self.bail("Missing required email address")
            try:
                job.queue()
            except Exception as e:
                self.bail(f"Could not start job: {e}")
            args = self.TITLE, self.subtitle, self.script, self.SUBMENU
            job.show_status_page(self.session, *args)

    @property
    def args(self):
        """Arguments passed to the batch job contructor."""

        if not hasattr(self, "_args"):
            self._args = {
                "report_type": self.report_type,
                "connect_timeout": self.timeouts.connect,
                "read_timeout": self.timeouts.read,
                "check_certs": self.certs,
            }
            if self.debug:
                self._args["debug"] = True
            if self.report_type == self.BROKEN_URLS:
                self._args["show_redirects"] = self.redirects
            else:
                self._args["show_all"] = self.show_all
            if self.method == "id":
                if not self.doc_id:
                    self.bail("Valid CDR ID required")
                self._args["doc_id"] = self.doc_id
            else:
                self._args["doc_type"] = self.doctype
                if self.doctype in ("Summary", "GlossaryTermConcept"):
                    if self.audience:
                        self._args["audience"] = self.audience
                    if self.language:
                        self._args["language"] = self.language
                    if self.doctype == "Summary" and self.board:
                        self._args["boards"] = self.board
            if self.quick:
                self._args["throttle"] = True
                self._args["max_urls"] = self.throttles.urls
                self._args["max_time"] = self.throttles.seconds
            self._args = list(self._args.items())
        return self._args

    @property
    def audience(self):
        """Patient or health professional?"""

        if not hasattr(self, "_audience"):
            self._audience = self.fields.getvalue("audience")
            if self._audience:
                if self._audience not in self.AUDIENCES:
                    self.bail()
        return self._audience

    @property
    def board(self):
        """PDQ board(s) selected for the report."""

        if not hasattr(self, "_board"):
            all_boards = list(self.get_boards())
            boards = self.fields.getlist("board")
            if "all" in boards:
                self._board = None
            else:
                self._board = []
                for board in boards:
                    if not board.isdigit():
                        self.bail()
                    board = int(board)
                    if board not in all_boards:
                        self.bail()
                    self._board.append(board)
        return self._board

    @property
    def certs(self):
        """True if we should report on HTTPS certifications with problems."""
        return "certs" in self.opts

    @property
    def debug(self):
        """True if we should perform extra logging."""
        return "debug" in self.opts

    @property
    def doc_id(self):
        """CDR ID of document to be checked."""

        if not hasattr(self, "_doc_id"):
            self._doc_id = self.fields.getvalue("cdr-id")
            if self._doc_id:
                try:
                    self._doc_id = Doc.extract_id(self._doc_id)
                except:
                    self.bail("Invalid document ID")
        return self._doc_id

    @property
    def doctype(self):
        """CDR document type selected for the report."""

        if not hasattr(self, "_doctype"):
            self._doctype = self.fields.getvalue("doctype") or "Citation"
            if self._doctype not in self.DOCTYPES:
                self.bail()
        return self._doctype

    @property
    def email(self):
        """Sequence or string for where the report should be sent."""

        if not hasattr(self, "_email"):
            if self.request == self.SUBMIT:
                email = self.fields.getvalue("email", "").strip()
                self._email = []
                for string in email.split():
                    address = self.parse_email_address(string)
                    if address:
                        self._email.append(address)
            else:
                self._email = self.session.user.email
        return self._email

    @property
    def language(self):
        """English or Spanish?"""

        if not hasattr(self, "_language"):
            self._language = self.fields.getvalue("language")
            if self._language:
                if self._language not in self.LANGUAGES:
                    self.bail()
        return self._language

    @property
    def method(self):
        """Are we selecting documents by ID or by type?"""

        if not hasattr(self, "_method"):
            self._method = self.fields.getvalue("method") or "doctype"
            allowed = {method[0] for method in self.METHODS}
            if self._method not in allowed:
                self.bail()
        return self._method

    @property
    def opts(self):
        """Miscellaneous report options."""
        return self.fields.getlist("opt")

    @property
    def quick(self):
        """True if we deliver the report immediately, avoiding the queue."""
        return "quick" in self.opts

    @property
    def report_type(self):
        """Broken URLs or page title mismatches."""

        if not hasattr(self, "_report_type"):
            self._report_type = self.fields.getvalue("report-type")
            if not self._report_type:
                self._report_type = self.BROKEN_URLS
            elif self._report_type not in self.REPORT_TYPES:
                self.bail()
        return self._report_type

    @property
    def redirects(self):
        """True if we should report redirected URLs."""
        return "redirect" in self.opts

    @property
    def show_all(self):
        """True if we should include matching page titles."""
        return "show-all" in self.opts

    @property
    def throttles(self):
        """Options for doing a subset of the report for testing."""

        if not hasattr(self, "_throttles"):
            self._throttles = self.Throttles(self)
        return self._throttles

    @property
    def timeouts(self):
        """How long to wait before giving up on a URL."""

        if not hasattr(self, "_timeouts"):
            self._timeouts = self.Timeouts(self)
        return self._timeouts


    class Throttles:
        """Values for scaling back the report for testing."""

        def __init__(self, control):
            defaults = dict(urls=100, seconds=30)
            fields = control.fields
            for key in defaults:
                name = f"max-{key}"
                try:
                    value = int(fields.getvalue(name) or defaults[key])
                except:
                    value = defaults[key]
                setattr(self, key, value)


    class Timeouts:
        """Controls for how patiently we'll wait."""

        def __init__(self, control):
            fields = control.fields
            try:
                self.connect = int(fields.getvalue("connect-timeout") or "5")
                self.read = int(fields.getvalue("read-timeout") or "30")
            except:
                control.bail("timeout value must be an integer")


if __name__ == "__main__":
    Control().run()
