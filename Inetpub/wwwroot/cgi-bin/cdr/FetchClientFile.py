#!/usr/bin/env python

"""Retrieve a file from the CDR client set.
"""

from cdrcgi import Controller
from functools import cached_property
from pathlib import Path
from sys import stdout


class Control(Controller):
    """Access to the current CDR login session and page-building tools."""

    SUBTITLE = "Fetch Client File"
    LOGNAME = "FetchClientFile"

    def populate_form(self, page):
        """Prompt for the file and an optional comment.

        Pass:
            page - HTMLPage on which we place the fields
        """

        fieldset = page.fieldset("Select File")
        fieldset.append(page.select("path", options=self.paths))
        page.form.append(fieldset)

    def show_report(self):
        """Send the selected file back to the browser."""

        if self.path:
            path = self.client_files / self.path
            if "/.." in str(path) or "\\.." in str(path):
                self.logger.warning("suspected hacking with path %s", path)
                self.bail()
            try:
                file_bytes = path.read_bytes()
            except Exception as e:
                self.logger.exception("reading %s", path)
                self.bail(f"{path}: {e}")
            self.logger.info("fetching %s", path)
            headers = "\r\n".join([
                "Content-Type: application/octet-stream",
                f"Content-Disposition: attachment; filename={path.name}",
                f"Content-Length: {len(file_bytes)}",
            ]) + "\r\n\r\n"
            stdout.buffer.write(headers.encode("utf-8"))
            if file_bytes:
                stdout.buffer.write(file_bytes)

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


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
