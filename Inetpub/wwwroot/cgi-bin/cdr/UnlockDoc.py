#!/usr/bin/env python

"""Unlock one or more CDR documents.
"""

from functools import cached_property
from cdrapi.docs import Doc
from cdrcgi import Controller
from cdr import unlock


class Control(Controller):

    SUBTITLE = "Unlock Documents"
    LOGNAME = "unlock-docs"

    def populate_form(self, page):
        """Add the fields to the form.

        Pass:
            page - HTMLPage object where we communicate with the user.
        """

        session = self.tier_session
        tier = self.cdr_tier
        reason = self.reason
        fieldset = page.fieldset("Options")
        opts = dict(label="Doc IDs", tooltip="Separated by spaces")
        fieldset.append(page.text_field("ids", **opts))
        fieldset.append(page.text_field("cdr_tier", value=tier, label="Tier"))
        opts = dict(value=session, tooltip="Only needed if tier specified")
        fieldset.append(page.text_field("tier_session", **opts))
        fieldset.append(page.text_field("reason", value=reason))
        page.form.append(fieldset)

    def show_report(self):
        """Handle the request and circle back to the form."""

        if not self.ids:
            message = "At least one document ID is required."
            self.alerts.append(dict(message=message, type="error"))
        else:
            opts = dict(reason=self.reason)
            if self.cdr_tier:
                if not self.tier_session:
                    message = f"Session for {self.cdr_tier} tier missing."
                    self.alerts.append(dict(message=message, type="error"))
                else:
                    session = self.tier_session
                    opts["tier"] = self.cdr_tier.upper()
            else:
                session = self.session
        if not self.alerts:
            for id in self.ids:
                doc = Doc(session, id=id)
                try:
                    doctype = doc.doctype.name
                except Exception:
                    message = f"Document {id} not found."
                    self.alerts.append(dict(message=message, type="warning"))
                    continue
                if not doc.lock:
                    message = f"CDR{doc.id} is not locked."
                    self.alerts.append(dict(message=message, type="warning"))
                    continue
                try:
                    unlock(session, id, **opts)
                    message = f"Successfully unlocked {doctype} doc CDR{id}."
                    self.alerts.append(dict(message=message, type="success"))
                except Exception as e:
                    message = f"Failure unlocking CDR{id}: {e}"
                    self.alerts.append(dict(message=message, type="error"))
        self.show_form()

    @cached_property
    def ids(self):
        """IDs of the documents to be unlocked."""
        return self.fields.getvalue("ids", "").strip().split()

    @cached_property
    def cdr_tier(self):
        """Optional name for a CDR tier if not for this server's tier."""
        return self.fields.getvalue("cdr_tier")

    @cached_property
    def reason(self):
        """Optional comment for the unlock action(s)."""
        return self.fields.getvalue("reason")

    @cached_property
    def same_window(self):
        """Stay on the same browser tab."""
        return [self.SUBMIT]

    @cached_property
    def tier_session(self):
        """Session ID string if the request is for another tier."""
        return self.fields.getvalue("tier_session")


if __name__ == "__main__":
    """Don't execute if loaded as a module."""
    Control().run()
