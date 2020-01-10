#!/usr/bin/env python

"""Automate Quarterly ZIP Code Updates

Copy the ZIP code zip-archive file to the CDR server and load to the
zip_code database table.
"""

from os import path
from time import sleep
from zipfile import ZipFile
from cdrcgi import Controller
from cdr import BASEDIR, PYTHON, run_command

class Control(Controller):
    """Access to the database and form-building tools."""

    SUBTITLE = "Upload ZIP Codes"
    LOGNAME = "UploadZIPCodes"
    FIX_PERMISSIONS = path.join(BASEDIR, "Bin", "fix-permissions.cmd")
    FIX_PERMISSIONS = FIX_PERMISSIONS.replace("/", path.sep)

    def populate_form(self, page):
        """Display instructions and prompt for the file.

        Pass:
            page - HTMLPage on which we place the fields
        """

        fieldset = page.fieldset("Instructions")
        paragraph = page.B.P(
            "The load will take several minutes. Don't press ",
            page.B.EM("Submit"),
            " twice."
        )
        fieldset.append(paragraph)
        page.form.append(fieldset)
        fieldset = page.fieldset("Upload ZIP Files")
        fieldset.append(page.file_field("file", label="Codes"))
        page.form.append(fieldset)
        if self.logs is not None:
            fieldset = page.fieldset("Processing Output")
            fieldset.append(self.logs)
            page.form.append(fieldset)
            page.add_css("pre { color: green }")
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
            if "file" in list(self.fields.keys()):
                field = self.fields["file"]
                if field.file:
                    segments = []
                    while True:
                        more_bytes = field.file.read()
                        if not more_bytes:
                            break
                        segments.append(more_bytes)
                else:
                    segments = [field.value]
                self._file_bytes = b"".join(segments)
        return self._file_bytes

    @property
    def logs(self):
        """Log output describing the outcome of an upload action."""

        if not hasattr(self, "_logs"):
            self._logs = None
            if self.zipfile:
                if not self.session.can_do("UPLOAD ZIP CODES"):
                    error = "Account not authorized for uploading zip files."
                    self.bail(error)
                ziptxt = f"/tmp/zip-{self.timestamp}.txt"
                try:
                    with open(ziptxt, "wb") as fp:
                        fp.write(self.zipfile.read("z5max.txt"))
                except Exception as e:
                    self.logger.exception("Failure creating %s", ziptxt)
                    self.bail(f"Failure creating {ziptext}: {e}")
                zipload = f"{BASEDIR}/utilities/bin/LoadZipCodes.py"
                command = f"{PYTHON} {zipload} {ziptxt}"
                process = run_command(command, merge_output=True)
                if process.returncode:
                    self.logger.error("%s: %s", zipload, process.stdout)
                else:
                    self.logger.info("ZIP codes loaded successfully")
                self._logs = self.HTMLPage.B.PRE(process.stdout)
        return self._logs

    @property
    def zipfile(self):
        """Compressed archive from the ZIPList5 vendor."""

        if not hasattr(self, "_zipfile"):
            self._zipfile = None
            if self.file_bytes:
                name = f"zipcodes-{self.timestamp}.zip"
                filepath = f"{BASEDIR}/uploads/{name}"
                try:
                    with open(filepath, "wb") as fp:
                        fp.write(self.file_bytes)
                except Exception as e:
                    self.logger.exception("Failure storing %s", filepath)
                    self.bail(f"failure storing {filepath}: {e}")
                self.__fix_permissions(filepath)
                self._zipfile = ZipFile(filepath)
                self.logger.info("Stored %s", filepath)
        return self._zipfile

    def __fix_permissions(self, filepath):
        """Clean up messiness in the file system on CBIIT Windows servers."""

        sleep(2)
        filepath = filepath.replace("/", path.sep)
        command = f"{self.FIX_PERMISSIONS} {filepath}"
        process = run_command(command, merge_output=True)
        if process.returncode:
            extra = command, process.stdout
            self.bail("Failure fixing file permissions", extra=extra)


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
