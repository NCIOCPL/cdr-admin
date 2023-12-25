#!/usr/bin/env python

"""Display a submenu for the CDR translation job queues.
"""

from functools import cached_property
from cdrcgi import Controller


class Control(Controller):
    """Top-level processing control."""

    SUBTITLE = "Translation Job Queues"
    INSTRUCTIONS = (
        "There are multiple translation job queues for the CDR, "
        "each tracking active translation jobs and their statuses "
        "for one or more related document types. Tools are available "
        "for managing the status of each job, as well as for performing "
        "bulk operations on the individual queues. Links are provided "
        "below for the available queues."
    )
    QUEUES = (
        ("Glossary Translation Job Queue", "glossary-translation-jobs.py"),
        ("Media Translation Job Queue", "media-translation-jobs.py"),
        ("Summary Translation Job Queue", "translation-jobs.py"),
    )

    def populate_form(self, page):
        """Add the instructions and links to the page.

        Required positional argument:
            page - HTMLPage object on which we place the table
        """

        fieldset = page.fieldset("Instructions")
        fieldset.append(page.B.P(self.INSTRUCTIONS))
        page.form.append(fieldset)
        fieldset = page.fieldset("Available Queues")
        ul = page.B.UL(page.B.CLASS("usa-list usa-list--unstyled"))
        params = {}
        if self.testing:
            params["testing"] = True
        for label, url in self.QUEUES:
            link = page.menu_link(url, label, **params)
            link.set("target", "_blank")
            ul.append(page.B.LI(link))
        fieldset.append(ul)
        page.form.append(fieldset)
        page.add_css(
            ".usa-form a { text-decoration: none; }\n"
            "fieldset .usa-list--unstyled { margin-top: 1.5rem; }\n"
            "fieldset .usa-list li { padding-left: 3rem; }\n"
            f".usa-form a:visited {{ color: {page.LINK_COLOR}; }}\n"
        )

    @cached_property
    def buttons(self):
        """No buttons needed for this page."""
        return []

    @cached_property
    def testing(self):
        """Used by automated tests to avoid spamming the users."""
        return self.fields.getvalue("testing")


if __name__ == "__main__":
    """Don't run the script if loaded as a module."""
    Control().run()
