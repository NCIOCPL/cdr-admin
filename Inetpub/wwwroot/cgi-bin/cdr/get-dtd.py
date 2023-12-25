#!/usr/bin/env python
"""Get a DTD from the server's file system.
"""

from functools import cached_property
from pathlib import Path
from cdrcgi import Controller
from cdr import PDQDTDPATH


class Control(Controller):
    """Derived class for the specific page."""

    LOGNAME = "get-dtd"
    DTDS = {"pdq.dtd", "pdqCG.dtd"}
    DEFAULT = "pdq.dtd"

    def run(self):
        """Overriddent because this is not a standard report."""

        path = Path(PDQDTDPATH) / self.dtd
        dtd = path.read_text()
        control.send_page(dtd, text_type="plain")

    @cached_property
    def dtd(self):
        """Either pdp.dtd (the default) or pdqCG.dtd"""

        dtd = self.fields.getvalue("dtd", self.DEFAULT)
        return self.bail() if dtd not in self.DTDS else dtd


if __name__ == "__main__":
    """Only execute if invoked directly, not imported as a module."""

    control = Control()
    try:
        control.run()
    except Exception as e:
        control.logger.exception("failure getting dtd")
        control.send_page(f"Failure fetching dtd: {e}", text_type="plain")
