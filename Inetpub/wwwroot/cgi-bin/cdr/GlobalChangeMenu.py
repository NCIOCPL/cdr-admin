#!/usr/bin/env python

"""Global change reports menu.
"""

from cdrcgi import Controller

class Control(Controller):
    SUBTITLE = "Global Change Menu"
    SUBMIT = None
    def populate_form(self, page):
        page.body.set("class", "admin-menu")
        ol = page.B.OL()
        for display, script in (
            ("Global Change Test Results", "ShowGlobalChangeTestResults.py"),
            ("Log Out", "Logout.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))
        page.form.append(ol)
Control().run()
