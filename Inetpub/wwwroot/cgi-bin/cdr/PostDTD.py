#!/usr/bin/env python

"""Post a modified DTD to the CDR server.
"""

from cdrcgi import Controller
from os.path import basename
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

        fieldset = page.fieldset("DTD")
        fieldset.append(page.file_field("file", label="DTD File"))
        page.form.append(fieldset)
        fieldset = page.fieldset("Flavor")
        opts = dict(value="cg", checked=True, label="Cancer.gov (pdqCG.dtd)")
        fieldset.append(page.radio_button("flavor", **opts))
        opts = dict(value="vendor", label="Vendor (pdq.dtd)")
        fieldset.append(page.radio_button("flavor", **opts))
        page.form.append(fieldset)
        page.form.set("enctype", "multipart/form-data")

    def show_report(self):
        """Cycle back to the form."""
        self.show_form()

    @property
    def buttons(self):
        """Customize the action buttons on the banner bar."""
        return self.SUBMIT, self.DEVMENU, self.ADMINMENU, self.LOG_OUT

    @property
    def file_bytes(self):
        """UTF-8 serialization of the document to be posted."""

        if not hasattr(self, "_file_bytes"):
            self._file_bytes = None
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
                self._file_bytes = b"".join(segments)
        return self._file_bytes

    @property
    def file_field(self):
        """CGI field for the uploaded file, if any."""

        if not hasattr(self, "_file_field"):
            self._file_field = None
            if "file" in list(self.fields.keys()):
                self._file_field = self.fields["file"]
        return self._file_field

    @property
    def path(self):
        """Location in the file system where the DTD gets installed."""

        if not hasattr(self, "_path"):
            path = self.PATHS.get(self.fields.getvalue("flavor"))
            if not path:
                self.bail()
            self._path = path.replace("/", "\\")
        return self._path

    @property
    def subtitle(self):
        """What we display under the banner.

        Calculation of this string value actually installs the DTD
        if we have one.
        """

        if not hasattr(self, "_subtitle"):
            self._subtitle = self.SUBTITLE
            if self.file_bytes:
                try:
                    path = self.path.replace("\\", "/")
                    with open(path, "wb") as fp:
                        fp.write(self.file_bytes)
                    command = rf"{FIX_PERMISSIONS} {self.path}"
                    result = run_command(command, merge_output=True)
                    if result.returncode:
                        args = command, result.stdout
                        self.logger.error("%s failed: %s", *args)
                        message = f"Failure fixing permissions for {path}"
                        self._subtitle = message
                    else:
                        self._subtitle = f"Successfully installed {path}"
                except Exception as e:
                    self.logger.exception(path)
                    self._subtitle = f"Failed installing {path} (see logs)"
        return self._subtitle


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
