#!/usr/bin/env python

"""Switch /cdr/akamai/media.lock to /cdr/akamai/media.
"""

from functools import cached_property
from pathlib import Path
from cdrcgi import Controller
from cdrpub import Control as PubControl


class Control(Controller):
    """Top-level logic."""

    SUBTITLE = "Unlock Media"
    LOGNAME = "unlock-media"
    TO = PubControl.Media.MEDIA
    FROM = PubControl.Media.LOCK
    INSTRUCTIONS = (
        "Media documents published from the CDR are stored on servers "
        "at Akamai. The process involves queuing the media files and "
        "then running rsync to push changes to the Akamai CDN. In order "
        "to prevent two simultaneous jobs from inadvertently trying to "
        "prepare the media files for synchronization, the software "
        "renames the directory in which the media files are stored, "
        f"as {FROM}, effectively locking the job against subsequent attempts "
        "to run another instance while the first is in process. If the "
        "software is interrupted (for example, by server or network "
        "failures), the lock can be left in place, effectively preventing "
        "subsequent jobs from publishing media files to Akamai. This "
        "utility removes the lock by renaming the directory back to "
        f"its canonical location, which on this server is ({TO}). You "
        "normally won't need to adjust the values in the From and To "
        "fields below, but they can be used for development or testing."
    )

    def populate_form(self, page):
        """Allow the user to override directory defaults.

        Pass:
            page - HTMLPage object on which we place the fields
        """

        if not self.session.can_do("USE PUBLISHING SYSTEM"):
            self.bail("Not authorized")
        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)
        fieldset = page.fieldset("Directories")
        default = self.old or self.FROM
        fieldset.append(page.text_field("from", value=default))
        default = self.new or self.TO
        fieldset.append(page.text_field("to", value=default))
        page.form.append(fieldset)

    def show_report(self):
        """Handle the request and loop back to the form."""

        if not self.old:
            message = "The From field is required."
            self.alerts.append(dict(message=message, type="error"))
        else:
            old = Path(self.old)
            if not old.exists():
                message = f"Path {old} not found"
                self.alerts.append(dict(message=message, type="error"))
        if not self.new:
            message = "The To field is required."
            self.alerts.append(dict(message=message, type="error"))
        else:
            new = Path(self.new)
            if new.exists():
                message = f"Path {new} already exists."
                self.alerts.append(dict(message=message, type="error"))
        if not self.alerts:
            try:
                old.rename(new)
                message = "Media successfully unlocked."
                self.alerts.append(dict(message=message, type="success"))
            except Exception as e:
                message = f"Directory rename failed: {e}"
                self.alerts.append(dict(message=message, type="error"))
        self.show_form()

    @cached_property
    def new(self):
        """New name for the directory."""
        return self.fields.getvalue("to")

    @cached_property
    def old(self):
        """Current name for the directory."""
        return self.fields.getvalue("from")

    @cached_property
    def same_window(self):
        """Stay in the same browser tab."""
        return [self.SUBMIT]


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
