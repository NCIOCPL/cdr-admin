#!/usr/bin/env python

"""Person and Organization report menu.
"""

from cdrcgi import Controller

class Control(Controller):

    SUBTITLE = "Person and Organization Reports"
    SUBMIT = None
    QC_PARMS = dict(DocType="Media", ReportType="img")

    def populate_form(self, page):
        page.body.set("class", "admin-menu")
        page.form.append(page.B.H3("QC Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script in (
            ("Organization QC Report", "OrgSearch2.py"),
            ("Person QC Report", "PersonSearch.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))

Control().run()
