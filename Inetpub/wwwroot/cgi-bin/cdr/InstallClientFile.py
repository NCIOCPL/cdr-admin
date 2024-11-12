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
        page.form.set("enctype", "multipart/form-data")

    def show_report(self):
        """Cycle back to the form."""
        self.show_form()

    @cached_property
    def same_window(self):
        """Don't open a new tab when processing the form."""
        return [self.SUBMIT]

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
    def alerts(self):
        """Log output describing the outcome of the operation."""

        if self.file_bytes and self.location:
            if not self.session.can_do("MANAGE CLIENT FILES"):
                message = "Account not authorized for managing client files."
                return [dict(message=message, type="warning")]
            path = self.client_files / self.location
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.logger.exception("creating directories for %s", path)
                message = f"Failure creating directories for {path}: {e}"
                return [dict(message=message, type="error")]
            try:
                path.write_bytes(self.file_bytes)
            except Exception as e:
                self.logger.exception("writing to %s", path)
                return [dict(
                    message=f"Failure writing {path}: {e}",
                    type="error",
                )]
            run_command(f"fix-permissions.cmd {self.client_files}")
            return self.__refresh_manifest(path)
            message = "\n\n".join([
                f"Saved {path}.",
                self.__refresh_manifest().strip(),
                "File installed successfully.",
                f"Elapsed: {self.elapsed}",
            ])
            return self.HTMLPage.B.PRE(message)
        elif self.file_bytes or self.location:
            return [dict(
                message="File and Location fields are both required.",
                type="warning",
            )]
        return []

    def __refresh_manifest(self, path):
        """Rebuild the client manifest file.

        Return:
            string to append to the processing log display
        """

        cmd = r"python d:\cdr\build\RefreshManifest.py"
        result = run_command(cmd, merge_output=True)
        if result.returncode:
            output = result.stdout
            return [dict(
                message=f"Manifest refresh failure: {output}",
                type="error",
            )]
        self.logger.info("Manifest updated")
        message = f"{path} successfully installed in {self.elapsed}."
        return [dict(message=message, type="success")]


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
