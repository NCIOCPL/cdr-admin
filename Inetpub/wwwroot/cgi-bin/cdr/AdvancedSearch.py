#!/usr/bin/env python

"""Main menu for advanced search forms.
"""

from cdrcgi import Controller


class Control(Controller):
    SUBTITLE = "Advanced Search"
    SUBMIT = None

    def populate_form(self, page):
        page.body.set("class", "admin-menu")
        page.form.append(page.B.H3("Document Type"))
        ol = page.B.OL()
        for display, script in (
            ("Citation", "CiteSearch.py"),
            ("Country", "CountrySearch.py"),
            ("Documentation", "HelpSearch.py"),
            ("Drug Information Summary", "DISSearch.py"),
            ("Glossary Term Concept", "GlossaryTermConceptSearch.py"),
            ("Glossary Term Name", "GlossaryTermNameSearch.py"),
            ("Media", "MediaSearch.py"),
            ("Miscellaneous", "MiscSearch.py"),
            ("Organization", "OrgSearch2.py"),
            ("Person", "PersonSearch.py"),
            ("Person (Locations in Result Display)", "PersonLocSearch.py"),
            ("Political SubUnit", "PoliticalSubUnitSearch.py"),
            ("Summary", "SummarySearch.py"),
            ("Term", "TermSearch.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))
        page.form.append(ol)


Control().run()
