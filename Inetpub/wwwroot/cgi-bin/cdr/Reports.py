#----------------------------------------------------------------------
#
# $Id$
#
# Reports submenu for CDR administrative system.
#
#----------------------------------------------------------------------
import cdrcgi

class Control(cdrcgi.Control):
    def __init__(self):
        cdrcgi.Control.__init__(self, "Reports")
        self.buttons = (cdrcgi.MAINMENU, "Log Out")
    def set_form_options(self, opts):
        opts["body_classes"] = "admin-menu"
        return opts
    def populate_form(self, form):
        form.add("<ol>")
        for script, display in (
            ("GeneralReports.py", "General Reports"),
            ("CitationReports.py", "Citations"),
            ("CdrDocumentation.py", "Documentation"),
            ("DrugInfoReports.py", "Drug Information"),
            ("GeographicReports.py", "Geographic"),
            ("GlossaryTermReports.py", "Glossary Terms"),
            ("MailerReports.py", "Mailers"),
            ("MediaReports.py", "Media"),
            ("PublishReports.py", "Publishing"),
            ("PersonAndOrgReports.py", "Persons and Organizations"),
            ("ProtocolReports.py", "Protocols"),
            ("SummaryAndMiscReports.py",
             "Summaries and Miscellaneous Documents"),
            ("TerminologyReports.py",  "Terminology")
        ):
            form.add_menu_link(script, display, self.session)
        form.add("</ol>")
Control().run()
