#!/usr/bin/env python

"""Delete a file from the CDR client set.
"""

from cdrcgi import Controller
from functools import cached_property
from pathlib import Path
from cdr import run_command


class Control(Controller):
    """Access to the current CDR login session and page-building tools."""

    SUBTITLE = "Remove Client File"
    LOGNAME = "RemoveClientFile"

    def populate_form(self, page):
        """Prompt for the file and an optional comment.

        Checking for processing logs triggers the file removal
        if a file has been selected, and in that case the logs
        are displayed below the form.

        Pass:
            page - HTMLPage on which we place the fields
        """

        fieldset = page.fieldset("Select File")
        fieldset.append(page.select("path", options=self.paths))
        page.form.append(fieldset)
        if self.logs is not None:
            fieldset = page.fieldset("Processing Logs")
            fieldset.append(self.logs)
            page.form.append(fieldset)
            page.add_css("fieldset { width: 600px } #comment { width: 450px }")
            page.add_css("pre { color: green }")

    def show_report(self):
        """Cycle back to the form."""
        self.show_form()

    @cached_property
    def client_files(self):
        """Location where the client files are stored."""

        return Path(self.session.tier.basedir, "ClientFiles")

    @cached_property
    def path(self):
        """Relative path to the file selected for deletion."""
        return self.fields.getvalue("path")

    @cached_property
    def paths(self):
        """List of client files installed on the CDR Server."""

        paths = [p for p in self.client_files.rglob("*") if p.is_file()]
        paths = [p.relative_to(self.client_files) for p in paths]
        paths = [str(p) for p in paths]
        return [["", "- Select file -"]] + sorted(paths, key=str.lower)

    @cached_property
    def logs(self):
        """Log output describing the outcome of the operation."""

        if self.path:
            if not self.session.can_do("MANAGE CLIENT FILES"):
                error = "Account not authorized for managing client files."
                self.bail(error)
            path = self.client_files / self.path
            if "/.." in str(path) or "\\.." in str(path):
                self.logger.warning("suspected hacking with path %s", path)
                self.bail()
            run_command(f"fix-permissions.cmd {self.client_files}")
            try:
                path.unlink(missing_ok=True)
            except Exception as e:
                self.logger.exception("removing %s", path)
                self.bail(e)
            message = "\n\n".join([
                f"Removed {path}.",
                self.__refresh_manifest().strip(),
                "File removed successfully.",
                f"Elapsed: {self.elapsed}",
            ])
            return self.HTMLPage.B.PRE(message)
        return None

    @cached_property
    def same_window(self):
        """Don't open a new tab when processing the form."""
        return [self.SUBMIT]

    def __refresh_manifest(self):
        """Rebuild the client manifest file.

        Return:
            string to append to the processing log display
        """

        cmd = r"python d:\cdr\build\RefreshManifest.py"
        result = run_command(cmd, merge_output=True)
        if result.returncode:
            output = result.stdout
            raise Exception(f"Manifest refresh failure: {output}")
        self.logger.info("Manifest updated")
        return "Running RefreshManifest.py ...\n" + result.stdout


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
