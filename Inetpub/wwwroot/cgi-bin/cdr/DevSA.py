"""
Main menu for Developers and System Administrators.
BZIssue::5296
"""

import cgi
import os
import sys
import cdr
import cdrcgi

class Control:

    TITLE = "CDR Administration"
    SECTION = "Developers/System Administrators"
    MENU_USERS = "Developer/SysAdmin Menu Users"
    SET_NEXT_JOB_ID = "SetNextJobId.py"
    LOG_OUT = "Log Out"

    def __init__(self):
        fields  = cgi.FieldStorage()
        self.session = cdrcgi.getSession(fields)
        self.request = cdrcgi.getRequest(fields)
        self.buttons = cdrcgi.MAINMENU, self.LOG_OUT
        if not cdr.member_of_group(self.session, self.MENU_USERS):
            cdrcgi.bail("User not authorized for this menu")

    def run(self):
        try:
            if self.request == cdrcgi.MAINMENU:
                cdrcgi.navigateTo("Admin.py", self.session)
            elif self.request == self.LOG_OUT:
                cdrcgi.logout(self.session)
            else:
                self.show_menu()
        except Exception as e:
            cdrcgi.bail(e)

    def show_menu(self):
        opts = dict(
            subtitle=self.SECTION,
            body_classes="admin-menu",
            buttons=self.buttons,
            action=os.path.basename(sys.argv[0]),
            session=self.session,
        )
        page = cdrcgi.Page(self.TITLE, **opts)
        page.add("<ol>")
        for title, script in (
            ("Batch Job Status", "getBatchStatus.py"),
            ("Clear FileSweeper Lock File", "clear-filesweeper-lockfile.py"),
            ("Delete CDR Documents", "del-some-docs.py"),
            ("Email Logged-in Users", "MessageLoggedInUsers.py"),
            ("Fetch Tier Settings", "fetch-tier-settings.py"),
            ("Global Changes", "GlobalChangeMenu.py"),
            ("Mailers", "Mailers.py"),
            ("Manage Actions", "EditActions.py"),
            ("Manage Control Values", "set-ctl-value.py"),
            ("Manage Document Types", "EditDocTypes.py"),
            ("Manage Filter Sets", "EditFilterSets.py"),
            ("Manage Filters", "EditFilters.py"),
            ("Manage Glossary Servers", "glossary-servers.py"),
            ("Manage Groups", "EditGroups.py"),
            ("Manage Linking Tables", "EditLinkControl.py"),
            ("Manage Query Term Definitions", "EditQueryTermDefs.py"),
            ("Manage Users", "EditUsers.py"),
            ("Manage Value Tables", "edit-value-table.py"),
            ("Publishing - Create Job", "Publishing.py"),
            ("Publishing - Fail Job", "FailBatchJob.py"),
            ("Publishing - Reverify Push Job", "ReverifyJob.py"),
            ("Publishing - Set Next Job ID", self.SET_NEXT_JOB_ID),
            ("Re-Publishing", "Republish.py"),
            ("Replace CWD with Older Version", "ReplaceCWDwithVersion.py"),
            ("Reports", "Reports.py"),
            ("Scheduled Jobs", "../scheduler/"),
            ("Schema - Post", "post-schema.py"),
            ("Schema - Show", "GetSchema.py"),
            ("Unblock Documents", "UnblockDoc.py"),
            ("Update Mapping Table", "EditExternMap.py"),
            ("Update ZIP Codes", "upload-zip-code-file.py"),
            ("View Logs", "log-tail.py"),
        ):
            if not cdr.isProdHost() or script != self.SET_NEXT_JOB_ID:
                page.add_menu_link(script, title, self.session)
        page.add("</ol>")
        page.send()

Control().run()
