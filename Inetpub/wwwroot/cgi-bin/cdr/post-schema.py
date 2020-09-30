#!/usr/bin/env python

"""Post a new or modified CDR schema document.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc
from os.path import basename
from cdr import run_command

class Control(Controller):
    """Access to the current CDR login session and page-building tools."""

    SUBTITLE = "Post CDR Schema"
    LOGNAME = "post-schema"
    ACTIONS = (
        ("add", "Add New Schema"),
        ("replace", "Replace Existing Schema"),
    )

    def populate_form(self, page):
        """Prompt for the file and an optional comment.

        Checking for processing logs triggers the schema save
        if a schema file has been posted, and in that case the
        logs are displayed below the form.

        Pass:
            page - HTMLPage on which we place the fields
        """

        fieldset = page.fieldset("Schema")
        fieldset.append(page.file_field("file", label="Summary File"))
        fieldset.append(page.text_field("comment"))
        page.form.append(fieldset)
        fieldset = page.fieldset("Action")
        checked = False
        for value, label in self.ACTIONS:
            opts = dict(value=value, label=label, checked=checked)
            fieldset.append(page.radio_button("action", **opts))
            checked = True
        page.form.append(fieldset)
        if self.logs is not None:
            fieldset = page.fieldset("Processing Logs")
            fieldset.append(self.logs)
            page.form.append(fieldset)
            page.add_css("fieldset { width: 600px } #comment { width: 450px }")
            page.add_css("pre { color: green }")
        page.form.set("enctype", "multipart/form-data")

    def show_report(self):
        """Cycle back to the form."""
        self.show_form()

    @property
    def action(self):
        """Are we replacing an existing schema or adding a new one?"""
        return self.fields.getvalue("action")

    @property
    def buttons(self):
        """Customize the action buttons on the banner bar."""
        return self.SUBMIT, self.DEVMENU, self.ADMINMENU, self.LOG_OUT

    @property
    def comment(self):
        """Override the default comment as appropriate."""

        if not hasattr(self, "_comment"):
            self._comment = self.fields.getvalue("comment")
            if not self._comment:
                verb = "Replacing" if self.document.id else "Adding"
                self._comment = f"{verb} schema using admin interface"
        return self._comment

    @property
    def document(self):
        """Uploaded summary document to be posted."""

        if not hasattr(self, "_document"):
            self._document = None
            if self.schema_title and self.file_bytes:
                title = self.schema_title
                xml = self.file_bytes
                opts = dict(xml=xml, doctype="schema")
                query = self.Query("document d", "d.id")
                query.join("doc_type t", "t.id = d.doc_type")
                query.where("t.name = 'schema'")
                query.where(query.Condition("d.title", title))
                rows = query.execute(self.cursor).fetchall()
                if rows:
                    if self.action == "add":
                        raise Exception(f"Schema {title} already exists")
                    if len(rows) > 1:
                        raise Exception(f"Multiple schemas match {title}")
                    opts["id"] = rows[0].id
                else:
                    if self.action != "add":
                        raise Exception(f"Schema document {title} not found")
                self._document = Doc(self.session, **opts)
                if rows:
                    self._document.check_out(comment="locking for update")
        return self._document

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
    def logs(self):
        """Log output describing the outcome of a post action."""

        if not hasattr(self, "_logs"):
            self._logs = None
            if self.document:
                if not self.session.can_do("MODIFY DOCUMENT", "schema"):
                    error = "Account not authorized for posting schemas."
                    self.bail(error)
                self.document.save(**self.opts)
                message = "\n\n".join([
                    f"Saved {self.document.cdr_id}.",
                    self.__check_dtds().strip(),
                    self.__refresh_manifest().strip(),
                    "Schema posted successfully.",
                    f"Elapsed: {self.elapsed}",
                ])
                self._logs = self.HTMLPage.B.PRE(message)
        return self._logs

    @property
    def opts(self):
        """Options passed to the `Doc.save()` method."""

        if not hasattr(self, "_opts"):
            self._opts = dict(
                version=True,
                unlock=True,
                comment=self.comment,
                reason=self.comment,
                title=self.schema_title,
            )
        return self._opts

    @property
    def schema_title(self):
        """Name of the uploaded file without the full path."""

        if not hasattr(self, "_filename"):
            self._title = None
            if self.file_field is not None:
                self._title = basename(self.file_field.filename)
                self.logger.info("filename for schema is %r", self._title)
        return self._title

    def __check_dtds(self):
        """Regenerate the DTDs to reflect the new/updated schema.

        Return:
            string to append to the processing log display
        """

        cmd = r"python d:\cdr\build\CheckDtds.py"
        result = run_command(cmd, merge_output=True)
        if result.returncode:
            raise Exception(f"DTD check failure: result.stdout")
        self.logger.info("DTDs updated")
        return "Running CheckDtds.py ...\n" + result.stdout

    def __refresh_manifest(self):
        """Rebuild the client manifest file.

        Return:
            string to append to the processing log display
        """

        cmd = r"python d:\cdr\build\RefreshManifest.py"
        result = run_command(cmd, merge_output=True)
        if result.returncode:
            output = result.stdout
            raise Exception(f"Manifest refresh failure: {output}")
        self.logger.info("Manifest updated")
        return "Running RefreshManifest.py ...\n" + result.stdout


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
