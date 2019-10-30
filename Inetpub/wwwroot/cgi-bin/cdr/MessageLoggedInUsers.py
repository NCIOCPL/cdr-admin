#!/usr/bin/env python

"""Send a message to users currently logged in to the CDR.
"""

from cdrcgi import Controller
from cdr import EmailMessage


class Control(Controller):
    """Logic for the messaging utility."""

    SUBTITLE = "Send a Message to Logged-In CDR Users"
    LOGNAME = "MessageLoggedInUsers"
    CSS = (
        "fieldset {width: 700px; }",
        ".labeled-field input, .labeled-field textarea { width: 550px; }",
    )

    def build_tables(self):
        """Send the message and show the recipients."""

        # Make sure this action is allowed for the current user.
        if not self.session.can_do("EMAIL USERS"):
            bail("Current user not allowed to use this script")

        # Make sure we have everything we need for the message.
        if not self.message:
            self.show_form()

        # Remember what we do.
        args = self.subject, self.recipients
        self.logger.info("sending message %s to %s", *args)
        self.logger.info("message from: %s", self.email)
        self.logger.info("message body: %s", self.body)

        # Send the message, logging failures.
        try:
            self.message.send()
        except Exception as e:
            self.logger.exception("Send failure")
            self.bail(e)

        # Show who got the message.
        rows = [[recipient] for recipient in self.recipients]
        return self.Reporter.Table(rows, columns=["Message Recipients"])

    def populate_form(self, page):
        """Ask the user for the email message's values.

        Pass:
            page = HTMLPage object on which to show the fields
        """

        fieldset = page.fieldset("All fields are required")
        fieldset.append(page.text_field("email", value=self.user.email))
        fieldset.append(page.text_field("subject", value="CDR"))
        fieldset.append(page.textarea("body", rows=10))
        page.form.append(fieldset)
        page.add_css("\n".join(self.CSS))

    @property
    def body(self):
        """String for the email message's body."""
        return self.fields.getvalue("body")

    @property
    def email(self):
        """String for the email address from which the message will be sent."""
        return self.fields.getvalue("email")

    @property
    def message(self):
        """Email message ready for sending."""

        if not hasattr(self, "_message"):
            self._message = None
            if self.email and self.recipients and self.subject and self.body:
                opts = dict(subject=self.subject, body=self.body)
                args = self.email, self.recipients
                self._message = EmailMessage(*args, **opts)
        return self._message

    @property
    def recipients(self):
        """Email addresses of the currently logged-in users."""

        if not hasattr(self, "_recipients"):
            query = self.Query("session s", "u.email").unique()
            query.join("usr u", "u.id = s.usr")
            query.where("s.ended IS NULL")
            query.where("u.email IS NOT NULL")
            query.where("u.email LIKE '%@%'")
            rows = query.execute(self.cursor).fetchall()
            self._recipients = [row.email for row in rows]
        return self._recipients

    @property
    def subject(self):
        """String for the email message's subject header."""
        return self.fields.getvalue("subject", "CDR")

    @property
    def user(self):
        """Currently logged-on user, for the default sender address."""

        if not hasattr(self, "_user"):
            user = self.session.User(self.session, id=self.session.user_id)
            self._user = user
        return self._user


Control().run()
