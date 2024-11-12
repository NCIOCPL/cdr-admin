#!/usr/bin/env python

"""Track the processing of audio pronunciation media documents.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrbatch import CdrBatch


class Control(Controller):

    SUBTITLE = "Pronunciation Recordings Tracking Report"
    JOB_NAME = "Audio Pronunciation Recordings Tracking Report"
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
        self.job.show_status_page(self.session)

    @cached_property
    def args(self):
        """Arguments for the batch job."""
        return [(name, getattr(self, name)) for name in self.ARGS]

    @cached_property
    def email(self):
        """Email address to which we send the notification."""
        return self.fields.getvalue("email") or self.user.email

    @cached_property
    def user(self):
        """The currently logged-in user."""

        opts = dict(id=self.session.user_id)
        return self.session.User(self.session, **opts)

    @cached_property
    def end(self):
        """End of the date range for the report."""

        value = self.parse_date(self.fields.getvalue("end_date"))
        return str(value or self.started.strftime("%Y-%m-%d"))

    @cached_property
    def job(self):
        """Batch job for the report."""
        return CdrBatch(**self.opts)

    @cached_property
    def language(self):
        """Language code selected for the report."""
        return self.fields.getvalue("language")

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
    def start(self):
        """Beginning of the date range for the report."""

        start = self.parse_date(self.fields.getvalue("start_date"))
        return str(start or "2011-01-01")


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
