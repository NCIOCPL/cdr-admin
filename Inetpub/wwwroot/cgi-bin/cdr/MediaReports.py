#!/usr/bin/env python

"""Media report menu.
"""

from cdrcgi import Controller

class Control(Controller):

    SUBTITLE = "Media Reports"
    SUBMIT = None
    QC_PARMS = dict(DocType="Media", ReportType="img")

    def populate_form(self, page):
        page.body.set("class", "admin-menu")
        page.form.append(page.B.H3("QC Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script, parms in (
            ("Advanced Search", "MediaSearch.py", dict()),
            ("Media Doc QC Report", "QcReport.py", self.QC_PARMS),
        ):
            ol.append(page.B.LI(page.menu_link(script, display, **parms)))
        page.form.append(page.B.H3("Management Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for item in (
            ("Board Meeting Recording Tracking Report",
             "RecordingTrackingReport.py"),
            ("Linked Media Documents", "MediaLinks.py"),
            ("Media Caption and Content Report", "MediaCaptionContent.py"),
            ("Media Doc Publishing Report", "PubStatsByDate.py", {"VOL":"Y"}),
            ("Media (Images) Processing Status Report", "ocecdr-4038.py"),
            ("Media Lists", "MediaLists.py"),
            ("Media Permissions Report", "ocecdr-3704.py"),
            ("Media Translation Job Workflow Report",
             "media-translation-job-report.py"),
        ):
            if len(item) == 3:
                display, script, parms = item
            else:
                display, script = item
                parms = dict()
            ol.append(page.B.LI(page.menu_link(script, display, **parms)))
        page.form.append(page.B.H3("Other Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script in (
            ("Audio Pronunciation Recordings Tracking Report",
             "PronunciationRecordings.py"),
            ("Audio Pronunciation Review Statistics Report",
             "GlossaryTermAudioReviewReport.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))

Control().run()
