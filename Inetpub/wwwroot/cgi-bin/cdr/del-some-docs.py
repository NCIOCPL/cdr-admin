#!/usr/bin/env python

"""Delete CDR documents.

The documents aren't actually deleted, but instead their active_status
column is set to 'D'.
"""

from functools import cached_property
from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):

    SUBTITLE = "CDR Document Deletion"
    LOGNAME = "del-some-docs"
    LEGEND = "Select Documents To Delete"
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
        opts = dict(label="Comment (optional)", value=self.reason)
        fieldset.append(page.textarea("reason", **opts))
        page.form.append(fieldset)
        fieldset = page.fieldset("Options")
        label = "Validate? (Please read the instructions above)"
        opts = dict(value="validate", label=label, checked=True)
        fieldset.append(page.checkbox("options", **opts))
        page.form.append(fieldset)

    def show_report(self):
        """Process the deletions and return to the form page."""

        if not self.ids:
            if not self.alerts:
                self.alerts.append(dict(
                    message="At least one document ID is required.",
                    type="error",
                ))
        else:
            self.logger.info(" session: %r", self.session)
            self.logger.info("    user: %r", self.session.user_name)
            self.logger.info("validate: %r", self.validate)
            self.logger.info("  reason: %r", self.reason)
            opts = dict(reason=self.reason, validate=self.validate)
            for id in self.ids:
                doc = Doc(self.session, id=id)
                cdr_id = doc.cdr_id
                if doc.active_status == Doc.DELETED:
                    self.alerts.append(dict(
                        message=f"{doc.cdr_id} has already been deleted.",
                        type="warning",
                    ))
                    continue
                try:
                    doc.delete(**opts)
                    self.logger.info("Deleted %s", doc.cdr_id)
                    self.alerts.append(dict(
                        message=f"{cdr_id} has been deleted successfully.",
                        type="success",
                    ))
                    for error in doc.errors:
                        self.alerts.append(dict(
                            message=f"{doc.cdr_id}: {error}.",
                            type="warning",
                        ))
                except Exception as e:
                    self.logger.exception(cdr_id)
                    self.alerts.append(dict(
                        message=f"Failure deleting {doc.cdr_id}: {e}",
                        type="error",
                    ))
        self.show_form()

    @cached_property
    def same_window(self):
        """No need to open new browser tabs for this tool."""
        return [self.SUBMIT]

    @cached_property
    def ids(self):
        """CDR IDs of documents which are to be marked as deleted."""

        ids = []
        invalid = []
        for id in self.fields.getvalue("ids", "").split():
            try:
                ids.append(Doc.extract_id(id))
            except Exception:
                invalid.append(id)
        if invalid:
            for id in invalid:
                self.alerts.append(dict(
                    message=f"Invalid CDR id {id!r}.",
                    type="warning",
                ))
            self.alerts.append(dict(
                message="No deletions performed.",
                type="warning",
            ))
            return []
        return ids

    @cached_property
    def reason(self):
        """Explanation for the deletions."""
        return self.fields.getvalue("reason", self.REASON)

    @cached_property
    def validate(self):
        """Whether deletions should be blocked for docs that are linked."""
        return "validate" in self.fields.getlist("options")


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
