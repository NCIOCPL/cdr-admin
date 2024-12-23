#!/usr/bin/env python

from cdrcgi import Controller


class Control(Controller):
    """Create a 404 (page not found) error page."""

    SUBTITLE = "Not Found"
    MESSAGE = "The requested resource cannot be found."
    JIRA = "https://tracker.nci.nih.gov/projects/OCECDR/"
    BODY = "If the problem persists, please file a JIRA ticket."

    def run(self):
        """Take over control of the page."""

        page = self.HTMLPage("CDR Administration", subtitle=self.SUBTITLE)
        page.form.append(page.B.P(self.BODY))
        parent = page.header.find("div")
        if parent is not None:
            nav = parent.find("nav")
            if nav is not None:
                parent.remove(nav)
        parent = page.header.find("div/div/div/em")
        if parent is not None:
            link = parent.find("a")
            if link is not None:
                parent.remove(link)
                parent.text = "CDR Administration"
        parent = page.header.find("div/div/div")
        if parent is not None:
            button = parent.find("button")
            if button is not None:
                parent.remove(button)
        page.body.remove(page.footer)
        page.add_alert(self.MESSAGE, type="error")
        page.send()


if __name__ == "__main__":
    Control().run()
