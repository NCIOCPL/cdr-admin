#----------------------------------------------------------------------
#
# Spreadsheet of glossary terms needing pronunciation audio files.
#
# BZIssue::3606
#
#----------------------------------------------------------------------

import cgi
import datetime
import os
import sys
import lxml.etree as etree
import cdrapi.db as cdrdb
import cdrcgi
import cdr

REPORTS = cdr.BASEDIR + "/reports"

fields = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
if not cdr.canDo(session, "AUDIO IMPORT"):
    cdrcgi.bail("You are not authorized to generate this spreadsheet")

def make_sheet(styles, name):
    sheet = styles.add_sheet(name)
    labels = ("CDR ID", "Term Name", "Language", "Pronunciation", "Filename",
              "Notes (Vanessa)", "Approved?", "Notes (NCI)", "Reuse Media ID")
    for i, label in enumerate(labels):
        sheet.write(0, i, label)
    return sheet

def add_doc(sheet, doc, row_number):
    for name in doc.names:
        if not name.exclude:
            sheet.write(row_number, 0, doc.docId)
            sheet.write(row_number, 1, name.string)
            sheet.write(row_number, 2, name.language)
            if name.pronunciation:
                sheet.write(row_number, 3, name.pronunciation)
            row_number += 1
    return row_number

class TermName:
    def __init__(self, node, language):
        self.language = language
        self.string = self.pronunciation = u""
        self.exclude = node.get("AudioRecording") == "No"
        for child in node.findall('TermNameString'):
            self.string = child.text
        if language == 'English':
            for child in node.findall('TermPronunciation'):
                self.pronunciation = child.text

class TermNameDoc:
    def __init__(self, docId, cursor):
        self.docId = docId
        self.names = []
        cursor.execute("SELECT xml FROM document WHERE id = ?", (docId,))
        docXml = cursor.fetchone().xml
        root = etree.XML(docXml.encode('utf-8'))
        for nameNode in root.findall('TermName'):
            self.names.append(TermName(nameNode, 'English'))
        for nameNode in root.findall('TranslatedName'):
            self.names.append(TermName(nameNode, 'Spanish'))

cursor = cdrdb.connect(user="CdrGuest").cursor()
cursor.execute("""\
SELECT DISTINCT n.doc_id
           FROM query_term n
           JOIN pub_proc_cg c
             ON c.id = n.doc_id
LEFT OUTER JOIN query_term m
             ON m.doc_id = n.doc_id
            AND m.path LIKE '/GlossaryTermName/%/MediaLink/MediaID/@cdr:ref'
            AND LEFT(m.node_loc, 4) = LEFT(n.node_loc, 4)
          WHERE n.path LIKE '/GlossaryTermName/T%Name/TermNameString'
            AND m.doc_id IS NULL
       ORDER BY n.doc_id""")
doc_ids = [row.doc_id for row in cursor.fetchall()]
styles = cdrcgi.ExcelStyles()
sheet = make_sheet(styles, "A")
row_number = 1
for doc_id in doc_ids:
    try:
        doc = TermNameDoc(doc_id, cursor)
        row_number = add_doc(sheet, doc, row_number)
    except Exception as e:
        cdrcgi.bail("CDR{:d}: {}".format(docId, e))
today = datetime.date.today()
name = "Report4926-{}.xls".format(today.strftime("%Y%m%d%H%M%S"))
with open("{}/{}".format(REPORTS, name), "wb") as fp:
    styles.book.save(fp)
url = "/cdrReports/{}".format(name)
cdrcgi.sendPage("""<p>Report: <a href="{}">{}</a></p>""".format(url, name))
