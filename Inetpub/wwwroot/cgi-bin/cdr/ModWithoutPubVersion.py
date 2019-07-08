#----------------------------------------------------------------------
# Reports on documents which have been changed since a previously
# publishable version without a new publishable version have been
# created.
#
# Rewritten summer 2015 as part of security sweep.
#----------------------------------------------------------------------
import cdr
import cdrdb
import cdrcgi
import cgi
import datetime

class Control(cdrcgi.Control):
    TITLE = "Documents Modified Since Last Publishable Version"
    def __init__(self):
        cdrcgi.Control.__init__(self, Control.TITLE)
        self.mod_user = self.fields.getvalue("ModUser")
        self.start = self.fields.getvalue("FromDate")
        self.end = self.fields.getvalue("ToDate")
        self.doc_type = self.fields.getvalue("DocType")
        self.sanitize()
    def populate_form(self, form):
        end = datetime.date.today()
        start = end - datetime.timedelta(7)
        doc_types = [("", "All Types")] + cdr.getDoctypes(self.session)
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Report Options"))
        form.add_text_field("ModUser", "User")
        form.add_select("DocType", "Doc Type", doc_types)
        form.add_date_field("FromDate", "Start Date", value=start)
        form.add_date_field("EndDate", "To Date", value=end)
        form.add("</fieldset>")

    def build_tables(self):
        "String interpolation is safe because of sanitize() below."
        actions = ("ADD DOCUMENT", "MODIFY DOCUMENT")
        actions = ", ".join(["'%s'" % action for action in actions])
        tables = []
        subquery = cdrdb.Query("audit_trail a", "MAX(dt)")
        subquery.join("action", "action.id = a.action")
        subquery.where("a.document = d.id")
        subquery.where("action.name IN (%s)" % actions)
        query = cdrdb.Query("active_doc d", "t.name AS doc_type",
                            "d.id AS doc_id", "u.fullname AS user_name",
                            "a.dt AS mod_date").into("#last_mod")
        query.join("doc_type t", "d.doc_type = t.id")
        query.join("audit_trail a", "a.document = d.id")
        query.join("open_usr u", "u.id = a.usr")
        query.join("action", "action.id = a.action")
        query.where("action.name IN (%s)" % actions)
        query.where(query.Condition("a.dt", subquery))
        if self.start:
            query.where("a.dt >= '%s'" % self.start)
        if self.end:
            query.where("a.dt <= '%s 23:59:59'" % self.end)
        if self.mod_user:
            query.where("u.name = '%s'" % self.mod_user.replace("'", "''"))
        if self.doc_type:
            query.where("t.name = '%s'" % self.doc_type)
        query.execute(self.cursor)
        query = cdrdb.Query("doc_version v", "v.id AS doc_id",
                            "MAX(v.updated_dt) AS pub_ver_date")
        query.into("#last_publishable_version")
        query.join("#last_mod m", "m.doc_id = v.id")
        query.where("v.publishable = 'Y'")
        query.group("v.id")
        query.execute(self.cursor)
        query = cdrdb.Query("doc_version v", "v.id AS doc_id",
                            "MAX(v.updated_dt) AS unpub_ver_date")
        query.into("#last_unpublishable_version")
        query.join("#last_mod m", "m.doc_id = v.id")
        query.where("v.publishable = 'N'")
        query.group("v.id")
        query.execute(self.cursor)
        query = cdrdb.Query("#last_mod d", "d.doc_type", "d.doc_id",
                            "p.pub_ver_date", "d.user_name", "d.mod_date",
                            "u.unpub_ver_date")
        query.join("#last_publishable_version p", "p.doc_id = d.doc_id")
        query.outer("#last_unpublishable_version u", "u.doc_id = d.doc_id")
        query.where("p.pub_ver_date < d.mod_date")
        query.order("d.doc_type", "d.mod_date", "d.user_name")
        rows = query.execute(self.cursor).fetchall()
        current_doc_type = None
        columns = (
            cdrcgi.Report.Column("Doc ID"),
            cdrcgi.Report.Column("Latest Publishable Version Date"),
            cdrcgi.Report.Column("Modified By"),
            cdrcgi.Report.Column("Modified Date"),
            cdrcgi.Report.Column("Latest Non-publishable Version Date")
        )
        table_rows = []
        for row in rows:
            doc = Document(*row)
            if doc.doc_type != current_doc_type:
                if current_doc_type and table_rows:
                    tables.append(cdrcgi.Report.Table(columns, table_rows,
                                                      caption=current_doc_type))
                current_doc_type = doc.doc_type
                table_rows = []
            table_rows.append(doc.report())
        if current_doc_type and table_rows:
            tables.append(cdrcgi.Report.Table(columns, table_rows,
                                              caption=current_doc_type))
        return tables
    def set_report_options(self, opts):
        if self.doc_type:
            subtitle = "%s Documents" % self.doc_type
        else:
            subtitle = "Documents"
        if self.mod_user or self.start or self.end:
            subtitle += " Modified"
        if self.mod_user:
            subtitle += " By %s" % self.mod_user
        if self.start and self.end:
            subtitle += " Between %s And %s" % (self.start, self.end)
        elif self.start:
            subtitle += " On Or After %s" % self.start
        elif self.end:
            subtitle += " On Or Before %s" % self.end
        if subtitle == "Documents":
            subtitle = "All Documents"
        opts["subtitle"] = subtitle
        opts["page_opts"] = {}
        return opts
    def sanitize(self):
        if not self.session:
            cdrcgi.bail("Missing required session")
        msg = cdrcgi.TAMPERING
        cdrcgi.valParmVal(self.request, val_list=self.buttons, empty_ok=True,
                          msg=msg)
        cdrcgi.valParmDate(self.start, empty_ok=True, msg=msg)
        cdrcgi.valParmDate(self.end, empty_ok=True, msg=msg)
        if self.start and self.end and self.start > self.end:
            cdrcgi.bail("Date range can't end before it starts")
        if self.mod_user:
            if self.mod_user.lower() not in self.get_names("open_usr"):
                cdrcgi.bail("Unknown user")
        if self.doc_type:
            if self.doc_type.lower() not in self.get_names("doc_type"):
                cdrcgi.bail()
    def get_names(self, table):
        query = cdrdb.Query(table, "name")
        rows = query.execute(self.cursor).fetchall()
        return set([row[0].lower() for row in rows])

class Document:
    def __init__(self, doc_type, doc_id, pub_date, mod_by, mod_date, np_date):
        self.doc_type = doc_type
        self.doc_id = doc_id
        self.pub_date = pub_date
        self.mod_by = mod_by
        self.mod_date = mod_date
        self.non_pub_ver_date = np_date
    def report(self):
        cdr_id = cdr.normalize(self.doc_id)
        if self.doc_type in cdr.FILTERS:
            url = "QcReport.py?DocId={:d}".format(self.doc_id)
            cdr_id = cdrcgi.Report.Cell(cdr_id, href=url, target="_blank")
        return (
            cdr_id,
            self.pub_date,
            self.mod_by,
            self.mod_date,
            self.non_pub_ver_date
        )

if __name__ == "__main__":
    Control().run()
