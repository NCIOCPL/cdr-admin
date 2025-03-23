#!/usr/bin/env python

# ----------------------------------------------------------------------
# Release lock blocking future Hoover runs.
# JIRA::OCECDR-4196
# ----------------------------------------------------------------------

import os
import cdr
import cdrcgi


class Control(cdrcgi.Controller):

    PATH = f"{cdr.DEFAULT_LOGDIR}/FileSweeper.lockfile"
    SUBTITLE = "Clear File Sweeper Lockfile"
    DOCTYPE = "SweepSpecifications"
    REPOSITORY = "https://github.com/NCIOCPL/cdr-scheduler"
    CODE = f"{REPOSITORY}/blob/master/jobs/file_sweeper_task.py"

    def populate_form(self, page):
        query = self.Query("document d", "d.id")
        query.join("doc_type t", "t.id = d.doc_type")
        query.where(f"t.name = '{self.DOCTYPE}'")
        id = query.execute(self.cursor).fetchone()
        url = f"ShowCdrDocument.py?Request=Submit&doc-id={id}"
        fieldset = page.fieldset("Instructions")
        fieldset.append(
            page.B.P(
                "Click the ",
                page.B.STRONG("Submit"),
                " button to remove any lock file which blocks future "
                "runs of the job which cleans up the file system, "
                "archiving or removing assets which are no longer "
                "required for normal CDR processing."
            )
        )
        fieldset.append(
            page.B.P(
                "The processing performed by this scheduled job is "
                "controlled by the singleton document of type ",
                page.B.EM(self.DOCTYPE),
                ". Modify and store a new version of that document to "
                "change the settings which determine what the job will do. "
                "Click ",
                page.B.A("here", href=url, target="_blank"),
                " to view the current settings for this tier. "
                "Read the extensive inline documentation in the ",
                page.B.A("script", href=self.CODE, target="_blank"),
                " for specific information about how each processing rule "
                "is handled during a cleanup job."
            )
        )
        page.form.append(fieldset)

    def build_tables(self):
        """No tables to display, so go back to the form after processing."""

        if not self.session.can_do("MANAGE SCHEDULER"):
            self._alert = dict(
                message="You are not authorized to perform this action.",
                type="error",
            )
        elif os.path.exists(self.PATH):
            try:
                os.unlink(self.PATH)
                self._alert = dict(
                    message="Lock file successfully removed.",
                    type="success",
                )
            except Exception:
                self._alert = dict(
                    message="Unable to remove lock file.",
                    type="error",
                )
        else:
            self._alert = dict(
                message="Lock file not found.",
                type="warning",
            )
        self.show_form()

    @property
    def alerts(self):
        """What to show the user at the top of the page."""
        return [self._alert] if hasattr(self, "_alert") else []

    @property
    def same_window(self):
        """Stay on the same tab."""
        return [self.SUBMIT]


if __name__ == "__main__":
    Control().run()
