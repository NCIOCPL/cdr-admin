#!/usr/bin/env python

from os import listdir
import sys
from cdrcgi import Controller

class Control(Controller):

    SUBMIT = None
    SUBTITLE = "Board Member Letters"

    def populate_form(self, page):
        """Add links to the letters which were generated.

        Pass:
            page - HTMLPage object to which we add the links
        """

        if self.filepath:
            return self.send_file()
        legend = f"PDQ Board Member Letters for Job {self.job}"
        fieldset = page.fieldset(legend)
        ol = page.B.OL()
        params = dict(job=self.job)
        for name in listdir(self.job_directory):
            if name.endswith(".rtf") and not name.startswith("~"):
                params["file"] = name
                link = page.menu_link(self.script, name, **params)
                ol.append(page.B.LI(link))
        fieldset.append(ol)
        page.form.append(fieldset)

    def send_file(self):
        """Send the requested RTF file and exit."""

        with open(self.filepath, "rb") as fp:
            file_bytes = fp.read()
            headers = (
                "Content-Type: application/rtf;charset=utf-8",
                f"Content-Length: {len(file_bytes)}",
                f"Content-Disposition: attachment; filename={self.filename}",
            )
            for header in headers:
                sys.stdout.buffer.write(header.encode("utf-8"))
                sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.write(b"\n")
            sys.stdout.buffer.write(file_bytes)
            sys.exit(0)

    @property
    def filename(self):
        """Name of the RTF file to send back to the browser."""
        return self.fields.getvalue("file")

    @property
    def filepath(self):
        """Location of the RTF file to return."""

        if not hasattr(self, "_filepath"):
            if self.filename is None:
                self._filepath = None
            else:
                self._filepath = f"{self.job_directory}/{self.filename}"
        return self._filepath

    @property
    def job(self):
        """Job for which we will be showing board member letters."""

        if not hasattr(self, "_job"):
            self._job = self.fields.getvalue("job")
            if not self._job:
                self.bail("Missing job parameter")
        return self._job

    @property
    def job_directory(self):
        """Location of the generated board member letters."""

        if not hasattr(self, "_job_directory"):
            mailers = f"{self.session.tier.basedir}/Output/Mailers"
            directory = f"{mailers}/Job{self.job}-r"
            self._job_directory = directory.replace("\\", "/")
        return self._job_directory


if __name__ == "__main__":
    """Don't execute the script if we're loaded as a module."""
    Control().run()
