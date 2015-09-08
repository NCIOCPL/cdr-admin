#----------------------------------------------------------------------
#
# $Id$
#
# Submenu for ClinicalTrials.gov activities.
#
# BZIssue::4700
# BZIssue::4804
# BZIssue::5141
# Removed obsolete reports and tools to eliminate security holes (2015-07-15)
# Suppressed report on orphaned CT.gov trials (summary 2015) while
# CIAT considers whether it should be rewritten for CTRP trials.
# It could never have worked when launched on PROD from a lower
# tier anyway, because a session ID from one tier won't work on another.
#----------------------------------------------------------------------
import cdr
import cdrcgi
import cgi

class Control:
    BUTTONS = (cdrcgi.MAINMENU, "Log Out")
    TITLE = "CDR Administration"
    SCRIPT = "CTGov.py"
    def __init__(self):
        fields = cgi.FieldStorage()
        self.session = cdrcgi.getSession(fields)
        self.request = cdrcgi.getRequest(fields)
        self.qc = fields.getvalue("qc")
        msg = "CGI parameter tampering detected"
        cdrcgi.valParmVal(self.qc, val_list=("1",), msg=msg, empty_ok=True)
        cdrcgi.valParmVal(self.request, val_list=self.BUTTONS, msg=msg,
                          empty_ok=True)
    def run(self):
        if self.request == cdrcgi.MAINMENU:
            cdrcgi.navigateTo("Admin.py", self.session)
        elif self.request == "Log Out":
            cdrcgi.logout(self.session)
        elif self.qc:
            self.show_qc_form()
        else:
            self.show_menu()
    def show_menu(self):
        opts = {
            "session": self.session,
            "subtitle": "ClinicalTrials.Gov Protocols",
            "buttons": self.BUTTONS,
            "action": self.SCRIPT,
            "body_classes": "admin-menu"
        }
        page = cdrcgi.Page(self.TITLE, **opts)
        page.add(page.B.H3("Mapping Table"))
        page.add("<ol>")
        page.add_menu_link("EditExternMap.py", "Update Mapping Table",
                           self.session)
        page.add("</ol>")
        page.add(page.B.H3("QC Reports"))
        page.add("<ol>")
        page.add_menu_link("CTGov.py", "CTGov Protocol QC Report",
                           self.session, qc="1")
        page.add("</ol>")
        page.add(page.B.H3("Management Reports"))
        page.add("<ol>")
        for script, display in (
            ('CTGovUpdateReport.py', 'CTGovProtocols Imported vs. CWDs'),
            ('CTGovProtocolProcessingStatusReport.py',
             'CTGovProtocols Processing Status Report'),
            ('CTGovDupReport.py', 'Records Marked Duplicate'),
            ('CTGovOutOfScope.py', 'Records Marked Out of Scope'),
            ('CTGovDownloadReport.py', 'Statistics Report - Download'),
            ('CTGovImportReport.py', 'Statistics Report - Import')
        ):
            page.add_menu_link(script, display, self.session)
        page.add("</ol>")
        page.send()
    def show_qc_form(self):
        opts = {
            "session": self.session,
            "subtitle": "CTGovProtocol QC Report",
            "buttons": ("Submit",) + self.BUTTONS,
            "action": "QcReport.py"
        }
        page = cdrcgi.Page(self.TITLE, **opts)
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Select Document for QC Report"))
        page.add_text_field(cdrcgi.DOCID, "Doc ID")
        page.add("</fieldset>")
        page.send()

Control().run()
