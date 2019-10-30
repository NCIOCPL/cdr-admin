#!/usr/bin/env python

"""Create new summary document for translated version (CGI interface).
"""

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
        if self.message is not None:
            page.form.append(self.message)
        fieldset.append(page.file_field("file", label="Summary File"))
        fieldset.append(page.text_field("comment"))
        page.form.append(fieldset)
        page.form.set("enctype", "multipart/form-data")

    def show_report(self):
        """Cycle back to the form."""
        self.show_form()

    @property
    def comment(self):
        """Override the default comment as appropriate."""

        if not hasattr(self, "_comment"):
            self._comment = self.fields.getvalue("comment", self.COMMENT)
        return self._comment

    @property
    def document(self):
        """Uploaded summary document to be posted."""

        if not hasattr(self, "_document"):
            self._document = None
            if self.file_bytes:
                opts = dict(doctype="Summary", xml=self.file_bytes)
                self._document = Doc(self.session, **opts)
        return self._document

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
    def message(self):
        """Paragraph element describing the outcome of a post action."""

        if not hasattr(self, "_message"):
            self._message = None
            if self.document:
                if not self.session.can_do("CREATE WS SUMMARIES"):
                    error = "Account not authorized for adding WS summaries."
                    self.bail(error)
                try:
                    self.document.save(**self.opts)
                    message = f"Saved {self.document.cdr_id}."
                    message_class = self.HTMLPage.B.CLASS("info center")
                except Exception as e:
                    self.logger.exception("Save failure")
                    message = f"Failure: {e}"
                    message_class = self.HTMLPage.B.CLASS("error center")
                self._message = self.HTMLPage.B.P(message, message_class)
        return self._message

    @property
    def opts(self):
        """Options passed the the `Doc.save()` method."""

        if not hasattr(self, "_opts"):
            self._opts = dict(
                version=True,
                unlock=True,
                comment=self.comment,
                reason=self.comment,
            )
        return self._opts


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
