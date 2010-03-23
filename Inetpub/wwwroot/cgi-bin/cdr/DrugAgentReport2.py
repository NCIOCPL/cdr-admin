#----------------------------------------------------------------------
#
# $Id$
#
# Request #1602 (second report on Drug/Agent terms).
#
# BZIssue::1602
# BZIssue::1695
# BZIssue::2337
# BZIssue::4784
#
#----------------------------------------------------------------------
import cdrdb, cgi, ExcelWriter, sys, time, lxml.etree as etree

# The report can now produce drug information terms filtered
#   by protocol status as before, or unfiltered if requested.
allDrugs = False
fields = cgi.FieldStorage()
if fields and fields.getvalue('alldrugs'):
    allDrugs = True

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

class Term:
    def __init__(self, id):
        self.id         = id
        self.name       = u""
        self.otherNames = []
        cursor.execute("SELECT xml FROM document WHERE id = ?", id)
        tree = etree.XML(cursor.fetchone()[0].encode('utf-8'))
        for e in tree.findall('PreferredName'):
            self.name = e.text
        for e in tree.findall('OtherName'):
            self.otherNames.append(Term.OtherName(e))
        self.otherNames.sort()
    def __cmp__(self, other):
        return cmp(self.name, other.name)
    class OtherName:
        def __init__(self, node):
            self.name = self.nameType = self.vocabularyCode = None
            self.referenceSource = self.sourceTermId = None
            for child in node:
                if child.tag == 'OtherTermName':
                    self.name = child.text
                    self.nameUpper = self.name.upper()
                elif child.tag == 'OtherNameType':
                    self.nameType = child.text
                elif child.tag == 'SourceInformation':
                    for grandchild in child.findall('ReferenceSource'):
                        self.referenceSource = grandchild.text
                    for grandchild in child.findall('VocabularySource'
                                                    '/SourceCode'):
                        self.vocabularyCode = grandchild.text
                    for grandchild in child.findall('VocabularySource'
                                                    '/SourceTermId'):
                        self.sourceTermId = grandchild.text
        def __cmp__(self, other):
            return cmp(self.nameUpper, other.nameUpper)

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("CREATE TABLE #t1 (doc_id INTEGER)")
conn.commit()
cursor.execute("CREATE TABLE #t2 (doc_id INTEGER)")
conn.commit()
cursor.execute("""\
        INSERT INTO #t1 (doc_id)
    SELECT DISTINCT doc_id
               FROM query_term
              WHERE path = '/Term/SemanticType/@cdr:ref'
                AND int_val = (SELECT doc_id
                                 FROM query_term
                                WHERE path = '/Term/PreferredName'
                                  AND value = 'Drug/agent')""")
conn.commit()

if not allDrugs:
    # Filter in only those terms that are used in InterventionNameLinks
    #   in Active or Approved-not yet active protocols
    cursor.execute("""\
           INSERT INTO #t2
                SELECT doc_id
                  FROM query_term
                 WHERE path = '/InScopeProtocol/ProtocolAdminInfo'
                            + '/CurrentProtocolStatus'
                   AND value IN ('Active', 'Approved-not yet active')""")
    conn.commit()
    cursor.execute("""\
       SELECT DISTINCT u.int_val
                  FROM query_term u
                  JOIN #t1
                    ON #t1.doc_id = u.int_val
                  JOIN #t2
                    ON #t2.doc_id = u.doc_id
                 WHERE u.path = '/InScopeProtocol/ProtocolDetail/StudyCategory'
                               + '/Intervention/InterventionNameLink/@cdr:ref'
              ORDER BY u.int_val""")
else:
    # Take all drugs, regardless of usage in protocols
    cursor.execute("""\
       SELECT DISTINCT u.int_val
                  FROM query_term u
                  JOIN #t1
                    ON #t1.doc_id = u.int_val
              ORDER BY u.int_val""")

terms = []
#start = time.time()
for row in cursor.fetchall():
    terms.append(Term(row[0]))
#delta = time.time() - start
#print "%f seconds to process 100 docs" % delta
#sys.exit(0)
t = time.strftime("%Y%m%d%H%M%S")
terms.sort()
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=DrugAgentReport-%s.xls" % t
print

book = ExcelWriter.Workbook()
sheet = book.addWorksheet("Terms")
font = ExcelWriter.Font('white', bold=True)
alignment = ExcelWriter.Alignment('Center')
interior = ExcelWriter.Interior('blue')
format = book.addStyle(font=font, interior=interior, alignment=alignment)
sheet.addCol(1, 38)
sheet.addCol(2, 273)
sheet.addCol(3, 273)
sheet.addCol(4, 137)
sheet.addCol(5, 164)
sheet.addCol(6, 44)
row = sheet.addRow(1, format)
row.addCell(1, "CDR ID")
row.addCell(2, "Preferred Name")
row.addCell(3, "Other Names")
row.addCell(4, "Other Name Type")
row.addCell(5, "Source")
row.addCell(6, "SourceID")
rowNum = 2

for term in terms:
    row = sheet.addRow(rowNum)
    row.addCell(1, term.id)
    row.addCell(2, term.name)
    first = True
    for otherName in term.otherNames:
        if first:
            first = False
        else:
            row = sheet.addRow(rowNum)
        row.addCell(3, otherName.name)
        row.addCell(4, otherName.nameType)
        if otherName.vocabularyCode:
            row.addCell(5, u"%s Vocabulary" % otherName.vocabularyCode)
        else:
            row.addCell(5, otherName.referenceSource)
        if otherName.sourceTermId:
            row.addCell(6, otherName.sourceTermId)
        rowNum += 1
    if not term.otherNames:
        rowNum += 1
book.write(sys.stdout, True)
