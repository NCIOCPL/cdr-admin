#!/usr/bin/env python

"""Run the ReverifyPushJob script from the web admin interface.
"""

from cdrcgi import Controller
from cdr import BASEDIR, PYTHON, run_command

class Control(Controller):
    """Access to the database, logging, form building, etc."""

    SUBTITLE = "Reverify Gatekeeper Push Job"
    LOGNAME = "ReverifyJob"
    PUBDIR = f"{BASEDIR}/Publishing"
    STATUSES = "Failure", "Stalled", "Success"
    MODES = "test", "live"
    REVERIFY_SCRIPT = "ReverifyPushJob.py"

    def populate_form(self, page):
        """Show fields we need.

        Pass:
            page - HTMLPage object
        """

        fieldset = page.fieldset("Job")
        fieldset.append(page.text_field("jobid", label="Job ID"))
        page.form.append(fieldset)
        fieldset = page.fieldset("Status")
        for status in self.STATUSES:
            opts = dict(value=status)
            if status == "Success":
                opts["checked"] = True
            fieldset.append(page.radio_button("status", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Mode")
        checked = True
        for mode in self.MODES:
            label = f"{mode.title()} mode"
            opts = dict(value=mode, label=label, checked=checked)
            fieldset.append(page.radio_button("mode", **opts))
            checked = False
        page.form.append(fieldset)

    def show_report(self):
        """Override, since this is not a standard tabular report."""

        if not self.jobid:
            self.show_form()
        else:
            output = self.run_command()
            buttons = (
                self.HTMLPage.button(self.DEVMENU),
                self.HTMLPage.button(self.ADMINMENU),
                self.HTMLPage.button(self.LOG_OUT),
            )
            opts = dict(
                buttons=buttons,
                session=self.session,
                action=self.script,
                banner=self.title,
                subtitle=self.subtitle,
            )
            report = self.HTMLPage(self.title, **opts)
            report.body.append(self.HTMLPage.B.PRE(output))
            report.add_css("pre { font-size: .8em; }")
            report.send()

    def run_command(self):
        """Launch the external script.

        Return:
            standard output from the launched script
        """

        self.logger.info("--------------------------------------------")
        self.logger.info("%s: session %r", self.REVERIFY_SCRIPT, self.session)
        self.logger.info("%s: user:   %r", self.REVERIFY_SCRIPT, self.user)
        self.logger.info("%s: job-id: %s", self.REVERIFY_SCRIPT, self.jobid)
        self.logger.info("%s: status: %s", self.REVERIFY_SCRIPT, self.status)
        self.logger.info("%s: mode:   %s", self.REVERIFY_SCRIPT, self.mode)
        self.logger.info('Submitting command...\n%s', self.command)
        try:
            process = run_command(self.command, merge_output=True)
        except Exception as e:
            self.logger.exception("Failure running command")
            self.bail(e)
        self.logger.info("Code: %s" % process.returncode)
        self.logger.info("Outp: %s" % process.stdout)
        return process.stdout

    @property
    def command(self):
        """Command string for launching a new process."""

        if not hasattr(self, "_command"):
            path = f"{self.PUBDIR}/{self.REVERIFY_SCRIPT}".replace("/", "\\")
            self._command = f"{PYTHON} {path} {self.opts}"
        return self._command

    @property
    def jobid(self):
        """Integer ID for the job to reverify."""

        if not hasattr(self, "_jobid"):
            self._jobid = self.fields.getvalue("jobid")
            if self._jobid:
                try:
                    self._jobid = int(self._jobid)
                except:
                    self.bail("Invalid job ID")
        return self._jobid

    @property
    def mode(self):
        """Command-line option for live or test mode."""

        if not hasattr(self, "_mode"):
            self._mode = self.fields.getvalue("mode")
            if self._mode not in self.MODES:
                self.bail()
        return self._mode

    @property
    def opts(self):
        """String of options ready for the command line."""

        if not hasattr(self, "_opts"):
            opts = "session", "jobid", "status"
            opts = [f"--{opt}={getattr(self, opt)}" for opt in opts]
            self._opts = " ".join(opts) + f" --{self.mode}mode"
        return self._opts

    @property
    def status(self):
        """Status of job to reverify."""

        if not hasattr(self, "_status"):
            self._status = self.fields.getvalue("status")
            if self._status not in self.STATUSES:
                self.bail()
        return self._status

    @property
    def user(self):
        """CDR account name of current user, for logging."""
        return self.session.user_name


if __name__ == "__main__":
    """Don't execute script if loaded as a module."""
    Control().run()
