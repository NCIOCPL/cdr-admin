#!/usr/bin/env python

"""Geographic reports menu.
"""

from cdrcgi import Controller

class Control(Controller):
    SUBTITLE = "Geographic Reports"
    SUBMIT = None
    def populate_form(self, page):
        page.body.set("class", "admin-menu")
        ol = page.B.OL()
        for display, script in (
            ("Country QC Report", "CountrySearch.py"),
            ("Political Subunit QC Report", "PoliticalSubUnitSearch.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))
        page.form.append(ol)
Control().run()
