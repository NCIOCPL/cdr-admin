#----------------------------------------------------------------------
# "The Glossary Term Concept - Documents Modified Report will serve as a
# QC report to verify which documents were changed within a given time
# frame. The report will be separated into English and Spanish.
# New "documents modified" reports for restructured glossary documents.
#
# Rewritten July 2015 as part of security sweep.
#----------------------------------------------------------------------
import cdrcgi
import datetime
import lxml.etree as etree
from cdrapi import db

class Control(cdrcgi.Control):
    "Collect and verify the user options for the report."

    TITLE = "Glossary Concept Documents Modified Report"
    AUDIENCES = ("Patient", "Health Professional")

    def __init__(self):
        "Make sure the values make sense and haven't been hacked."
        cdrcgi.Control.__init__(self)
        now = datetime.date.today()
        then = now - datetime.timedelta(7)
        self.start = self.fields.getvalue("startdate", str(then))
        self.end = self.fields.getvalue("enddate", str(now))
        self.language = self.fields.getvalue("language", "en")
        self.audience = self.fields.getvalue("audience", self.AUDIENCES[0])
        msg = cdrcgi.TAMPERING
        cdrcgi.valParmDate(self.start, msg=msg)
        cdrcgi.valParmDate(self.end, msg=msg)
        cdrcgi.valParmVal(self.language, val_list=("en", "es"), msg=msg)
        cdrcgi.valParmVal(self.audience, msg=msg, val_list=self.AUDIENCES)
        if self.end < self.start:
            cdrcgi.bail("End date cannot precede start date.")

    def show_report(self):
        "Create an Excel workbook with a single sheet."
        table = self.build_table()
        report = cdrcgi.Report("GlossaryConceptDocumentsModified", [table])
        report.send("excel")

    def build_table(self):
        """
        Collect the glossary term concepts which match the user's
        criteria and add a row to the report table for each one.
        """
        columns = (
            cdrcgi.Report.Column("CDR ID", width="70px"),
            cdrcgi.Report.Column("Date Last Modified", width="100px"),
            cdrcgi.Report.Column("Publishable?", width="100px"),
            cdrcgi.Report.Column("Date First Published (*)", width="100px"),
            cdrcgi.Report.Column("Last Comment", width="450px")
        )
        query = db.Query("doc_version v", "v.id", "MAX(v.num)")
        query.join("doc_type t", "t.id = v.doc_type")
        query.join("active_doc a", "a.id = v.id")
        query.where("t.name = 'GlossaryTermConcept'")
        query.where(query.Condition("v.dt", self.start, ">="))
        query.where(query.Condition("v.dt", "%s 23:59:59" % self.end, "<="))
        query.group("v.id")
        docs = query.execute(self.cursor).fetchall()
        rows = []
        for concept in sorted([GlossaryTermConcept(self, *d) for d in docs]):
            rows.append(concept.row())
        note = ("(*) Date any GlossaryTermName document linked to the "
                "concept document was first published")
        no_wrap = cdrcgi.Report.xf(wrap=False)
        rows.append([cdrcgi.Report.Cell(note, sheet_style=no_wrap)])
        return cdrcgi.Report.Table(columns, rows, sheet_name="GlossaryTerm")

    def populate_form(self, form):
        "Put up the CGI form fields with defaults and instructions."
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Date Range"))
        form.add_date_field("startdate", "Start Date", value=self.start)
        form.add_date_field("enddate", "End Date", value=self.end)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Language"))
        form.add_radio("language", "English", "en", onclick=None, checked=True)
        form.add_radio("language", "Spanish", "es", onclick=None)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Audience"))
        for audience in self.AUDIENCES:
            checked = audience == self.audience
            form.add_radio("audience", audience, audience, checked=checked,
                           onclick=None)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Instructions"))
        form.add(form.B.P(
            "Specify the date range for the versions to be examined "
            "for the report. The required language and audience choices "
            "determine which comments will be included in the report."
        ))
        form.add("</fieldset>")

class GlossaryTermConcept:
    """
    Information needed for a single row of the report, as well as some
    information we're not currently using (in particular, the document
    title is used to sort the documents, but isn't displayed).
    """
    def __init__(self, control, doc_id, doc_version):
        self.control = control
        self.doc_id = doc_id
        self.doc_version = doc_version
        query = db.Query("document d", "MIN(d.first_pub)")
        query.join("query_term q", "q.doc_id = d.id")
        query.where("q.path = '/GlossaryTermName/GlossaryTermConcept/@cdr:ref'")
        query.where(query.Condition("q.int_val", doc_id))
        self.first_pub = query.execute(control.cursor).fetchone()[0]
        query = db.Query("doc_version v", "v.title", "v.xml",
                         "v.publishable")
        query.join("document d", "d.id = v.id")
        query.where(query.Condition("v.id", doc_id))
        query.where(query.Condition("v.num", doc_version))
        self.title, xml, publishable = query.execute(control.cursor).fetchone()
        root = etree.XML(xml.encode("utf-8"))
        self.publishable = publishable == "Y"
        self.comment = self.last_mod = None
        names = { "en": "TermDefinition", "es": "TranslatedTermDefinition" }
        for node in root.findall(names.get(control.language)):
            if self.want_node(node):
                child = node.find("Comment")
                if child is not None:
                    self.comment = self.Comment(child)
                child = node.find("DateLastModified")
                if child is not None:
                    self.last_mod = child.text
                break

    def want_node(self, node):
        """
        See if the languages and audience match. Ignore language for
        the English report.
        """
        language = self.control.language
        if language == "en" or node.get("language") == language:
            audiences = set([n.text for n in node.findall("Audience")])
            if self.control.audience in audiences:
                return True
        return False

    def row(self):
        "Serialize the concept information to the report table row"
        last_mod = self.last_mod and self.last_mod[:10] or ""
        publishable = self.publishable and "Y" or "N"
        first_pub = self.first_pub and self.first_pub[:10] or ""
        return (
            cdrcgi.Report.Cell(self.doc_id, center=True),
            cdrcgi.Report.Cell(last_mod, center=True),
            cdrcgi.Report.Cell(publishable, center=True),
            cdrcgi.Report.Cell(first_pub, center=True),
            self.comment and self.comment.tostring() or ""
        )

    def __cmp__(self, other):
        """
        Make the documents sortable, even though the order won't mean
        much to the user, since the title isn't shown.
        """
        return cmp(self.title, other.title)

    class Comment:
        "Subclass holding text and metadata for a definition comment"
        def __init__(self, node):
            self.text = node.text
            self.date = node.get("date", None)
            self.audience = node.get("audience", None)
            self.user = node.get("user", None)
        def __cmp__(self, other):
            return cmp(self.date, other.date)
        def tostring(self):
            return u"[date: %s; user: %s; audience: %s] %s" % (self.date,
                                                               self.user,
                                                               self.audience,
                                                               self.text)
if __name__ == "__main__":
    "Allow documentation and code check tools to import us without side effects"
    Control().run()
