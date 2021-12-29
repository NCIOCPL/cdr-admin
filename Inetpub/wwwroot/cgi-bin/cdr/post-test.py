#!/usr/bin/env python

"""Test Python multipart/form-data handling.
"""

from cdrcgi import Controller


class Control(Controller):

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
        """Loop back to the form."""
        self.show_form()

    @property
    def file_bytes(self):
        """Sequence of bytes for the item being posted."""

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
    def name(self):
        """Name of the posted file."""
        return self.fields.getvalue("name")

    @property
    def subtitle(self):
        """String displayed below the primary banner."""

        if self.file_bytes and self.name:
            with open(f"d:/tmp/{self.name}", "wb") as fp:
                fp.write(self.file_bytes)
            return f"Posted {self.name}"
        return "Python POST Test"


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
