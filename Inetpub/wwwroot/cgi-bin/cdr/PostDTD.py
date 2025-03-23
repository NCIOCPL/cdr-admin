#!/usr/bin/env python

"""Post a modified DTD to the CDR server.
"""

from functools import cached_property
from cdrcgi import Controller
from cdr import run_command, PDQDTDPATH, FIX_PERMISSIONS


class Control(Controller):
    """Access to the current CDR login session and page-building tools."""

    SUBTITLE = "Post DTD"
    LOGNAME = "PostDTD"
    PATHS = dict(cg=f"{PDQDTDPATH}/pdqCG.dtd", vendor=f"{PDQDTDPATH}/pdq.dtd")

    def populate_form(self, page):
        """Prompt for the file and an optional comment.

        Pass:
            page - HTMLPage on which we place the fields
        """

        fieldset = page.fieldset("File Selection")
        fieldset.append(page.file_field("file", label="DTD File"))
        page.form.append(fieldset)
        fieldset = page.fieldset("DTD Type")
        opts = dict(value="cg", checked=True, label="Cancer.gov (pdqCG.dtd)")
        fieldset.append(page.radio_button("flavor", **opts))
        opts = dict(value="vendor", label="Vendor (pdq.dtd)")
        fieldset.append(page.radio_button("flavor", **opts))
        page.form.append(fieldset)
        page.form.set("enctype", "multipart/form-data")

    def show_report(self):
        """Perform the requested operation and redraw the form."""

        if not self.file_bytes:
            self.alerts.append(dict(
                message="No DTD file selected.",
                type="error",
            ))
        else:
            try:
                path = self.path.replace("\\", "/")
                with open(path, "wb") as fp:
                    fp.write(self.file_bytes)
                command = rf"{FIX_PERMISSIONS} {self.path}"
                result = run_command(command, merge_output=True)
                if result.returncode:
                    args = command, result.stdout
                    self.logger.error("%s failed: %s", *args)
                    self.alerts.append(dict(
                        message=f"Failure fixing permissions for {path}.",
                        type="error",
                    ))
                else:
                    self.alerts.append(dict(
                        message=f"Successfully installed {path}.",
                        type="success",
                    ))
            except Exception as e:
                self.logger.exception(path)
                self.alerts.append(dict(
                    message=f"Failed installing {path} ({e}).",
                    type="error",
                ))
        self.show_form()

    @cached_property
    def file_bytes(self):
        """UTF-8 serialization of the document to be posted."""

        if self.file_field is None:
            return None
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

    @cached_property
    def file_field(self):
        """CGI field for the uploaded file, if any."""

        if "file" not in list(self.fields.keys()):
            return None
        return self.fields["file"]

    @cached_property
    def path(self):
        """Location in the file system where the DTD gets installed."""

        path = self.PATHS.get(self.fields.getvalue("flavor"))
        if not path:
            self.bail()
        return path.replace("/", "\\")

    @cached_property
    def same_window(self):
        """Stay in the same browser tab."""
        return [self.SUBMIT]


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
