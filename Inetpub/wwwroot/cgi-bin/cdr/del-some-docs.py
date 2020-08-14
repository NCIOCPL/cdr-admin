#!/usr/bin/env python

"""Delete CDR documents.

The documents aren't actually deleted, but instead their active_status
column is set to 'D'.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):

    SUBTITLE = "CDR Document Deletion"
    LOGNAME = "del-some-docs"
    LEGEND = "Select Documents To Delete (with optional comment)"
    REASON = "Deleted using the CDR Admin interface"
    INSTRUCTIONS = (
        "Enter document IDs separated by spaces and/or line breaks. "
        "If you check the 'Validate' box below, documents which would "
        "introduce link validation errors if deleted will not be deleted. "
        "If you uncheck this box, the validation errors will still be "
        "displayed, but the document deletion will be processed."
    )

    def populate_form(self, page):
        """Add fields to the form.

        Pass:
            page - HTMLPage object which presents the fields
        """

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        prefix = "It is recommended that you run the "
        suffix = " to check for links to the documents you plan to delete."
        opts = dict(href="LinkedDocs.py", target="_blank")
        link = page.B.A("linked-docs report", **opts)
        warning = page.B.P(prefix, link, suffix, page.B.CLASS("warning"))
        fieldset.append(warning)
        page.form.append(fieldset)
        fieldset = page.fieldset(self.LEGEND)
        fieldset.append(page.textarea("ids", label="CDR IDs", rows=3))
        fieldset.append(page.textarea("reason", label="Comment"))
        page.form.append(fieldset)
        fieldset = page.fieldset("Options")
        label = "Validate? (Please read the instructions above)"
        opts = dict(value="validate", label=label, checked=True)
        fieldset.append(page.checkbox("options", **opts))
        page.form.append(fieldset)
        if self.results is not None:
            fieldset = page.fieldset("Processing Results")
            fieldset.append(self.results)
            page.form.append(fieldset)

    def show_report(self):
        """Override to handle everything on the form page."""
        self.show_form()

    @property
    def buttons(self):
        """Customize the action buttons on the banner bar."""
        return self.SUBMIT, self.DEVMENU, self.ADMINMENU, self.LOG_OUT

    @property
    def ids(self):
        """CDR IDs of documents which are to be marked as deleted."""

        if not hasattr(self, "_ids"):
            self._ids = []
            ids = self.fields.getvalue("ids")
            if ids:
                for id in ids.split():
                    try:
                        self._ids.append(Doc.extract_id(id))
                    except:
                        self.bail("Invalid document ID")
        return self._ids

    @property
    def reason(self):
        """Explanation for the deletions."""

        if not hasattr(self, "_reason"):
            self._reason = self.fields.getvalue("reason", self.REASON)
        return self._reason

    @property
    def results(self):
        """Processing results from any deletion requests."""

        if not hasattr(self, "_results"):
            self._results = None
            if self.ids:
                self.logger.info(" session: %r", self.session)
                self.logger.info("    user: %r", self.session.user_name)
                self.logger.info("validate: %r", self.validate)
                self.logger.info("  reason: %r", self.reason)
                B = self.HTMLPage.B
                items = []
                opts = dict(reason=self.reason, validate=self.validate)
                for id in self.ids:
                    doc = Doc(self.session, id=id)
                    cdr_id = doc.cdr_id
                    try:
                        doc.delete(**opts)
                        self.logger.info("Deleted %s", cdr_id)
                        message = f"{cdr_id} deleted successfully"
                        items.append(B.LI(message, B.CLASS("info")))
                        for error in doc.errors:
                            self.logger.warning("%s: %s", cdr_id, error)
                            items.append(B.LI(f"{cdr_id}: {error}"))
                    except Exception as e:
                        self.logger.exception(cdr_id)
                        items.append(B.LI(f"{cdr_id}: {e}", B.CLASS("error")))
                self._results = B.UL(*items)
        return self._results

    @property
    def validate(self):
        """Whether deletions should be blocked for docs that are linked."""
        return "validate" in self.fields.getlist("options")


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
