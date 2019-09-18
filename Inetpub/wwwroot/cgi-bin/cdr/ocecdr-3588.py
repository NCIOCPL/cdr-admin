#----------------------------------------------------------------------
# Report of thesaurus concept IDs for concepts which are marked as
# not yet public.
#
# JIRA::OCECDR-3588
# JIRA::OCECDR-4223 - rewritten to use new nci_thesaurus module
#----------------------------------------------------------------------
from cdrapi import db
import cdrcgi
import nci_thesaurus

class Control(cdrcgi.Control):
    CAPTION = "NCI Thesaurus Links Not Marked Public"
    COLUMNS = (
        "CDR ID",
        "Concept ID",
        "Available?",
        "Date Last Modified",
        "Semantic Types"
    )
    def __init__(self):
        cdrcgi.Control.__init__(self, self.CAPTION)
    def run(self):
        self.show_report()
    def set_report_options(self, opts):
        return {}
    def build_tables(self):
        join_clauses = "p.doc_id = c.doc_id", "p.node_loc = c.node_loc"
        query = db.Query("query_term c", "c.doc_id", "c.value")
        query.outer("query_term p", *join_clauses)
        query.where("c.path = '/Term/NCIThesaurusConcept'")
        query.where("p.path = '/Term/NCIThesaurusConcept/@Public'")
        query.where(query.Or("p.value IS NULL", "p.value <> 'Yes'"))
        query.order("c.doc_id", "c.value")
        rows = query.execute(self.cursor).fetchall()
        terms = [Term(self, *row) for row in rows]
        columns = [cdrcgi.Report.Column(label) for label in self.COLUMNS]
        rows = [term.row() for term in terms]
        return [cdrcgi.Report.Table(columns, rows, caption=self.CAPTION)]
class Term:
    def __init__(self, control, doc_id, concept_code):
        self.doc_id = doc_id
        self.concept_code = concept_code.strip().upper()
        query = db.Query("query_term n", "n.value").unique()
        query.join("query_term t", "t.int_val = n.doc_id")
        query.where("n.path = '/Term/PreferredName'")
        query.where("t.path = '/Term/SemanticType/@cdr:ref'")
        query.where(query.Condition("t.doc_id", doc_id))
        rows = query.execute(control.cursor).fetchall()
        self.types = [row[0] for row in rows]
        query = db.Query("query_term", "value")
        query.where("path = '/Term/DateLastModified'")
        query.where(query.Condition("doc_id", doc_id))
        rows = query.execute(control.cursor).fetchall()
        self.last_mod = rows and rows[0][0] or ""
        try:
            concept = nci_thesaurus.Concept(code=concept_code)
            self.available = concept.code.upper() == self.concept_code
        except Exception:
            control.logger.exception("fetching %r" % concept_code)
            self.available = False
    def row(self):
        return (
            "CDR%d" % self.doc_id,
            self.concept_code,
            self.available and "Yes" or "No",
            self.last_mod,
            u"; ".join(self.types)
        )
Control().run()
exit(0)
cursor = db.connect(user="CdrGuest").cursor()
title = "NCI Thesaurus Links Not Marked Public"
style = """
th, td { background-color: #ecf1ef; margin: 3px; padding: 3px; }
th { background-color: maroon; color: white; }
tr.odd td { background-color: #eff7f2; }
* { font-family: Arial, sans-serif; font-size: 11pt; }
h1 { color: maroon; font-size: 12pt; }
.flag { text-align: center; }
.frag-id { text-align: right; }
"""
html = H.Element("html")
html.append(
    B.HEAD(
        B.TITLE(title),
        B.STYLE(style)
    )
)
body = H.Element("body")
body.append(B.H1(title))
table = H.Element("table")
table.append(B.TR(B.TH("CDR ID"), B.TH("Concept ID"), B.TH("Available?"),
                  B.TH("Date Last Modified"), B.TH("Semantic Types")))
count = 1
for docId, conceptId in cursor.fetchall():
    rowClass = count % 2 == 1 and "odd" or "even"
    count += 1
    row = H.Element("tr", B.CLASS(rowClass))
    row.append(B.TD(u"CDR%d" % docId))
    row.append(B.TD(conceptId))
    row.append(B.TD(checkConcept(conceptId) and "Yes" or "No"))
    row.append(B.TD(getDateLastModified(cursor, docId)))
    row.append(B.TD(getSemanticTypes(cursor, docId)))
    table.append(row)
body.append(B.DIV(table))
html.append(body)
print("Content-type: text/html\n")
print("<!DOCTYPE html>")
print(H.tostring(html, pretty_print=True))
