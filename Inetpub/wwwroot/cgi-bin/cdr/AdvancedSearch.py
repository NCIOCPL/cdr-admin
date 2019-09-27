#----------------------------------------------------------------------
# Main menu for advanced search forms.
#----------------------------------------------------------------------
import cdrcgi

class Control(cdrcgi.Control):
    def __init__(self):
        cdrcgi.Control.__init__(self, "Advanced Search")
        self.buttons = (self.REPORTS_MENU, self.ADMINMENU, self.LOG_OUT)
    def set_form_options(self, opts):
        opts["body_classes"] = "admin-menu"
        return opts
    def populate_form(self, form):
        form.add(form.B.H3("Document Type"))
        form.add("<ol>")
        for script, display in (
            ("CiteSearch.py", "Citation"),
            ("CountrySearch.py", "Country"),
            ("DISSearch.py", "Drug Information Summary"),
            ("HelpSearch.py", "Documentation"),
            ("GlossaryTermConceptSearch.py", "Glossary Term Concept"),
            ("GlossaryTermNameSearch.py", "Glossary Term Name"),
            ("MiscSearch.py", "Miscellaneous"),
            ("MediaSearch.py", "Media"),
            ("OrgSearch2.py", "Organization"),
            ("PersonSearch.py", "Person"),
            ("PersonLocSearch.py", "Person (Locations in Result Display)"),
            ("PoliticalSubUnitSearch.py", "Political SubUnit"),
            ("SummarySearch.py", "Summary"),
            ("TermSearch.py", "Term")
        ):
            form.add_menu_link(script, display, self.session)
        form.add("</ol>")
Control().run()
