#!/usr/bin/env python

"""Main menu for advanced search forms.
"""

from cdrcgi import Controller
from cdr import isProdHost

class Control(Controller):
    SUBTITLE = "Developers/System Administrators"
    SUBMIT = None
    ON_PROD = isProdHost()
    def populate_form(self, page):
        page.body.set("class", "admin-menu")
        ol = page.B.OL()
        for display, script in (
            ("Batch Job Status", "getBatchStatus.py"),
            ("Clear FileSweeper Lock File", "clear-filesweeper-lockfile.py"),
            ("Delete CDR Documents", "del-some-docs.py"),
            ("Email Logged-in Users", "MessageLoggedInUsers.py"),
            ("Fetch Tier Settings", "fetch-tier-settings.py"),
            ("Global Changes", "GlobalChangeMenu.py"),
            ("Mailers", "Mailers.py"),
            ("Manage Actions", "EditActions.py"),
            ("Manage Configuration Files", "EditConfig.py"),
            ("Manage Control Values", "EditControlValues.py"),
            ("Manage Document Types", "EditDocTypes.py"),
            ("Manage Filter Sets", "EditFilterSets.py"),
            ("Manage Filters", "EditFilters.py"),
            ("Manage Glossary Servers", "glossary-servers.py"),
            ("Manage Groups", "EditGroups.py"),
            ("Manage Linking Tables", "EditLinkControl.py"),
            ("Manage Query Term Definitions", "EditQueryTermDefs.py"),
            ("Manage Scheduled Jobs", "Scheduler.py"),
            ("Manage Users", "EditUsers.py"),
            ("Manage Value Tables", "edit-value-table.py"),
            ("Publishing - Create Job", "Publishing.py"),
            ("Publishing - Fail Job", "FailBatchJob.py"),
            ("Re-Publishing", "Republish.py"),
            ("Replace CWD with Older Version", "ReplaceCWDwithVersion.py"),
            ("Reports", "Reports.py"),
            ("Schema - Post", "post-schema.py"),
            ("Schema - Show", "GetSchema.py"),
            ("Unblock Documents", "UnblockDoc.py"),
            ("Unlock Media", "UnlockMedia.py"),
            ("Update Mapping Table", "EditExternalMap.py"),
            ("Update ZIP Codes", "upload-zip-code-file.py"),
            ("View Logs", "log-tail.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))
        page.form.append(ol)
Control().run()
