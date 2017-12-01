#!/usr/bin/env python

"""
Report on dated actions for a particular document type
"""

from lxml import etree
import cdr
import cdrcgi

class Control(cdrcgi.Control):
    "Collect and verify the user options for the report"

    TITLE = "Dated Actions Report"

    def __init__(self):
        "Make sure the values make sense and haven't been hacked"

        cdrcgi.Control.__init__(self, self.TITLE)
        self.doctypes = cdr.getDoctypes(self.session)
        self.doctype = self.fields.getvalue("doctype")
        if self.doctype and self.doctype not in self.doctypes:
            cdrcgi.bail(cdrcgi.TAMPERING)

    def populate_form(self, form):
        "Show form with doctype selection picklist"

        form.add("<fieldset>")
        form.add(form.B.LEGEND("Select Document Type For Report"))
        form.add_select("doctype", "Doc Type", self.doctypes)
        form.add("</fieldset>")

    def build_tables(self):
        "Show the report's only table"

        columns = (
            cdrcgi.Report.Column("Doc ID"),
            cdrcgi.Report.Column("Doc Title"),
            cdrcgi.Report.Column("Action Description"),
            cdrcgi.Report.Column("Action Date"),
            cdrcgi.Report.Column("Comment")
        )
        parms = dict(DocType=self.doctype)
        report = cdr.report(self.session, "Dated Actions", parms=parms)
        class Action:
            def __init__(self, id, title, node):
                self.id = id
                self.title = title
                self.desc = cdr.get_text(node.find("ActionDescription"), "")
                self.date = cdr.get_text(node.find("ActionDate"), "")
                self.comment = cdr.get_text(node.find("Comment"), "")
            @property
            def row(self):
                return self.id, self.title, self.desc, self.date, self.comment
            def __cmp__(self, other):
                return cmp((self.date, self.id), (other.date, other.id))
        actions = []
        for row in report.findall("ReportRow"):
            id = cdr.get_text(row.find("DocId"), "")
            title = cdr.get_text(row.find("DocTitle"), "")
            for node in row.findall("DatedAction"):
                actions.append(Action(id, title, node))
        rows = [action.row for action in sorted(actions)]
        caption = "Document Type: {}".format(self.doctype)
        return [cdrcgi.Report.Table(columns, rows, caption=caption)]

if __name__ == "__main__":
    try:
        Control().run()
    except Exception as e:
        cdrcgi.bail(str(e))
