#----------------------------------------------------------------------
#
# $Id$
#
# Spreadsheet of glossary terms needing pronunciation audio files.
#
# BZIssue::3606
#
#----------------------------------------------------------------------
import xlwt
import lxml.etree as etree
import cdrdb
import datetime
import os
import sys
import cgi
import cdrcgi
import cdr

fields = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
if not cdr.canDo(session, "AUDIO IMPORT"):
    cdrcgi.bail("You are not authorized to generate this spreadsheet")

try:
    import msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
except:
    pass

def makeSheet(book, name):
    sheet = book.add_sheet(name)
    sheet.write(0, 0, "CDR ID")
    sheet.write(0, 1, "Term Name")
    sheet.write(0, 2, "Language")
    sheet.write(0, 3, "Pronunciation")
    sheet.write(0, 4, "Filename")
    sheet.write(0, 5, "Notes (Vanessa)")
    sheet.write(0, 6, "Approved?")
    sheet.write(0, 7, "Notes (NCI)")
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
book = xlwt.Workbook(encoding="UTF-8")
sheet = makeSheet(book, "A")
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
for docId in added:
    cursor.execute("""\
INSERT INTO glossary_term_audio_request (cdr_id, spreadsheet, requested)
     VALUES (?, ?, ?)""", (docId, name, today))
conn.commit()
print "Content-type: application/vnd.ms-excel"
print "Content-disposition: attachment; filename=%s" % name
print
book.save(sys.stdout)
