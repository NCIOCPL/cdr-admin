#!/usr/bin/env python

"""Drug Information Summary report menu.
"""

from cdrcgi import Controller

class Control(Controller):

    SUBTITLE = "Drug Information Reports"
    SUBMIT = None
    QC_PARMS = dict(DocType="DrugInformationSummary", DocVersion="0")
    PP_PARMS = dict(DocType="DrugInformationSummary", ReportType="pp")
    PP_PARMS["DocVersion"] = "0"

    def populate_form(self, page):
        page.body.set("class", "admin-menu")
        page.form.append(page.B.H3("Management Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script in (
            ("Drug Date Last Modified Report", "DrugDateLastModified.py"),
            ("Drug Information Comprehensive Review Date Report",
             "DrugCRD.py"),
            ("Drug Information Summaries Processing Report",
             "DISProcessingStatusReport.py"),
            ("Drug Summaries with Markup Report", "DISWithMarkup.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))
        page.form.append(page.B.H3("QC Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script, parms in (
            ("Advanced Search", "DISSearch.py?type=advanced", {}),
            ("Drug Information QC Report", "QcReport.py", self.QC_PARMS),
            ("Publish Preview", "QcReport.py", self.PP_PARMS),
        ):
            ol.append(page.B.LI(page.menu_link(script, display, **parms)))
        page.form.append(page.B.H3("Other Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script in (
            ("DIS By Drug Type Report", "DISByDrugType.py"),
            ("Drug Description Report", "DrugDescriptionReport.py"),
            ("Drug Indications Report", "DrugIndicationsReport.py"),
            ("Drug Information Summaries Lists", "DISLists.py"),
            ("Drug Information Type Of Change", "DISTypeChangeReport.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))


Control().run()
