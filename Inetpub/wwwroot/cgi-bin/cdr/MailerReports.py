#----------------------------------------------------------------------
# Submenu for mailer reports.
#
# BZIssue::4630
# BZIssue::1572
# BZIssue::5239 (JIRA::OCECDR-3543) - menu cleanup
# JIRA::OCECDR-3734
# JIRA::OCECDR-4092 - fix bug in link to GP Emailers List; use Control class
#----------------------------------------------------------------------

import cdrcgi

class Control(cdrcgi.Control):
    SUBMIT = "" # suppress this button
    def __init__(self):
        cdrcgi.Control.__init__(self, "Mailer Reports")
    def set_form_options(self, opts):
        opts["body_classes"] = "admin-menu"
        return opts
    def populate_form(self, form):
        form.add("<ol>")
        for script, display in (
            ("ocecdr-3734.py", "Bounced GP Emailers"),
            ("MailerActivityStatistics.py", "Mailer Activity Counts"),
            ("MailerCheckinReport.py", "Mailer Check-In Count"),
            ("MailerHistory.py", "Mailer History"),
            ("Request4275.py", "Mailers Received - Detailed")
        ):
            form.add_menu_link(script, display, self.session)
        form.add("</ol>")
Control().run()
