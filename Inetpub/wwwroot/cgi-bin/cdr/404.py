#!/usr/bin/env python

from cdrcgi import Controller

class Control(Controller):
    """Create a 404 (page not found) error page."""

    SUBTITLE = "Not Found"
    MESSAGE = "The requested resource cannot be found."
    JIRA = "https://tracker.nci.nih.gov/projects/OCECDR/"

    def run(self):
        """Take over control of the page."""
        page = self.HTMLPage("CDR Administration", subtitle=self.SUBTITLE)
        page.form.append(
             page.B.P(
                "If the problem persists, please create a ",
                page.B.A("JIRA", href=self.JIRA),
                " ticket in the OCECDR project."
            )
        )
        parent = page.header.find("div")
        if parent is not None:
            nav = parent.find("nav")
            if nav is not None:
                parent.remove(nav)
        page.body.remove(page.footer)
        page.add_alert(self.MESSAGE, type="error")
        page.add_uswds_script()
        page.send()

if __name__ == "__main__":
    Control().run()
