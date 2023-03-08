#!/usr/bin/env python

"""Terminology report menu.
"""

from cdrcgi import Controller


class Control(Controller):

    SUBTITLE = "Terminology Reports"
    SUBMIT = None

    def populate_form(self, page):
        page.body.set("class", "admin-menu")
        page.form.append(page.B.H3("QC Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script in (
            ("Term Usage", "TermUsage.py"),
            ("Terminology QC Report", "TermSearch.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))
        page.form.append(page.B.H3("Other Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for item in (
            ("Cancer Diagnosis Hierarchy", "DiseaseDiagnosisTerms.py"),
            ("Cancer Diagnosis Hierarchy (Without Alternate Names)",
             "DiseaseDiagnosisTerms.py", dict(flavor="short")),
            ("Clinical Trials Drug Analysis Report",
             "RecentCTGovProtocols.py"),
            ("Drug Review Report", "DrugReviewReport.py"),
            ("Drug Terms Eligible For Refresh From the EVS",
             "RefreshDrugTermsFromEVS.py"),
            ("EVS Concepts Used By Multiple CDR Drug Term Documents",
             "AmbiguousEVSDrugConcepts.py"),
            ("Intervention or Procedure Terms",
             "InterventionAndProcedureTerms.py",
             dict(IncludeAlternateNames="True")),
            ("Intervention or Procedure Terms (without Alternate Names)",
             "InterventionAndProcedureTerms.py",
             dict(IncludeAlternateNames="False")),
            ("Match Drug Terms With EVS Concepts By Name",
             "MatchDrugTermsByName.py"),
            ("Term Hierarchy Tree", "TermHierarchyTree.py"),
            ("Thesaurus Concepts Not Marked Public", "ocecdr-3588.py"),
            ("Unsuppress Drug Terms", "SuppressedDrugTerms.py"),
        ):
            if len(item) == 3:
                display, script, parms = item
            else:
                display, script = item
                parms = dict()
            ol.append(page.B.LI(page.menu_link(script, display, **parms)))


Control().run()
