#!/usr/bin/env python

"""Create new summary document for translated version (CGI interface).
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):

    SUBTITLE = "Create World Server Translated Summary"
    LOGNAME = "PostTranslatedSummary"
    COMMENT = "Creating document translated in Trados"

    def populate_form(self, page):
        """Prompt for the file and an optional comment.

        Pass:
            page - HTMLPage on which we place the fields
        """

        fieldset = page.fieldset("Translated Summary")
        fieldset.append(page.file_field("file", label="Summary File"))
        fieldset.append(page.text_field("comment", value=self.comment))
        page.form.append(fieldset)
        page.form.set("enctype", "multipart/form-data")

    def show_report(self):
        """Post the document and loop back to the form."""

        if not self.session.can_do("CREATE WS SUMMARIES"):
            self.bail("Account not authorized for adding WS summaries.")
        if not self.document:
            self.alerts.append(dict(
                message="Summary document not posted.",
                type="warning",
            ))
        else:
            try:
                self.document.save(**self.opts)
                self.alerts.append(dict(
                    message=f"Successfully created {self.document.cdr_id}.",
                    type="success",
                ))
            except Exception as e:
                self.logger.exception("Save failure")
                self.alerts.append(dict(
                    message=f"Failure: {e}",
                    type="error",
                ))
        self.show_form()

    @cached_property
    def comment(self):
        """Override the default comment as appropriate."""
        return self.fields.getvalue("comment", self.COMMENT)

    @cached_property
    def document(self):
        """Uploaded summary document to be posted."""

        if not self.file_bytes:
            return None
        return Doc(self.session, doctype="Summary", xml=self.file_bytes)

    @cached_property
    def file_bytes(self):
        """UTF-8 serialization of the document to be posted."""

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
    def opts(self):
        """Options passed the the `Doc.save()` method."""

        return dict(
            version=True,
            unlock=True,
            comment=self.comment,
            reason=self.comment,
        )

    @cached_property
    def same_window(self):
        """Avoid opening new browser tabs."""
        return [self.SUBMIT]


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
