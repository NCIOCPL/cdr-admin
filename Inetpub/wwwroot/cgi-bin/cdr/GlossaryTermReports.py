#!/usr/bin/env python

"""Glossary Term Reports.
"""

from cdrcgi import Controller

class Control(Controller):
    """Provide extra nesting for this, the most complex of the CDR menus."""

    SUBTITLE = "Glossary Term Reports"
    SUBMIT = None
    STATUS_REPORT = "Glossary Term Concept by {} Definition Status Report"
    MENU = (
        (
            "Management Reports", (
                (
                    "Linked or Related Document Reports", (
                        (
                            "Documents Linked to Glossary Term Name Report",
                            "GlossaryTermLinks.py",
                        ),
                        (
                            "Glossary Term and Variant Search Report",
                            "GlossaryTermPhrases.py",
                        ),
                        (
                            "Glossary Term Concept By Type Report",
                            "Request4486.py",
                        ),
                        (
                            "Pronunciation by Glossary Term Stem Report",
                            "PronunciationByWordStem.py",
                        ),
                    ),
                ),
                (
                    "Processing Reports", (
                        (
                            STATUS_REPORT.format("English"),
                            "Request4344.py",
                            dict(report="4342"),
                        ),
                        (
                            STATUS_REPORT.format("Spanish"),
                            "Request4344.py",
                            dict(report="4344"),
                        ),
                        (
                            "Glossary Term Concept Documents Modified Report",
                            "GlossaryConceptDocsModified.py",
                        ),
                        (
                            "Glossary Term Name Documents Modified Report",
                            "GlossaryNameDocsModified.py",
                        ),
                        (
                            "Glossary Translation Job Workflow Report",
                            "glossary-translation-job-report.py",
                        ),
                        (
                            "Processing Status Report",
                            "GlossaryProcessingStatusReport.py",
                        ),
                    ),
                ),
                (
                    "Publication Reports", (
                        (
                            "New Published Glossary Terms",
                            "Request4333.py",
                        ),
                        (
                            "Publish Preview",
                            "QcReport.py",
                            dict(DocType="GlossaryTermName", ReportType="pp"),
                        ),
                    ),
                ),
            ),
        ),
        (
            "QC Reports", (
                (
                    "Combined QC Reports", (
                        (
                            "Glossary Term Concept - Full QC Report",
                            "GlossaryConceptFull.py",
                        ),
                        (
                            "Glossary Term Name With Concept QC Report",
                            "QcReport.py",
                            dict(
                                DocType="GlossaryTermName",
                                ReportType="gtnwc",
                                DocVersion="0",
                            ),
                        ),
                    ),
                ),
                (
                    "Glossary Term Concept", (
                        (
                            "Glossary Term Concept QC Report",
                            "QcReport.py",
                            dict(DocType="GlossaryTermConcept"),
                        ),
                    ),
                ),
                (
                    "Glossary Term Name", (
                        (
                            "Glossary Term Name QC Report",
                            "QcReport.py",
                            dict(DocType="GlossaryTermName", DocVersion="0"),
                        ),
                    ),
                ),
            ),
        ),
    )

    def populate_form(self, page):
        page.body.set("class", "admin-menu")
        for top_section, submenus in self.MENU:
            page.form.append(page.B.H3(top_section))
            ul = page.B.UL()
            page.form.append(ul)
            for submenu_name, items in submenus:
                submenu = page.B.LI()
                submenu.append(page.B.H4(submenu_name))
                ol = page.B.OL()
                submenu.append(ol)
                for item in items:
                    if len(item) == 3:
                        label, script, parms = item
                    else:
                        label, script = item
                        parms = dict()
                    link = page.menu_link(script, label, **parms)
                    ol.append(page.B.LI(link))
                ul.append(submenu)


Control().run()
