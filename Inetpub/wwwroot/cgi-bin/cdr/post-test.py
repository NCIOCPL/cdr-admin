#!/usr/bin/env python

"""Test Python multipart/form-data handling.
"""

from functools import cached_property
from cdrcgi import Controller


class Control(Controller):

    SUBTITLE = "Python POST Test"

    def populate_form(self, page):
        """Prompt for the item to be tested.

        Pass:
            page - HTMLPage object on which we place the fields
        """

        if not self.session.can_do("MANAGE SCHEDULER"):
            self.bail("Not authorized")
        fieldset = page.fieldset("Post Test")
        fieldset.append(page.text_field("name"))
        fieldset.append(page.file_field("file", label="Test File"))
        page.form.append(fieldset)
        page.form.set("enctype", "multipart/form-data")

    def show_report(self):
        """Post the file and loop back to the form."""

        if self.file_bytes is None:
            self.alerts.append(dict(
                message="No file selected.",
                type="warning",
            ))
        if not self.name:
            self.alerts.append(dict(
                message="File name is required.",
                type="warning",
            ))
        if not self.alerts:
            with open(f"d:/tmp/{self.name}", "wb") as fp:
                fp.write(self.file_bytes)
            self.alerts.append(dict(
                message=f"Posted {self.name}.",
                type="success",
            ))
        self.show_form()

    @cached_property
    def file_bytes(self):
        """Sequence of bytes for the item being posted."""

        if "file" not in list(self.fields.keys()):
            return None
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
        return b"".join(segments)

    @cached_property
    def name(self):
        """Name of the posted file."""
        return self.fields.getvalue("name", "").strip()

    @cached_property
    def same_window(self):
        """Avoid opening new browser tabs."""
        return [self.SUBMIT]


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
