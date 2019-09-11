#----------------------------------------------------------------------
# Submenu for terminology reports.
#
# BZIssue::4653 CTRO Access to CDR Admin Interface
# BZIssue::4698 Genetics Directory Menu Information
# JIRA::OCECDR-3987
#----------------------------------------------------------------------
import cdr
import cdrcgi
from cdrapi.users import Session

class Control(cdrcgi.Control):
    def __init__(self):
        cdrcgi.Control.__init__(self, "Terminology Reports")
        self.buttons = (self.REPORTS_MENU, self.ADMINMENU, self.LOG_OUT)
    def set_form_options(self, opts):
        opts["body_classes"] = "admin-menu"
        return opts
    def populate_form(self, form):
        form.add(form.B.H3("QC Reports"))
        form.add("<ol>")
        for script, display in (
            ("TermUsage.py", "Term Usage"),
            ("TermSearch.py", "Terminology QC Report")
        ):
            form.add_menu_link(script, display, self.session)
        form.add("</ol>")
        form.add(form.B.H3("Other Reports"))
        form.add("<ol>")
        for script, display, args in (
            ("DiseaseDiagnosisTerms.py", "Cancer Diagnosis Hierarchy", {}),
            ("DiseaseDiagnosisTerms.py",
             "Cancer Diagnosis Hierarchy (Without Alternate Names)",
             { "flavor": "short" }),
            ("RecentCTGovProtocols.py",
             "Clinical Trials Drug Analysis Report", {}),
            ("DrugAgentReport.py", "Drug/Agent Report", {}),
            ("DrugReviewReport.py", "Drug Review Report", {}),
            ("GeneticConditionMenuMappingReport.py",
             "Genetics Directory Menu Report", {}),
            ("InterventionAndProcedureTerms.py",
             "Intervention or Procedure Terms",
             { "IncludeAlternateNames": "True" }),
            ("InterventionAndProcedureTerms.py",
             "Intervention or Procedure Terms (without Alternate Names)",
             { "IncludeAlternateNames": "False" }),
            ("MenuHierarchy.py", "Menu Hierarchy Report", {}),
            ("SemanticTypeReport.py", "Semantic Type Report", {}),
            ("Stub.py", "Term By Type", {}),
            ("TermHierarchyTree.py", "Term Hierarchy Tree", {}),
            ("TermHierarchyTree.py",
             "Terms with No Parent Term and Not a Semantic Type",
             { "SemanticTerms": "False" }),
            ("ocecdr-3588.py", "Thesaurus Concepts Not Marked Public", {}),
        ):
            form.add_menu_link(script, display, self.session, **args)
        form.add("</ol>")
    def guest_user(self):
        name = Session(self.session).user_name
        user = cdr.getUser(self.session, name)
        return 'GUEST' in user.groups and len(user.groups) < 2
Control().run()
