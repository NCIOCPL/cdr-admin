#----------------------------------------------------------------------
# "The Glossary Term Concept - Documents Modified Report will serve as a
# QC report to verify which documents were changed within a given time
# frame. The report will be separated into English and Spanish.
#
# Rewritten as part of the 2015 security sweep.
# JIRA::OCECDR-4184 - add new column for date last made publishable
#----------------------------------------------------------------------
import cgi
import cdrcgi
import cdrdb
import datetime
import lxml.etree as etree

class Control(cdrcgi.Control):
    "Collect and verify the user options for the report."

    TITLE = "Glossary Name Documents Modified Report"
    NAME_LABELS = {"en": "Term Name", "es": "Translated Term Name" }

    def __init__(self):
        "Make sure the values make sense and haven't been hacked."
        cdrcgi.Control.__init__(self)
        now = datetime.date.today()
        then = now - datetime.timedelta(7)
        self.start = self.fields.getvalue("startdate", str(then))
        self.end = self.fields.getvalue("enddate", str(now))
        self.language = self.fields.getvalue("language", "en")
        msg = cdrcgi.TAMPERING
        cdrcgi.valParmDate(self.start, msg=msg)
        cdrcgi.valParmDate(self.end, msg=msg)
        cdrcgi.valParmVal(self.language, val_list=("en", "es"), msg=msg)
        if self.end < self.start:
            cdrcgi.bail("End date cannot precede start date.")

    def show_report(self):
        "Create an Excel workbook with a single sheet."
        table = self.build_table()
        report = cdrcgi.Report("GlossaryNameDocumentsModified", [table])
        report.send("excel")

    def build_table(self):
        """
        Collect the glossary term name docs which match the user's
        criteria and add a row to the report table for each one.
        """
        columns = (
            cdrcgi.Report.Column("CDR ID", width="70px"),
            cdrcgi.Report.Column(self.name_label(), width="350px"),
            cdrcgi.Report.Column("Date Last Modified", width="100px"),
            cdrcgi.Report.Column("Publishable?", width="100px"),
            cdrcgi.Report.Column("Date First Published (*)", width="100px"),
            cdrcgi.Report.Column("Last Comment", width="450px"),
            cdrcgi.Report.Column("Date Last Publishable", width="100px")
        )
        query = cdrdb.Query("doc_version v", "v.id", "MAX(v.num)")
        query.join("doc_type t", "t.id = v.doc_type")
        query.join("active_doc a", "a.id = v.id")
        query.where("t.name = 'GlossaryTermName'")
        query.where(query.Condition("v.dt", self.start, ">="))
        query.where(query.Condition("v.dt", "%s 23:59:59" % self.end, "<="))
        query.group("v.id")
        docs = query.execute(self.cursor, timeout=300).fetchall()
        rows = []
        for term in sorted([GlossaryTermName(self, *d) for d in docs]):
            rows += term.rows()
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

    def name_label(self):
        """
        Show a different label for the name column's label, depending
        on the language selected for the report.
        """
        return self.NAME_LABELS.get(self.language)

class GlossaryTermName:
    "Information needed for a glossary terms report rows"
    def __init__(self, control, doc_id, doc_version):
        self.control = control
        self.doc_id = doc_id
        self.doc_version = doc_version
        self.names = []
        query = cdrdb.Query("doc_version", "MAX(dt) AS last_pub")
        query.where(query.Condition("id", doc_id))
        query.where("publishable = 'Y'")
        row = query.execute(control.cursor).fetchone()
        self.last_pub = row and row[0] or None
        fields = ("v.title", "v.xml", "v.publishable", "d.first_pub")
        query = cdrdb.Query("doc_version v", *fields)
        query.join("document d", "d.id = v.id")
        query.where(query.Condition("v.id", doc_id))
        query.where(query.Condition("v.num", doc_version))
        row = query.execute(control.cursor).fetchone()
        self.title, doc_xml, publishable, self.first_pub = row
        self.publishable = publishable == "Y"
        root = etree.XML(doc_xml.encode("utf-8"))
        names = { "en": "TermName", "es": "TranslatedName" }
        for node in root.findall(names.get(control.language)):
            if self.want_node(node):
                self.names.append(self.Name(self, node))

    def want_node(self, node):
        """
        See if the language matches for the name node. Ignore language for
        the English report.
        """
        if self.control.language == "en":
            return True
        return self.control.language == node.get("language")

    def rows(self):
        "Create a row for each of the term's names"
        return [name.row() for name in self.names]

    def __cmp__(self, other):
        """
        Make the documents sortable, even though the order won't mean
        much to the user, since the title isn't shown.
        """
        return cmp(self.title, other.title)

    class Name:
        "A Glossary term can have multiple names."
        def __init__(self, term, node):
            self.term = term
            self.value = self.comment = self.last_mod = None
            for child in node.findall("TermNameString"):
                self.value = child.text
            for child in node.findall("DateLastModified"):
                self.last_mod = child.text
            nodes = node.findall('Comment')
            if nodes:
                self.comment = self.Comment(nodes[0])

        def row(self):
            """
            Each name for a term gets its own row in the report, repeating
            the information common to the term in each row for the term.
            """
            name = self.value is not None and self.value or ""
            last_mod = self.last_mod and self.last_mod[:10] or ""
            publishable = self.term.publishable and "Y" or "N"
            first_pub = self.term.first_pub and self.term.first_pub[:10] or ""
            last_pub = self.term.last_pub and self.term.last_pub[:10] or ""
            comment = self.comment is not None and self.comment.tostring() or ""
            return (
                cdrcgi.Report.Cell(self.term.doc_id, center=True),
                name,
                cdrcgi.Report.Cell(last_mod, center=True),
                cdrcgi.Report.Cell(publishable, center=True),
                cdrcgi.Report.Cell(first_pub, center=True),
                comment,
                cdrcgi.Report.Cell(last_pub, center=True)
            )

        class Comment:
            "Subclass holding text and metadata for a definition comment"
            def __init__(self, node):
                self.text = node.text
                self.date = node.get("date", None)
                self.audience = node.get("audience", None)
                self.user = node.get("user", None)
            def tostring(self):
                return (u"[date: %s; user: %s; audience: %s] %s" %
                        (self.date, self.user, self.audience, self.text))
            def __cmp__(self, other):
                return cmp(self.date, other.date)

if __name__ == "__main__":
    "Allow documentation and code check tools to import us without side effects"
    Control().run()
