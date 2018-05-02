#----------------------------------------------------------------------
#
# Main menu for CIAT/CIPS staff.
#
# BZIssue::1365
# BZIssue::4009
# BZIssue::4700
# BZIssue::5013 - [Glossary Audio] Create Audio Download Tool
# BZIssue::4942 - CTRP mapping gaps
# BZIssue::5239 (JIRA::OCECDR-3543) - menu cleanup
# JIRA::OCECDR-4192
#
#----------------------------------------------------------------------
import cdrcgi

class Control(cdrcgi.Control):
    def __init__(self):
        cdrcgi.Control.__init__(self, "CIAT/OCC Staff")
        self.buttons = (cdrcgi.MAINMENU, "Log Out")
    def set_form_options(self, opts):
        opts["body_classes"] = "admin-menu"
        return opts
    def populate_form(self, form):
        audio_label = (
            "Audio Request Spreadsheet"
            " (clicking this writes to the database)"
        )
        audio_popup = (
            "Don't click this if you're not ready to generate\n"
            "a spreadsheet for pronunciation audio requests)"
        )
        form.add("<ol>")
        for script, display in (
            ("AdvancedSearch.py", "Advanced Search"),
            ("FtpAudio.py", "Audio Download"),
            ("ocecdr-3373.py", "Audio Import"),
            ("ocecdr-3606.py", audio_label),
            ("GlossaryTermAudioReview.py", "Audio Review Glossary Term"),
            ("getBatchStatus.py", "Batch Job Status"),
            ("post-translated-summary.py",
             "Create World Server Translated Summary"),
            ("Mailers.py", "Mailers"),
            ("Reports.py", "Reports"),
            ("EditExternMap.py", "Update Mapping Table"),
            ("ReplaceCWDwithVersion.py","Replace CWD with Older Version"),
            ("ReplaceDocWithNewDoc.py", "Replace Doc with New Doc"),
            ("translation-jobs.py", "Translation Job Queue"),
            ("UpdatePreMedlineCitations.py", "Update Pre-Medline Citations")
        ):
            if display == audio_label:
                form.add_menu_link(script, display, self.session,
                                   title=audio_popup)
            else:
                form.add_menu_link(script, display, self.session)
        form.add("</ol>")
Control().run()
