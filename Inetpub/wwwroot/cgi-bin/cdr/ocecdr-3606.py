#----------------------------------------------------------------------
#
# Spreadsheet of glossary terms needing pronunciation audio files.
#
# BZIssue::3606
#
#----------------------------------------------------------------------
import lxml.etree as etree
import cdrdb
import datetime
import os
import sys
import cgi
import cdrcgi
import cdr

REPORTS = cdr.BASEDIR + "/reports"

fields = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
if not cdr.canDo(session, "AUDIO IMPORT"):
    cdrcgi.bail("You are not authorized to generate this spreadsheet")

try:
    import msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
except:
    pass

def makeSheet(styles, name):
    sheet = styles.add_sheet(name)
    labels = ("CDR ID", "Term Name", "Language", "Pronunciation", "Filename",
              "Notes (Vanessa)", "Approved?", "Notes (NCI)")
    for i, label in enumerate(labels):
        sheet.write(0, i, label)
    return sheet

def addDoc(sheet, doc, rowNumber):
    for name in doc.names:
        sheet.write(rowNumber, 0, doc.docId)
        sheet.write(rowNumber, 1, name.string)
        sheet.write(rowNumber, 2, name.language)
        if name.pronunciation:
            sheet.write(rowNumber, 3, name.pronunciation)
        rowNumber += 1
    return rowNumber

class TermName:
    def __init__(self, node, language):
        self.language = language
        self.string = self.pronunciation = u""
        for child in node.findall('TermNameString'):
            self.string = child.text
        if language == 'English':
            for child in node.findall('TermPronunciation'):
                self.pronunciation = child.text

class TermNameDoc:
    def __init__(self, docId, cursor):
        self.docId = docId
        self.names = []
        cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml.encode('utf-8'))
        for nameNode in tree.findall('TermName'):
            self.names.append(TermName(nameNode, 'English'))
        for nameNode in tree.findall('TranslatedName'):
            self.names.append(TermName(nameNode, 'Spanish'))

conn = cdrdb.connect()
cursor = conn.cursor()
cursor.execute("""\
    SELECT d.id
      FROM document d
      JOIN doc_type t
        ON t.id = d.doc_type
      JOIN pub_proc_cg c
        ON c.id = d.id
     WHERE t.name = 'GlossaryTermName'""")
docIds = [row[0] for row in cursor.fetchall()]
docIds.sort()
cursor.execute("SELECT cdr_id FROM glossary_term_audio_request")
alreadyDone = set([row[0] for row in cursor.fetchall()])
styles = cdrcgi.ExcelStyles()
sheet = makeSheet(styles, "A")
rowNumber = 1
added = []
for docId in docIds:
    if docId in alreadyDone:
        continue
    try:
        doc = TermNameDoc(docId, cursor)
        if doc.names[0].pronunciation:
            rowNumber = addDoc(sheet, doc, rowNumber)
            alreadyDone.add(docId)
            added.append(docId)
    except Exception, e:
        cdrcgi.bail("CDR%d: %s" % (docId, e))
today = datetime.date.today()
name = "Report4926-%s.xls" % today.strftime("%Y%m%d")
fp = open("%s/%s" % (REPORTS, name), "wb")
styles.book.save(fp)
fp.close()
for docId in added:
    cursor.execute("""\
INSERT INTO glossary_term_audio_request (cdr_id, spreadsheet, requested)
     VALUES (?, ?, ?)""", (docId, name, today))
conn.commit()
url = "/cdrReports/%s" % name
cdrcgi.sendPage("""<p>Report: <a href="%s">%s</a></p>""" % (url, name))
