#!/usr/bin/env python

"""Media report menu.
"""

from cdrcgi import Controller


class Control(Controller):

    SUBTITLE = "Media Reports"
    SUBMIT = None
    QC_PARMS = dict(DocType="Media", ReportType="img", DocVersion="0")

    def populate_form(self, page):
        page.body.set("class", "admin-menu")
        page.form.append(page.B.H3("Management Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script in (
            ("Board Meeting Recording Tracking Report",
             "RecordingTrackingReport.py"),
            ("Image Demographic Information Report",
             "ImageDemographicInformationReport.py"),
            ("Linked Media Documents", "MediaLinks.py"),
            ("Media Caption and Content Report", "MediaCaptionContent.py"),
            ("Media Doc Publishing Report", "PublishedMediaDocuments.py"),
            ("Media Images Report", "MediaLanguageCompare.py"),
            ("Media (Images) Processing Status Report",
             "ImageMediaProcessingStatusReport.py"),
            ("Media in Summary Report", "MediaInSummary.py"),
            ("Media Keyword Search Report", "MediaKeywordSearchReport.py"),
            ("Media Lists", "MediaLists.py"),
            ("Media Permissions Report", "MediaPermissionsReport.py"),
            ("Media Translation Job Workflow Report",
             "media-translation-job-report.py"),
        ):
            ol.append(page.B.LI(page.menu_link(script, display)))
        page.form.append(page.B.H3("QC Reports"))
        ol = page.B.OL()
        page.form.append(ol)
        for display, script, parms in (
            ("Advanced Search", "MediaSearch.py", dict()),
            ("Media Doc QC Report", "QcReport.py", self.QC_PARMS),
        ):
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
