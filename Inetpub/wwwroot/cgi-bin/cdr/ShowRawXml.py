#!/usr/bin/env python

"""Show unformatted XML.
"""

from cdrcgi import Controller
from cdrapi.docs import Doc


class Control(Controller):
    """Script logic."""

    LOGNAME = "ShowRawXml"
    SUBMIT = None

    def run(self):
        """Override the base class version: no menu and no tables."""

        if not self.request:
            try:
                self.show_report()
            except Exception as e:
                self.logger.exception("Report failed")
                self.bail(e)
        else:
            Controller.run(self)

    def show_report(self):
        """Override, because this is not a tabular report."""

        self.report.page.form.append(self.HTMLPage.B.PRE(self.doc.xml))
        self.report.send()

    @property
    def doc(self):
        """The CDR document to display."""

        if not hasattr(self, "_doc"):
            id = self.fields.getvalue("id") or self.bail("No ID")
            self._doc = Doc(self.session, id=id)
        return self._doc

    @property
    def footer(self):
        """Suppress the footer."""
        return None

    @property
    def no_results(self):
        """Suppress the message we'd get with no tables."""
        return None

    @property
    def subtitle(self):
        """String to be displayed under the main banner."""
        return f"CDR Document {self.doc.id}"


if __name__ == "__main__":
    """Don't execute the script if loaded as a module."""
    Control().run()
