#!/usr/bin/env python

"""Submenu for citation reports.
"""

from cdrcgi import Controller

class Control(Controller):

    SUBMIT = None
    SUBTITLE = "Citation Reports"

    def populate_form(self, page):
        """Add the menu items for Citations."""
        page.body.set("class", "admin-menu")
        page.form.append(page.B.H3("QC Reports"))
        link = page.menu_link("CiteSearch.py", "Citation QC Report")
        ol = page.B.OL(page.B.LI(link))
        page.form.append(ol)
        page.form.append(page.B.H3("Other Reports"))
        link = page.menu_link("UnverifiedCitations.py", "Unverified Citations")
        ol = page.B.OL(page.B.LI(link))
        page.form.append(ol)
        page.form.append(page.B.H3("Management Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script in (
            ("Citations Linked to Summaries", "CitationsInSummaries.py"),
            ("New Citations Report", "NewCitations.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))


Control().run()
