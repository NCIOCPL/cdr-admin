#!/usr/bin/env python

"""Track the processing of audio pronunciation media documents.
"""

from cdrcgi import Controller
from cdrbatch import CdrBatch


class Control(Controller):

    JOB_NAME = SUBTITLE = "Audio Pronunciation Recordings Tracking Report"
    LANGUAGES = dict(all="All", en="English", es="Spanish")
    LONG_REPORTS = "lib/Python/CdrLongReports.py"
    ARGS = "start", "end", "language"

    def populate_form(self, page):
        """Show the instructions and request the required values.

        Pass:
            page - HTMLPage where we drop the forms
        """
        fieldset = page.fieldset("Date Range")
        fieldset.append(page.date_field("start_date", value=self.start))
        fieldset.append(page.date_field("end_date", value=self.end))
        page.form.append(fieldset)
        fieldset = page.fieldset("Language")
        for langcode in sorted(self.LANGUAGES):
            opts = dict(value=langcode, label=self.LANGUAGES[langcode])
            if langcode == "all":
                opts["checked"] = True
            fieldset.append(page.radio_button("language", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Email Address for Report Notification")
        fieldset.append(page.text_field("email", value=self.email))
        page.form.append(fieldset)

    def show_report(self):
        """Queue the report and display its status."""

        if not self.email:
            self.bail("Missing required email address")
        try:
            self.job.queue()
        except Exception as e:
            self.logger.exception("Failure queueing report")
            self.bail(f"Unable to start job: {e}")
        self.job.show_status_page(self.session.name, self.title,
                                  self.JOB_NAME, self.script, self.SUBMENU)

    @property
    def args(self):
        """Arguments for the batch job."""
        return [(name, getattr(self, name)) for name in self.ARGS]

    @property
    def email(self):
        """Email address to which we send the notification."""

        if not hasattr(self, "_email"):
            self._email = self.fields.getvalue("email")
            if not self._email:
                self._email = self.user.email
        return self._email

    @property
    def user(self):
        """The currently logged-in user."""

        if not hasattr(self, "_user"):
            opts = dict(id=self.session.user_id)
            self._user = self.session.User(self.session, **opts)
        return self._user

    @property
    def end(self):
        """End of the date range for the report."""

        default = self.started.strftime("%Y-%m-%d")
        return self.fields.getvalue("end_date") or default

    @property
    def job(self):
        """Batch job for the report."""

        if not hasattr(self, "_job"):
            self._job = CdrBatch(**self.opts)
        return self._job

    @property
    def language(self):
        """Language code selected for the report."""
        return self.fields.getvalue("language")

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
    def start(self):
        """Beginning of the date range for the report."""
        return self.fields.getvalue("start_date") or "2011-01-01"


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
