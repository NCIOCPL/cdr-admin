#!/usr/bin/env python

"""Stub for report which hasn't been implemented yet.
"""

from cdrcgi import Controller

class Control(Controller):
    SUBTITLE = "Reports"
    SUBMIT = None
    INSTRUCTIONS = (
        "This report has not yet been implemented, either because we don't "
        "yet have the specs, or because it's behind higher-priority tasks "
        "in the development task queue."
    )
    def populate_form(self, page):
        fieldset = page.fieldset()
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)


if __name__ == "__main__":
    """Don't run the script if invoked as a module."""
    Control().run()
