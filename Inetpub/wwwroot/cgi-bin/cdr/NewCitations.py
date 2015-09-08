#----------------------------------------------------------------------
#
# $Id$
#
# Report of Citation documents created during a specified date range.
#
# Rewritten summary 2015 as part of security sweep.
#----------------------------------------------------------------------
import cdrdb
import cdrcgi
import datetime

class Control(cdrcgi.Control):
    started = datetime.datetime.now()
    def __init__(self):
        cdrcgi.Control.__init__(self, "New Citations Report")
        self.today = datetime.date.today()
        self.start = self.fields.getvalue("start")
        self.end = self.fields.getvalue("end")
        if not self.start or not self.end:
            self.end = self.today
            self.start = self.today - datetime.timedelta(6)
        self.sanitize()

    def sanitize(self):
        msg = cdrcgi.TAMPERING
        if not self.session:
            cdrcgi.bail("Unknown or expired CDR session.")
        cdrcgi.valParmDate(str(self.start), msg=msg)
        cdrcgi.valParmDate(str(self.end), msg=msg)
        if self.end < self.start:
            cdrcgi.bail("Ending date cannot precede starting date.")
        cdrcgi.valParmVal(self.request, valList=self.buttons, empty_ok=True,
                          msg=msg)

    def populate_form(self, form):
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Report Options"))
        form.add_date_field("start", "Start Date", value=self.start)
        form.add_date_field("end", "End Date", value=self.end)
        form.add("</fieldset>")

    def build_tables(self):
        columns = (
            cdrcgi.Report.Column("CDR ID"),
            cdrcgi.Report.Column("Document Title"),
            cdrcgi.Report.Column("Created By"),
            cdrcgi.Report.Column("Creation Date", width="80px"),
            cdrcgi.Report.Column("Last Version Pub?"),
            cdrcgi.Report.Column("PMID")
        )
        self.PAGE_TITLE = "New Citation Documents"
        self.subtitle = str(self.today)
        subquery = cdrdb.Query("document d", "d.id", "c.dt", "c.usr",
                               "MAX(v.num) AS ver")
        subquery.join("doc_type t", "t.id = d.doc_type")
        subquery.join("audit_trail c", "c.document = d.id")
        subquery.join("action a", "a.id = c.action")
        subquery.outer("doc_version v", "v.id = d.id")
        subquery.where("t.name = 'Citation'")
        subquery.where("a.name = 'ADD DOCUMENT'")
        subquery.where("c.dt BETWEEN '%s' AND '%s 23:59:59'" %
                       (self.start, self.end))
        subquery.group("d.id", "c.dt", "c.usr")
        subquery.alias("t")
        pattern = "/Citation/PubmedArticle/%s/PMID"
        paths = [pattern % name for name in ("MedlineCitation", "NCBIArticle")]
        paths = ",".join(["'%s'" % path for path in paths])
        query = cdrdb.Query("document d", "d.id", "d.title", "u.name", "t.dt",
                            "v.publishable", "p.value")
        query.join(subquery, "t.id = d.id")
        query.join("open_usr u", "u.id = t.usr")
        query.outer("doc_version v", "v.id = d.id", "v.num = t.ver")
        query.outer("query_term p", "p.doc_id = d.id", "p.path IN (%s)" % paths)
        query.order("d.id")
        parms = {
            "cmd": "Retrieve",
            "db": "pubmed",
            "dopt": "Abstract",
        }
        citations = []
        rows = query.execute(self.cursor).fetchall()
        for doc_id, title, user, date, publishable, pmid in rows:
            if pmid:
                parms["list_uids"] = pmid
                p = "&".join(["%s=%s" % (k, parms[k]) for k in parms])
                url = "http://www.ncbi.nlm.nih.gov/entrez/query.fcgi?%s" % p
                pmid = cdrcgi.Report.Cell(pmid, href=url, target="_blank")
            else:
                pmid = ""
            citations.append([
                doc_id,
                title,
                user,
                date[:10],
                cdrcgi.Report.Cell(publishable or "N/A", classes="center"),
                pmid
            ])
        caption = "%d Documents Created Between %s and %s" % (len(citations),
                                                              self.start,
                                                              self.end)
        return [cdrcgi.Report.Table(columns, citations, caption=caption)]

    def set_report_options(self, opts):
        opts["elapsed"] = datetime.datetime.now() - Control.started
        return opts

if __name__ == "__main__":
    Control().run()
