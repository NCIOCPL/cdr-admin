#!/usr/bin/env python

"""Main menu for advanced search forms.
"""

from cdrcgi import Controller, HTMLPage


class Control(Controller):
    """Override the base class with menu-generation  logic."""

    SUBTITLE = "Advanced Search"
    SUBMIT = None
    B = HTMLPage.B
    INSTRUCTIONS = (
        B.P(
            """\
This module allows you to search for documents of a specific type
using filtering criteria appropriate to that type. For example, the
search page for """,
            B.CODE("Term"),
            """ documents has fields for the term's primary name, other names
used for the term, the type of the term (for example, Drug Combination),
and/or its semantic type (for example, Disease/Diagnosis)."""
        ),
        B.P(
            """\
For some of the more comples document types (such as """,
            B.CODE("Summary"),
            """), creating the search form may take a few seconds, because
the page must assemble all of the valid values for the picklists."""
        ),
        B.P(
            """\
The search forms for some of the document types have extra buttons
specific to those document types. For example, the """,
            B.CODE("Term"),
            """ search form has a button which opens a new browser tab
for searching the NCI Thesaurus.
If the user account has sufficient permissions, the """,
            B.CODE("Citation"),
            """ form includes fields for importing or updating citations
from PubMed. There is an alternate form for """,
            B.CODE("Person"),
            """ documents, which includes location information about the
people matching the search criteria, to make it easier to distinguish
between individuals with the same name."""
        ),
        B.P(
            """\
For all document types, the display of the search results includes a
link to each matching document's QC report.
""")
    )
    DOCTYPES = (
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
    )
    CSS = """
.menu-links { list-style: none; }
.usa-form .menu-links a { text-decoration: none; }
.usa-form .menu-links a:visited { color: #005ea2 }
.usa-form .menu-links li { margin-bottom: .5rem; }
#primary-form .usa-accordion { margin-bottom: 2rem; }
code { color: brown; }
"""

    def populate_form(self, page):
        # page.body.set("class", "admin-menu")
        accordion = page.accordion("Instructions")
        for paragraph in self.INSTRUCTIONS:
            accordion.payload.append(paragraph)
        page.form.append(accordion.wrapper)
        fieldset = page.fieldset("Select a Document Type")
        ul = page.B.UL(page.B.CLASS("menu-links"))
        fieldset.append(ul)
        for display, script in (self.DOCTYPES):
            link = page.menu_link(script, display)
            link.set("target", "_blank")
            ul.append(page.B.LI(link))
        page.form.append(fieldset)
        page.add_css(self.CSS)


Control().run()
