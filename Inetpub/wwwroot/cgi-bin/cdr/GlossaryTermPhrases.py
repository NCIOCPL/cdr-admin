#!/usr/bin/env python

"""Report on phrases matching specified glossary term.
"""

from functools import cached_property
from cdrapi.docs import Doc
from cdrcgi import Controller
from cdrbatch import CdrBatch


class Control(Controller):
    """Access to the database and to report/form-building tools."""

    SUBTITLE = "Glossary Term Phrases Report"
    JOB_NAME = "Glossary Term Search"
    LOGNAME = "GlossaryTermPhrases"
    LONG_REPORTS = "lib/Python/CdrLongReports.py"
    INSTRUCTIONS = (
        "This report requires a few minutes to complete. "
        "A document ID or a term name must be provided. If you enter a name "
        "string which matches the start of more than one term name, you "
        "will be asked to select the term name for the report from the "
        "list of matching names. "
        "When the report processing has completed, email notification "
        "will be sent to all addresses specified below.  At least "
        "one email address must be provided.  If more than one "
        "address is specified, separate the addresses with a blank."
    )
    TYPES = (
        ("HPSummaries", "Health Professional Summaries"),
        ("PatientSummaries", "Patient Summaries"),
    )
    LANGUAGES = "English", "Spanish"
    NOTE = "The report can take several minutes to prepare; please be patient."

    def populate_form(self, page):
        """Add the fields and instruction to the form page.

        Pass:
            page - HTMLPage object where we build the form
        """

        if self.email and self.types and self.names:
            fieldset = page.fieldset("Select Term For Report")
            for id, label in self.names:
                opts = dict(label=label, value=id)
                fieldset.append(page.radio_button("id", **opts))
            page.form.append(fieldset)
            page.form.append(page.hidden_field("email", self.email))
            page.form.append(page.hidden_field("language", self.language))
            for summary_type in self.types:
                page.form.append(page.hidden_field("types", summary_type))
        else:
            entered_id = self.fields.getvalue("id")
            entered_name = self.fields.getvalue("name")
            if self.request == self.SUBMIT:
                if not self.email:
                    self.alerts.append(dict(
                        message="At least one email address is required.",
                        type="warning"))
                if not self.types:
                    self.alerts.append(dict(
                        message="At least one document type is required.",
                        type="warning"))
                if not entered_id and not entered_name:
                    self.alerts.append(dict(
                        message="ID or name must be specified.",
                        type="warning"))
                if entered_id and entered_name:
                    self.alerts.append(dict(
                        message="ID and name may not both be specified.",
                        type="warning"))
            fieldset = page.fieldset("Instructions")
            fieldset.append(page.B.P(self.INSTRUCTIONS))
            page.form.append(fieldset)
            fieldset = page.fieldset("Enter Document ID or Glossary Term Name")
            opts = dict(label="Document ID", value=entered_id)
            fieldset.append(page.text_field("id", **opts))
            opts = dict(label="Term Name", value=entered_name)
            fieldset.append(page.text_field("name", **opts))
            page.form.append(fieldset)
            fieldset = page.fieldset("Enter Required Email Address")
            fieldset.append(page.text_field("email", value=self.email))
            page.form.append(fieldset)
            legend = "Document Types (at least one is required)"
            fieldset = page.fieldset(legend)
            for value, label in self.TYPES:
                checked = value in self.types
                opts = dict(value=value, label=label, checked=checked)
                fieldset.append(page.checkbox("types", **opts))
            page.form.append(fieldset)
            fieldset = page.fieldset("Language")
            for language in self.LANGUAGES:
                checked = self.language == language
                opts = dict(value=language, checked=checked)
                fieldset.append(page.radio_button("language", **opts))
            page.form.append(fieldset)
            fieldset = page.fieldset()
            classes = "text-red text-bold"
            fieldset.append(page.B.P(self.NOTE, page.B.CLASS(classes)))
            page.form.append(fieldset)

    def run(self):
        """Customize the routing."""

        try:
            if self.email and self.types and self.id:
                return self.show_report()
            return self.show_form()
        except Exception as e:
            self.logger.exception("Report ailure")
            self.bail(e)

    def show_report(self):
        """Queue the report and display its status."""

        try:
            self.job.queue()
        except Exception as e:
            self.logger.exception("Failure queueing report")
            self.bail(f"Unable to start job: {e}")
        self.job.show_status_page(self.session)

    @cached_property
    def args(self):
        """Arguments for the batch job."""

        return (
            ("id", self.id),
            ("types", " ".join(self.types)),
            ("language", self.language),
        )

    @cached_property
    def email(self):
        """Email address(es) to which to send notification of the report."""

        email = (self.fields.getvalue("email") or "").strip()
        return email or self.user.email

    @cached_property
    def id(self):
        """Glossary term document selected for the report.

        XMetaL spells the CGI parameter with an uppercase first letter.
        """

        if self.name:
            return None
        id = self.fields.getvalue("id") or self.fields.getvalue("Id")
        if not id and len(self.names) == 1:
            id = str(self.names[0][0])
        if id:
            warning = None
            doc = Doc(self.session, id=id)
            if not doc.title:
                warning = f"Document CDR{id} not found."
            elif doc.doctype.name != "GlossaryTermName":
                warning = f"CDR{id} is a {doc.doctype.name} document."
            if warning:
                self.alerts.append(dict(message=warning, type="warning"))
                return None
        return id

    @cached_property
    def job(self):
        """Batch job for the report."""
        return CdrBatch(**self.opts)

    @cached_property
    def language(self):
        """English or Spanish."""
        return self.fields.getvalue("language") or ""

    @cached_property
    def name(self):
        """Name fragment entered by the user on the form."""
        return (self.fields.getvalue("name") or "").strip()

    @cached_property
    def names(self):
        """Picklist for glossary term names matching the user's fragment."""

        if self.fields.getvalue("id"):
            return None
        names = []
        if self.name and self.types:
            fields = "d.id", "d.title"
            query = self.Query("document d", *fields).order("d.title")
            query.join("doc_type t", "t.id = d.doc_type")
            query.where("t.name = 'GlossaryTermName'")
            query.where(query.Condition("d.title", f"{self.name}%", "LIKE"))
            rows = query.execute(self.cursor).fetchall()
            for id, title in rows:
                names.append((id, f"CDR{id:010d}: {title}"))
            if not names:
                message = f"No names found starting with {self.name!r}."
                self.alerts.append(dict(message=message, types="warning"))
        return names

    @cached_property
    def opts(self):
        """Options for the batch job constructor."""

        return dict(
            jobName=self.JOB_NAME,
            email=self.email,
            args=self.args,
            command=self.LONG_REPORTS,
        )

    @cached_property
    def same_window(self):
        """Only create one new browser tab."""
        return [self.SUBMIT] if self.request else []

    @cached_property
    def types(self):
        """Which type(s) of linking summaries should we look for?"""
        return self.fields.getlist("types")

    @cached_property
    def suppress_sidenav(self):
        """Use the full grid container width for the second form."""
        return True if self.email and self.types and self.names else False

    @cached_property
    def user(self):
        """Object representing the currently logged-on CDR user."""
        return self.session.User(self.session, id=self.session.user_id)


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
