#!/usr/bin/env python

"""Reports menu.
"""

from cdrcgi import Controller

class Control(Controller):

    SUBTITLE = "Reports"
    SUBMIT = None

    @property
    def buttons(self):
        """Override to omit the button for this page."""
        return self.DEVMENU, self.ADMINMENU, self.LOG_OUT

    def populate_form(self, page):
        page.body.set("class", "admin-menu")
        ol = page.B.OL()
        page.form.append(ol)
        for display, script in (
            ("Citations", "CitationReports.py"),
            ("Documentation", "CdrDocumentation.py"),
            ("Drug Information", "DrugInfoReports.py"),
            ("General Reports", "GeneralReports.py"),
            ("Geographic", "GeographicReports.py"),
            ("Glossary Terms", "GlossaryTermReports.py"),
            ("Media", "MediaReports.py"),
            ("Persons and Organizations", "PersonAndOrgReports.py"),
            ("Publishing", "PublishReports.py"),
            ("Summaries and Miscellaneous Documents",
             "SummaryAndMiscReports.py"),
            ("Terminology", "TerminologyReports.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))

Control().run()
