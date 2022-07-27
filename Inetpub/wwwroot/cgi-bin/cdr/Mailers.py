#!/usr/bin/env python

"""Mailer job reports menu.
"""

from cdrcgi import Controller


class Control(Controller):
    SUBTITLE = "Mailers"
    SUBMIT = None

    def populate_form(self, page):
        page.body.set("class", "admin-menu")
        ol = page.B.OL()
        for display, script, params in (
            ("SummaryMailers (Advisory Board)",
             "SummaryMailerReqForm.py", dict(BoardType="Advisory")),
            ("PDQ\xae Board Member Correspondence Mailers",
             "BoardMemberMailerReqForm.py", {}),
        ):
            ol.append(page.B.LI(page.menu_link(script, display, **params)))
        page.form.append(ol)


Control().run()
