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
        opts = dict(DocType="Citation")
        link = page.menu_link("QcReport.py", "Citation QC Report", **opts)
        ol = page.B.OL(page.B.LI(link))
        page.form.append(ol)
        page.form.append(page.B.H3("Other Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script in (
            ("Advanced Citation Search", "CiteSearch.py"),
            ("Unverified Citations", "UnverifiedCitations.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))
        page.form.append(page.B.H3("Management Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script in (
            ("Citations Linked to Summaries", "CitationsInSummaries.py"),
            ("New Citations Report", "NewCitations.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))


Control().run()
