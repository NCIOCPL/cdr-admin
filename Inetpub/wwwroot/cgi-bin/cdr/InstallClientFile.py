#!/usr/bin/env python

"""Post a new or modified CDR client file.
"""

from cdrcgi import Controller
from functools import cached_property
from pathlib import Path
from cdr import run_command


class Control(Controller):
    """Access to the current CDR login session and page-building tools."""

    SUBTITLE = "Install Client File"
    LOGNAME = "InstallClientFile"
    INSTRUCTIONS = (
        "Select the file to be installed and then provide the path "
        "(including the filename), relative to {}, for the location where "
        "the file is to be installed. For example, Macros\\cdr.xml, or "
        "(for a file to be installed directly in the root of the client "
        "files area) certificate.png."
    )

    def populate_form(self, page):
        """Prompt for the file and an optional comment.

        Checking for processing logs triggers the file save
        if a file has been posted, and in that case the logs
        are displayed below the form.

        Pass:
            page - HTMLPage on which we place the fields
        """

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS.format(self.client_files)))
        page.form.append(fieldset)
        fieldset = page.fieldset("Client File")
        fieldset.append(page.file_field("file"))
        fieldset.append(page.text_field("location"))
        page.form.append(fieldset)
        if self.logs is not None:
            fieldset = page.fieldset("Processing Logs")
            fieldset.append(self.logs)
            page.form.append(fieldset)
            page.add_css("fieldset { width: 600px } #comment { width: 450px }")
            page.add_css("pre { color: green }")
        page.form.set("enctype", "multipart/form-data")

    def show_report(self):
        """Cycle back to the form."""
        self.show_form()

    @cached_property
    def buttons(self):
        """Customize the action buttons on the banner bar."""
        return self.SUBMIT, self.DEVMENU, self.ADMINMENU, self.LOG_OUT

    @cached_property
    def client_files(self):
        """Location where the client files are stored."""
        return Path(self.session.tier.basedir, "ClientFiles")

    @cached_property
    def file_bytes(self):
        """Bytes for the client file to be installed."""

        if self.file_field is not None:
            if self.file_field.file:
                segments = []
                while True:
                    more_bytes = self.file_field.file.read()
                    if not more_bytes:
                        break
                    segments.append(more_bytes)
            else:
                segments = [self.file_field.value]
            return b"".join(segments)
        return None

    @cached_property
    def file_field(self):
        """CGI field for the uploaded file, if any."""

        if "file" in list(self.fields.keys()):
            return self.fields["file"]
        return None

    @cached_property
    def location(self):
        """Relative path where the file will be installed."""

        location = self.fields.getvalue("location")
        if not location:
            return None
        location = location.strip().strip("/").strip("\\")
        return location or None

    @cached_property
    def logs(self):
        """Log output describing the outcome of the operation."""

        if self.file_bytes and self.location:
            if not self.session.can_do("MANAGE CLIENT FILES"):
                error = "Account not authorized for managing client files."
                self.bail(error)
            path = self.client_files / self.location
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.logger.exception("creating directories for %s", path)
                self.bail(e)
            try:
                path.write_bytes(self.file_bytes)
            except Exception as e:
                self.logger.exception("writing to %s", path)
                self.bail(e)
            run_command(f"fix-permissions.cmd {self.client_files}")
            message = "\n\n".join([
                f"Saved {path}.",
                self.__refresh_manifest().strip(),
                "File installed successfully.",
                f"Elapsed: {self.elapsed}",
            ])
            return self.HTMLPage.B.PRE(message)
        return None

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
