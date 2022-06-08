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
        """Redirect back to form."""
        self.show_form()

    @cached_property
    def ids(self):
        """IDs of the documents to be unlocked."""

        ids = self.fields.getvalue("ids", "").split()
        if not ids:
            return []
        try:
            return [Doc.extract_id(id) for id in ids]
        except Exception:
            self.bail("not CDR IDs")

    @cached_property
    def tier_session(self):
        """Session ID string if the request is for another tier."""
        return self.fields.getvalue("tier_session")

    @cached_property
    def cdr_tier(self):
        """Optional name for a CDR tier if not for this server's tier."""
        return self.fields.getvalue("cdr_tier")

    @cached_property
    def reason(self):
        """Optional comment for the unlock action(s)."""
        return self.fields.getvalue("reason")

    @cached_property
    def subtitle(self):
        """This is where we actually handle the unlock requests."""

        if self.request == "Submit" and self.ids:
            opts = dict(reason=self.reason)
            if self.cdr_tier:
                if not self.tier_session:
                    self.bail("no session for tier")
                session = self.tier_session
                opts["tier"] = self.cdr_tier.upper()
            else:
                session = self.session
            for id in self.ids:
                try:
                    unlock(session, id, **opts)
                except Exception as e:
                    self.bail(f"{id}: {e}")
            return f"Unlocked {len(self.ids)} document(s)"
        return "Unlock documents"


if __name__ == "__main__":
    """Don't execute if loaded as a module."""
    Control().run()
