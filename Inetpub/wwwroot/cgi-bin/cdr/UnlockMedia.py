#!/usr/bin/env python

"""Switch /cdr/akamai/media.lock to /cdr/akamai/media.
"""

import os
from cdrcgi import Controller
from cdrpub import Control as PubControl


class Control(Controller):
    """Top-level logic."""

    LOGNAME = "unlock-media"
    TO = PubControl.Media.MEDIA
    FROM = PubControl.Media.LOCK

    def populate_form(self, page):
        """Allow the user to override directory defaults.

        Pass:
            page - HTMLPage object on which we place the fields
        """

        if not self.session.can_do("USE PUBLISHING SYSTEM"):
            self.bail("Not authorized")
        fieldset = page.fieldset("Directories")
        fieldset.append(page.text_field("from", value=self.FROM))
        fieldset.append(page.text_field("to", value=self.TO))
        page.form.append(fieldset)

    def show_report(self):
        """Loop back to the form."""
        self.show_form()

    @property
    def new(self):
        """New name for the directory."""

        if not hasattr(self, "_new"):
            self._new = self.fields.getvalue("to")
        return self._new

    @property
    def old(self):
        """Current name for the directory."""

        if not hasattr(self, "_old"):
            self._old = self.fields.getvalue("from")
        return self._old

    @property
    def subtitle(self):
        """String displayed below the primary banner."""

        if not hasattr(self, "_subtitle"):
            self._subtitle = "Unlock media"
            if self.request == self.SUBMIT and self.old and self.new:
                try:
                    os.rename(self.old, self.new)
                except Exception as e:
                    self.bail(e)
                self._subtitle = "Media unlocked"
        return self._subtitle


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
