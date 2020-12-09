#!/usr/bin/env python

"""General reports menu.
"""

from cdrcgi import Controller

class Control(Controller):
    SUBTITLE = "General Reports"
    SUBMIT = None
    def populate_form(self, page):
        page.body.set("class", "admin-menu")
        ol = page.B.OL()
        for display, script in (
            ("Checked Out Documents", "CheckedOutDocs.py"),
            ("Checked Out Documents With No Activity", "InactivityReport.py"),
            ("Current Sessions", "ActiveLogins.py"),
            ("Database Tables/Columns", "db-tables.py"),
            ("Date Last Modified", "DateLastModified.py"),
            ("Document Activity Report", "ActivityReport.py"),
            ("Document Version History", "DocVersionHistory.py"),
            ("Documents Modified", "DocumentsModified.py"),
            ("External Map Failures Report", "ExternMapFailures.py"),
            ("Filter Document", "/CdrFilter.html"),
            ("Global Change Test Results", "ShowGlobalChangeTestResults.py"),
            ("Invalid Documents", "InvalidDocs.py"),
            ("Linked Documents", "LinkedDocs.py"),
            ("Linked Media Documents", "MediaLinks.py"),
            ("List of New Documents with Publication Status",
             "NewDocsWithPubStatus.py"),
            ("New Document Count", "NewDocReport.py"),
            ("Documents Modified Since Last Publishable Version",
             "ModWithoutPubVersion.py"),
            ("Show CDR Document XML", "ShowCdrDocument.py"),
            ("Show DIS Elements", "ShowDISIncludes.py"),
            ("Show Summary Elements", "ShowSummaryIncludes.py"),
            ("URL Check", "CheckUrls.py"),
            ("URL List Report", "UrlListReport.py"),
            ("Unchanged Documents", "UnchangedDocs.py"),
            ("Versions that Replaced CWDs", "ReplaceCWDReport.py"),
            ("XMetaL CDR Icons", "xmetal-icons.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))
        page.form.append(ol)
Control().run()
