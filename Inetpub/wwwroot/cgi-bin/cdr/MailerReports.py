#!/usr/bin/env python

"""Mailer report menu.
"""

from cdrcgi import Controller

class Control(Controller):

    SUBTITLE = "Mailer Reports"
    SUBMIT = None

    def populate_form(self, page):
        page.body.set("class", "admin-menu")
        ol = page.B.OL()
        page.form.append(ol)
        for display, script in (
            ("Mailer Activity Counts", "MailerActivityStatistics.py"),
            ("Mailer Check-In Count", "MailerCheckinReport.py"),
            ("Mailer History", "MailerHistory.py"),
            ("Mailers Received - Detailed", "Request4275.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))


Control().run()
