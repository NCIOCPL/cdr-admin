#!/usr/bin/env python

"""Restore deleted CDR documents.

The documents aren't actually deleted, but instead their active_status
column is set to 'D'.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):

    SUBTITLE = "CDR Document Restoration"
    LOGNAME = "DocumentRestoration"
    LEGEND = "Select Documents To Restore (with optional comment)"
    REASON = "Restored using the CDR Admin interface"
    INSTRUCTIONS = "Enter document IDs separated by spaces and/or line breaks."

    def populate_form(self, page):
        """Add fields to the form.

        Pass:
            page - HTMLPage object which presents the fields
        """

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)
        fieldset = page.fieldset(self.LEGEND)
        fieldset.append(page.textarea("ids", label="CDR IDs", rows=3))
        fieldset.append(page.textarea("reason", label="Comment"))
        page.form.append(fieldset)
        fieldset = page.fieldset("New Status")
        opts = dict(value="I", label="Inactive", checked=True)
        fieldset.append(page.radio_button("status", **opts))
        opts = dict(value="A", label="Active", checked=False)
        fieldset.append(page.radio_button("status", **opts))
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
        """CDR IDs of documents which are to be marked as restored."""

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
                status = "Active" if self.status == "A" else "Blocked"
                self.logger.info(" session: %r", self.session)
                self.logger.info("    user: %r", self.session.user_name)
                self.logger.info("  status: %r", status)
                self.logger.info("  reason: %r", self.reason)
                B = self.HTMLPage.B
                items = []
                for id in self.ids:
                    doc = Doc(self.session, id=id)
                    cdr_id = doc.cdr_id
                    try:
                        doc.set_status(self.status, comment=self.reason)
                        self.logger.info("Restored %s", cdr_id)
                        message = f"{cdr_id} restored successfully"
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
    def status(self):
        """New status for the documents (Active or Inactive)."""
        if not hasattr(self, "_status"):
            self._status = self.fields.getvalue("status", "I")
            if not self._status in "IA":
                self.bail()
        return self._status


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
