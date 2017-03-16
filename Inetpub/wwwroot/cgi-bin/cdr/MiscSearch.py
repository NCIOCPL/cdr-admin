#----------------------------------------------------------------------
# Find Miscellaneous documents and display QC reports for them.
# JIRA::OCECDR-4115 - support searching titles with non-ascii characters
#----------------------------------------------------------------------
import cdrcgi
import cdrdb
import datetime
import urllib

class Control(cdrcgi.Control):
    """
    Select Miscellaneous documents for QC report display.
    """

    PAGE_TITLE = "CDR Advanced Search"
    TYPE_PATH = ("/MiscellaneousDocument/MiscellaneousDocumentMetadata"
                 "/MiscellaneousDocumentType")
    BOOLS = ("and", "or")
    FILTER = "name:Miscellaneous Document Report Filter"
    URL = "/cgi-bin/cdr/Filter.py"

    def __init__(self):
        """
        Collect and validate the report options.
        """

        cdrcgi.Control.__init__(self, "Miscellaneous Documents")
        self.today = datetime.date.today()
        self.types = self.get_types()
        self.type = self.fields.getvalue("type") or ""
        self.fragment = unicode(self.fields.getvalue("title") or "", "utf-8")
        self.bool = self.fields.getvalue("bool") or "and"
        cdrcgi.valParmVal(self.type, val_list=self.types, msg=cdrcgi.TAMPERING)
        cdrcgi.valParmVal(self.bool, val_list=self.BOOLS, msg=cdrcgi.TAMPERING)

    def populate_form(self, form):
        """
        Let the user indicate which documents she wants to see.
        """

        form.add("<fieldset>")
        form.add(form.B.LEGEND("Report Request Options"))
        form.add_text_field("title", "Title", value=self.fragment)
        form.add_select("type", "Type", options=self.types, default=self.type)
        form.add("</fieldset>")
        form.add("<fieldset>")
        form.add(form.B.LEGEND("Search Connector"))
        for value in self.BOOLS:
            checked = self.bool == value
            form.add_radio("bool", value.capitalize(), value, checked=checked)
        form.add("</fieldset>")

    def build_tables(self):
        """
        Find the Miscellaneous documents which match the report parameters.
        """

        conditions = []
        caption = []
        query = cdrdb.Query("document d", "d.id", "d.title")
        if self.fragment:
            fragment = self.fragment + "%"
            caption = [u"matching title fragment '%s'" % fragment]
            conditions.append(query.Condition("d.title", fragment, "LIKE"))
        if self.type:
            having = "having type %s" % repr(self.type)
            if caption:
                caption.append("%s %s" % (self.bool, having))
            else:
                caption = [having]
            conditions.append(query.Condition("t.value", self.type))
        else:
            query.join("doc_type t", "t.id = d.doc_type")
            query.where("t.name = 'MiscellaneousDocument'")
        if len(conditions) > 1 and self.bool == "or":
            query.where(query.Or(*conditions))
            query.outer("query_term t", "t.doc_id = d.id",
                        "t.path = '%s'" % self.TYPE_PATH)
        else:
            if self.type:
                query.join("query_term t", "t.doc_id = d.id",
                           "t.path = '%s'" % self.TYPE_PATH)
            for condition in conditions:
                query.where(condition)
        rows = []
        parms = { "Filter": self.FILTER }
        for doc_id, doc_title in query.order(2, 1).execute().fetchall():
            cdr_id = "CDR%010d" % doc_id
            parms["DocId"] = cdr_id
            url = "%s?%s" % (self.URL, urllib.urlencode(parms))
            link = cdrcgi.Report.Cell(cdr_id, href=url, target="_blank")
            rows.append((doc_title, link))
        columns = (
            cdrcgi.Report.Column("Document Title"),
            cdrcgi.Report.Column("CDR ID"),
        )
        caption = ["Found %d Miscellaneous Documents" % len(rows)] + caption
        caption.append(str(self.today))
        return [cdrcgi.Report.Table(columns, rows, caption=caption)]

    def set_report_options(self, opts):
        """
        Make sure table isn't too narrow if no results are found."
        """

        opts["css"] = "caption { min-width: 1024px; }"
        return opts

    def get_types(self):
        """
        Get the list of valid values for miscellaneous document types.
        """

        query = cdrdb.Query("query_term", "value").unique()
        query.where(query.Condition("path", self.TYPE_PATH))
        query.order("value")
        values = [""]
        for row in query.execute(self.cursor).fetchall():
            value = row[0] and row[0].strip() or ""
            if value:
                values.append(value)
        return values

#----------------------------------------------------------------------
# Make it possible to load this script as a module (e.g., for lint).
#----------------------------------------------------------------------
if __name__ == "__main__":
    Control().run()
