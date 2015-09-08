#----------------------------------------------------------------------
#
# $Id$
#
# Stats on documents imported from ClinicalTrials.gov into CDR.
#
# BZIssue::952
# BZIssue::1968
# BZIssue::4523
# BZIssue::4560
# BZIssue::4577
# BZIssue::4665
# Rewritten July 2015 to eliminate security flaws.
#
#----------------------------------------------------------------------
import cdr
import cdrcgi
import cdrdb
import cgi
import re
import time

class Control:
    """
    Top-level processing control object. Puts up request form,
    determines which export job the user has selected, and
    generate the report.
    """

    TITLE = "CDR Administration"
    SUBMENU = "Reports Menu"
    SECTION = "CTGov Import/Update Stats"
    SCRIPT = "CTGovImportReport.py"
    DATETIMELEN = len("YYYY-MM-DD HH:MM:SS")

    def __init__(self):
        fields = cgi.FieldStorage()
        cdrcgi.log_fields(fields)
        self.request = cdrcgi.getRequest(fields)
        self.session = cdrcgi.getSession(fields)
        self.job = fields.getvalue("job")
        self.max_jobs = fields.getvalue("max") or "30"
        self.cursor = cdrdb.connect("CdrGuest").cursor()
        cdrcgi.valParmVal(self.job, regex=r"^\d+$", empty_ok=True)
        cdrcgi.valParmVal(self.max_jobs, regex=r"^\d+$", empty_ok=True)
    def run(self):
        if self.request == cdrcgi.MAINMENU:
            cdrcgi.navigateTo("Admin.py", session)
        elif self.request == self.SUBMENU:
            cdrcgi.navigateTo("Reports.py", session)
        elif self.request == "Log Out":
            cdrcgi.logout(session)
        elif self.request == "Submit" and self.job:
            self.show_report()
        else:
            self.show_form()
    def show_report(self):
        query = cdrdb.Query("ctgov_import_job", "dt")
        query.where(query.Condition("id", self.job))
        rows = query.execute(self.cursor).fetchall()
        if not rows:
            cdrcgi.bail("job %s not found" % self.job)
        job_date = rows[0][0][:self.DATETIMELEN]
        opts = {
            "banner": "Clinical Trials Import/Update Statistics Report",
            "subtitle": "Import Run On %s" % job_date
        }
        title = "%s %s" % (opts["banner"], job_date)
        sets = (Doc.NEW, Doc.RVW, Doc.PUB, Doc.NOP, Doc.NOR, Doc.LCK)
        docs = self.collect_docs()
        tables = [Table(name, docs) for name in sets]
        report = cdrcgi.Report(title, tables, **opts)
        report.send()
    def show_form(self):
        opts = {
            "subtitle": self.SECTION,
            "action": self.SCRIPT,
            "buttons": ["Submit", self.SUBMENU, cdrcgi.MAINMENU, "Log Out"],
            "method": "GET"
        }
        page = cdrcgi.Page(self.TITLE, **opts)
        query = cdrdb.Query("ctgov_import_job", "id", "dt")
        query.order("dt DESC").limit(int(self.max_jobs))
        rows = query.execute(self.cursor).fetchall()
        if not rows:
            raise Exception("No import jobs recorded")
        jobs = [(str(row[0]), row[1][:self.DATETIMELEN]) for row in rows]
        page.add("<fieldset>")
        page.add(page.B.LEGEND("Select Import Job"))
        page.add_select("job", "Job Date", jobs, jobs[0][0])
        page.add("</fieldset>")
        page.send()
    def collect_docs(self):
        cols = ("e.nlm_id", "e.locked", "e.new", "e.needs_review",
                "e.pub_version", "d.id", "d.title", "q.value", "e.transferred")
        query = cdrdb.Query("ctgov_import_event e", *cols)
        query.join("ctgov_import i", "i.nlm_id = e.nlm_id")
        query.join("document d", "d.id = i.cdr_id")
        query.outer("query_term q", "q.doc_id = d.id",
                    "q.path = '/CTGovProtocol/IDInfo/OrgStudyID'")
        query.where(query.Condition("e.job", self.job))
        query.execute(self.cursor)
        docs = {}
        row = self.cursor.fetchone()
        while row:
            Doc(row).add_to_set(docs)
            row = self.cursor.fetchone()
        return docs

class Table(cdrcgi.Report.Table):
    COLUMNS = (
        cdrcgi.Report.Column("NCTID", width="100px"),
        cdrcgi.Report.Column("CDR Doc ID", width="50px"),
        cdrcgi.Report.Column("Document TItle")
    )
    def __init__(self, name, docs):
        docs = docs.get(name, {})
        docs = [docs[key] for key in sorted(docs)]
        rows = [(doc.nlm_id, doc.cdr_id, doc.title) for doc in docs]
        caption = "%s (%d)" % (name, len(docs))
        cdrcgi.Report.Table.__init__(self, Table.COLUMNS, rows, caption=caption)

class Doc:
    """
    Interesting information about a single CTGovProtocol document.
    Knows what information goes in its table row, and figures out
    which table it belongs in.
    """
    TRN = "Newly Imported Transferred Trials"
    NEW = "New Trials Imported Into the CDR"
    RVW = "Updated Trials That Require Review"
    PUB = "Updated Trials With New Publishable Version Created"
    NOP = "Updated Trials For Which Publishable Version Could Not Be Created"
    NOR = "Other Updated Trials That Do Not Require Review"
    LCK = "Trials Not Updated Because Document Was Checked Out"
    def __init__(self, row):
        self.nlm_id = row[0]
        self.locked = row[1] == 'Y'
        self.new = row[2] == 'Y'
        self.needs_review = row[3] == 'Y'
        self.pub_version = row[4] == 'Y'
        self.cdr_id = row[5]
        self.title = row[6]
        self.pub_ver_failed = row[4] == 'F'
        self.transferred = row[7] and row[7][:3].upper() == 'CDR'
        self.new_trans = row[8] == 'Y'
        #if self.new_trans:
        #    self.bucket = Doc.TRN *** OBSOLETE ***
        if self.locked:
            self.bucket = Doc.LCK
        elif self.new:
            self.bucket = Doc.NEW
        elif self.pub_version:
            self.bucket = Doc.PUB
        elif self.needs_review:
            self.bucket = Doc.RVW
        elif self.pub_ver_failed:
            self.bucket = Doc.NOP
        else:
            self.bucket = Doc.NOR
    def add_to_set(self, docs):
        if self.bucket not in docs:
            docs[self.bucket] = {}
        docs[self.bucket][self.nlm_id] = self

if __name__ == "__main__":
    Control().run()
