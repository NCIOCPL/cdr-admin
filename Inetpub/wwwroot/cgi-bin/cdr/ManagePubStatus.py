#!/usr/bin/env python

"""Let the user adjust the status of unfinished jobs.
"""

from functools import cached_property
from cdrcgi import Controller


class Control(Controller):

    SUBTITLE = "Manage Publishing Job Status"
    WAIT = "Waiting user approval"
    FAILURE = "Failure"
    IN_PROCESS = "In process"
    NEW_STATUSES = FAILURE, IN_PROCESS
    USE_PUBLISHING_SYSTEM = "USE PUBLISHING SYSTEM"
    INSTRUCTIONS = (
        "This page is for managing the status of unfinished publishing jobs, "
        "either by marking an unfinished (possibly stalled) job as failed, "
        "or (in the case of a job which is waiting for approval before "
        "proceeding), releasing the held job. Note that if ALL documents "
        "for a job need to be pushed, you need to fail the job, and manually "
        "submit a push job with the PushAllDocs paramater set to Yes."
    )
    HEADERS = "Job ID", "Job Type", "Job Started", "Job Status", "Actions"
    FIELDS = "id", "pub_subset", "started", "status"

    def run(self):
        """Override the base class version because this isn't a report."""

        if self.request:
            Controller.run(self)
        else:
            if not self.session.can_do(self.USE_PUBLISHING_SYSTEM):
                self.bail("Permission denied.")
            if self.id and self.status:
                if self.status not in self.NEW_STATUSES:
                    self.bail()
                values = self.status, self.id
                self.cursor.execute(
                    "UPDATE pub_proc"
                    "   SET status = ?"
                    " WHERE id = ?"
                    "   AND status NOT IN ('Success', 'Failure')", values)
                self.conn.commit()
                message = f"Set the status for job {self.id} to {self.status}."
                self.alerts.append(dict(message=message, type="success"))
            self.show_form()

    def populate_form(self, page):
        """Show the instructions andd the unfinished jobs.

        Pass:
            page - HTMLPage which holds the form
        """

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)
        fieldset = page.fieldset("Unfinished Publishing Jobs")
        headers = [page.B.TH(header) for header in self.HEADERS]
        thead = page.B.THEAD(page.B.TR(*headers))
        classes = "usa-table usa-table--borderless"
        table = page.B.TABLE(thead, page.B.CLASS(classes))
        for job in self.jobs:
            started = str(job.started)[:19]
            opts = dict(id=job.id, status=self.FAILURE)
            url = self.make_url(self.script, **opts)
            onclick = f"location.href='{url}'"
            button = page.button("Fail", onclick=onclick)
            buttons = page.B.SPAN(button)
            if job.status == self.WAIT:
                opts["status"] = self.IN_PROCESS
                url = self.make_url(self.script, **opts)
                onclick = f"location.href='{url}'"
                buttons.append(page.button("Resume", onclick=onclick))
            tr = page.B.TR(
                page.B.TD(str(job.id), page.B.CLASS("center")),
                page.B.TD(job.pub_subset),
                page.B.TD(started, page.B.CLASS("center")),
                page.B.TD(job.status),
                page.B.TD(buttons)
            )
            table.append(tr)
        fieldset.append(table)
        page.form.append(fieldset)
        page.add_css(
            ".usa-form .usa-button { margin-top: 0; }\n"
            "table { width: 100%; }\n"
        )

    @cached_property
    def buttons(self):
        """Form has no Submit button."""
        return []

    @cached_property
    def id(self):
        """Integer for the job we want to manage."""

        id = self.fields.getvalue("id")
        if id:
            try:
                return int(id)
            except Exception:
                self.logger.exception("bad job ID")
                self.bail()
        return None

    @cached_property
    def jobs(self):
        """Jobs which haven't yet hit the finish line."""

        query = self.Query("pub_proc", *self.FIELDS).order("started")
        query.where("status NOT IN ('Success', 'Failure', 'Verifying')")
        return query.execute(self.cursor).fetchall()

    @cached_property
    def status(self):
        """String for the new status to be applied to the job."""
        return self.fields.getvalue("status")


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
