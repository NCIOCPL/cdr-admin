#!/usr/bin/env python
"""Determine whether an account is allowed to perform a CDR action.

Originally for OCECDR-4107 (Require authorization for viewing GP emailer list),
but the CDR no longer supports genetics professional information, so this
has been re-purposed for the automated testing of the CDR permissions system.
"""

from functools import cached_property
from cdrcgi import Controller


class Control(Controller):

    LOGNAME = "check-auth"

    def run(self):
        """Overridden because this is not a standard report."""
        return self.send_page(self.answer, text_type="plain")

    @cached_property
    def account(self):
        """User object for the account in question."""

        opts = dict(name=self.fields.getvalue("account"))
        return self.session.User(self.session, **opts)

    @cached_property
    def action(self):
        """The name of the action the account wants to perform."""
        return self.fields.getvalue("action")

    @cached_property
    def answer(self):
        """Y if the account is allowed to perform the action, else 'N'."""

        allowed = self.account.can_do(self.action, doctype=self.doctype)
        return "Y" if allowed else False

    @cached_property
    def doctype(self):
        """Optional string for a specific document type."""
        return self.fields.getvalue("doctype")


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""

    control = Control()
    try:
        control.run()
    except Exception:
        control.logger.exception("Failure checking auhorization")
        control.send_page("N", text_type="plain")
