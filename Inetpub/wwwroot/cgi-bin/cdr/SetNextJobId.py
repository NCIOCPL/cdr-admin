#!/usr/bin/env python
"""Adjust the next job ID.

When the WCMS/Gatekeeper database gets refreshed from PROD the ID
created as the next Job-ID on the lower tiers has likely already been
used.  As a result the CDR publishing jobs can't be verified
anymore against the GK database.

Example:
On DEV the latest Job-ID is 1000, the PROD Job-ID is 1500. When the
database for gatekeeper is updated the PROD Job-ID becomes the latest
GK Job-ID.  The CDR sends a new publishing job with the next Job-ID
1002.  At this point *two* jobs exist in the GK DB, the job 1002
submitted in PROD *and* the job 1002 submitted from DEV.
Trying to verify the DEV job will fail and therefore every successively
submitted publishing jobs will fail as well.
In this case we can reset the Job-ID value on DEV to the highest
value found on PROD.
"""

from cdrcgi import Controller


class Control(Controller):
    """Access to the database and form-building tools."""

    SUBTITLE = "Setting Next Job-ID (reseeding pub_proc)"
    INSTRUCTIONS = (
        "This program can be used to change the value which will be "
        "assigned as the ID for the next publishing job. "
        "That ID will be one number higher than the number you enter "
        "as the new 'current' ID. In other words, if you enter 5000 in "
        "the New ID field, the next job will be assigned the ID 5001."
        "This tool is only needed on the lower tiers."
    )

    def populate_form(self, page):
        """Ask the user for the information we need.

        Pass:
            page - HTMLPage object on which the CGI form is drawn
        """

        if self.session.tier.name == "PROD":
            self.bail("Only use this tool on the lower tiers.")
        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)
        fieldset = page.fieldset("Enter New Job ID")
        opts = dict(label="Last ID", disabled=True, value=self.last)
        fieldset.append(page.text_field("last", **opts))
        opts = dict(label="Current ID", disabled=True, value=self.current)
        fieldset.append(page.text_field("current", **opts))
        fieldset.append(page.text_field("new", label="New ID"))
        page.form.append(fieldset)

    def show_report(self):
        """Override because we're not showing a tabular report."""

        if self.session.tier.name == "PROD":
            self.bail("Only use this tool on the lower tiers.")
        if not self.session.can_do("SET_SYS_VALUE"):
            self.bail("Action not allowed for this account")
        if not self.new_id:
            self.bail("No new job ID provided.")
        if self.new_id <= self.current:
            self.bail("New job ID must be greater than the current ID")
        self.cursor.execute("{CALL cdr_set_next_job_ID (?)}", self.new_id)
        self.conn.commit()
        self.subtitle = f"Job ID successfully set to {self.new_id:d}"
        self.show_form()

    @property
    def current(self):
        """What the database plans to use for the next ID."""

        self.cursor.execute("SELECT IDENT_CURRENT('pub_proc') AS current_id")
        return self.cursor.fetchone().current_id

    @property
    def last(self):
        """Integer for the last job ID."""

        query = self.Query("pub_proc", "MAX(id) AS id")
        return query.execute(self.cursor).fetchone().id

    @property
    def new_id(self):
        """Value to which we set the next publishing job ID."""

        if not hasattr(self, "_new_id"):
            self._new_id = self.fields.getvalue("new")
            if self._new_id:
                try:
                    self._new_id = int(self._new_id)
                except:
                    self.bail("Invalid job ID")
        return self._new_id

    @property
    def subtitle(self):
        """String displayed immediately below the main banner."""

        if not hasattr(self, "_subtitle"):
            self._subtitle = self.SUBTITLE
        return self._subtitle

    @subtitle.setter
    def subtitle(self, value):
        """Allow the string to be modified to reflect the new value.

        Pass:
            value - new string to be displayed
        """

        self._subtitle = value


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
