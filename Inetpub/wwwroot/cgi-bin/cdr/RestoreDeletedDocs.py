#!/usr/bin/env python

"""Restore deleted CDR documents.

The documents aren't actually deleted, but instead their active_status
column is set to 'D'.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):

    SUBTITLE = "CDR Document Restoration"
    LOGNAME = "DocumentRestoration"
    LEGEND = "Select Documents To Restore"
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
        fieldset.append(page.textarea("ids", label="CDR IDs"))
        opts = dict(label="Comment (optional)", value=self.reason)
        fieldset.append(page.textarea("reason", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("New Status")
        opts = dict(value="I", label="Inactive", checked=True)
        fieldset.append(page.radio_button("status", **opts))
        opts = dict(value="A", label="Active", checked=False)
        fieldset.append(page.radio_button("status", **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Process the requests and redraw the form."""

        # Make sure we have something to do.
        if not self.ids:
            self.alerts.append(dict(
                message="No document IDs entered.",
                type="warning",
            ))

        else:

            # Log the values.
            status = "Active" if self.status == "A" else "Blocked"
            self.logger.info(" session: %r", self.session)
            self.logger.info("    user: %r", self.session.user_name)
            self.logger.info("  status: %r", status)
            self.logger.info("  reason: %r", self.reason)

            # Walk through the documents.
            for id in self.ids:
                doc = Doc(self.session, id=id)
                try:
                    active_status = doc.active_status
                except Exception:
                    self.logger.exception(str(id))
                    self.alerts.append(dict(
                        message=f"CDR{id:010d} not found.",
                        type="error",
                    ))
                    continue
                if active_status != Doc.DELETED:
                    message = f"{doc.cdr_id} already restored."
                    self.logger.warning(message)
                    self.alerts.append(dict(message=message, type="warning"))
                    continue
                try:
                    doc.set_status(self.status, comment=self.reason)
                    message = f"{doc.cdr_id} restored successfully."
                    self.logger.warning(message)
                    self.alerts.append(dict(message=message, type="success"))
                    for error in doc.errors:
                        message = f"{doc.cdr_id}: {error}"
                        self.logger.warning(message)
                        self.alerts.append(dict(message=message, type="error"))
                except Exception as e:
                    self.logger.exception(doc.cdr_id)
                    self.alerts.append(dict(
                        message=f"{doc.cdr_id}: {e}",
                        type="error",
                    ))

        # In any case, redraw the form.
        self.show_form()

    @cached_property
    def ids(self):
        """CDR IDs of documents which are to be marked as restored."""

        ids = []
        for id in self.fields.getvalue("ids", "").split():
            try:
                ids.append(Doc.extract_id(id))
            except Exception:
                self.bail("Invalid document ID")
        return ids

    @cached_property
    def reason(self):
        """Explanation for the deletions."""
        return self.fields.getvalue("reason", self.REASON)

    @cached_property
    def same_window(self):
        """Limit the number of new browser tabs."""
        return [self.SUBMIT]

    @cached_property
    def status(self):
        """New status for the documents (Active or Inactive)."""

        status = self.fields.getvalue("status", "I")
        if status not in "IA":
            self.bail()
        return status


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
