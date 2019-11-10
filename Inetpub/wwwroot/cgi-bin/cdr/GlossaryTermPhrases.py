#!/usr/bin/env python

"""Report on phrases matching specified glossary term.
"""

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
            page.add_css("fieldset { width: 1000px; }")
        else:
            fieldset = page.fieldset("Instructions")
            fieldset.append(page.B.P(self.INSTRUCTIONS))
            page.form.append(fieldset)
            fieldset = page.fieldset("Enter Document ID or Glossary Term Name")
            fieldset.append(page.text_field("id", label="Document ID"))
            opts = dict(label="Term Name", value=self.name)
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
            fieldset.append(page.B.P(self.NOTE, page.B.CLASS("warning")))

    def run(self):
        """Customize the routing."""

        try:
            if self.email and self.types and self.id:
                if not self.request or self.request == self.SUBMIT:
                    return self.show_report()
            elif self.request == self.SUBMIT:
                return self.show_form()
        except Exception as e:
            self.logger.exception("Report ailure")
            self.bail(e)
        Controller.run(self)

    def show_report(self):
        """Queue the report and display its status."""

        try:
            self.job.queue()
        except Exception as e:
            self.logger.exception("Failure queueing report")
            self.bail(f"Unable to start job: {e}")
        session = self.session.name
        args = session, self.title, self.JOB_NAME, self.script, self.SUBMENU
        self.job.show_status_page(*args)

    @property
    def args(self):
        """Arguments for the batch job."""

        return (
            ("id", self.id),
            ("types", " ".join(self.types)),
            ("language", self.language),
        )

    @property
    def email(self):
        """Email address(es) to which to send notification of the report."""

        if not hasattr(self, "_email"):
            self._email = (self.fields.getvalue("email") or "").strip()
            if not self._email:
                self._email = self.user.email
        return self._email

    @property
    def id(self):
        """Glossary term document selected for the report.

        XMetaL spells the CGI parameter with an uppercase first letter.
        """

        if not hasattr(self, "_id"):
            self._id = self.fields.getvalue("id")
            if not self._id:
                self._id = self.fields.getvalue("Id")
            if not self._id and len(self.names) == 1:
                self._id = str(self.names[0][0])
        return self._id

    @property
    def job(self):
        """Batch job for the report."""

        if not hasattr(self, "_job"):
            self._job = CdrBatch(**self.opts)
        return self._job

    @property
    def language(self):
        """English or Spanish."""
        return self.fields.getvalue("language") or ""

    @property
    def name(self):
        """Name fragment entered by the user on the form."""
        return (self.fields.getvalue("name") or "").strip()

    @property
    def names(self):
        """Picklist for glossary term names matching the user's fragment."""

        if not hasattr(self, "_names"):
            self._names = []
            fragment = self.name
            if fragment:
                fields = "d.id", "d.title"
                query = self.Query("document d", *fields).order("d.title")
                query.join("doc_type t", "t.id = d.doc_type")
                query.where("t.name = 'GlossaryTermName'")
                query.where(query.Condition("d.title", f"{fragment}%", "LIKE"))
                rows = query.execute(self.cursor).fetchall()
                if not rows:
                    self.bail("No matching documents")
                for id, title in rows:
                    self._names.append((id, f"CDR{id:010d}: {title}"))
        return self._names

    @property
    def opts(self):
        """Options for the batch job constructor."""

        return dict(
            jobName=self.JOB_NAME,
            email=self.email,
            args=self.args,
            command=self.LONG_REPORTS,
        )

    @property
    def types(self):
        """Which type(s) of linking summaries should we look for?"""
        return self.fields.getlist("types")

    @property
    def user(self):
        """Object representing the currently logged-on CDR user."""

        if not hasattr(self, "_user"):
            opts = dict(id=self.session.user_id)
            self._user = self.session.User(self.session, **opts)
        return self._user


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
