#----------------------------------------------------------------------
# Report on Drug/Agent terms.
#
# BZIssue::1191
# BZIssue::5011
#----------------------------------------------------------------------
import sys
import time
import lxml.etree as etree
import cdrdb
import cdrcgi

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

def findActiveProtocols():
    cursor.execute("""\
SELECT doc_id
  INTO #active_protocols
  FROM query_term
 WHERE path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
   AND value IN ('Active', 'Approved-not yet active')""")

def getPrimaryIds():
    ids = {}
    cursor.execute("""\
SELECT i.doc_id, i.value
  FROM query_term i
  JOIN #active_protocols a
    ON a.doc_id = i.doc_id
 WHERE i.path = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'""")
    for docId, primaryId in cursor.fetchall():
        ids[docId] = primaryId
    return ids

def getInterventions():
    interventions = {}
    cursor.execute("""\
SELECT i.doc_id, i.int_val
  FROM query_term i
  JOIN #active_protocols a
    ON a.doc_id = i.doc_id
 WHERE i.path = '/InScopeProtocol/ProtocolDetail/StudyCategory/Intervention'
              + '/InterventionNameLink/@cdr:ref'""")
    for protocolId, interventionId in cursor.fetchall():
        if interventionId not in interventions:
            interventions[interventionId] = set([protocolId])
        else:
            interventions[interventionId].add(protocolId)
    return interventions

class Term:
    def __init__(self, id, protocolIds, primaryIds):
        self.id         = id
        self.name       = u""
        self.otherNames = []
        self.protocols  = []
        cursor.execute("SELECT xml FROM document WHERE id = ?", id)
        tree = etree.XML(cursor.fetchall()[0][0].encode('utf-8'))
        for node in tree.findall('PreferredName'):
            self.name = node.text
        for node in tree.findall('OtherName/OtherTermName'):
            self.otherNames.append(node.text)
        self.otherNames.sort(lambda a,b: cmp(a.upper(), b.upper()))
        if protocolIds:
            for protocolId in protocolIds:
                primaryId = primaryIds.get(protocolId,
                                           "[NO PRIMARY ID FOR CDR%d]" %
                                           protocolId)
                self.protocols.append(primaryId)
        self.protocols.sort(lambda a,b: cmp(a.upper(), b.upper()))

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
    SELECT DISTINCT doc_id
               FROM query_term
              WHERE path = '/Term/SemanticType/@cdr:ref'
                AND int_val = (SELECT doc_id
                                 FROM query_term
                                WHERE path = '/Term/PreferredName'
                                  AND value = 'Drug/agent')
           ORDER BY doc_id""")
rows = cursor.fetchall()
terms = []
findActiveProtocols()
primaryIds = getPrimaryIds()
interventions = getInterventions()
for row in rows:
    termId = row[0]
    protocolIds = interventions.get(termId)
    if protocolIds:
        terms.append(Term(termId, protocolIds, primaryIds))
t = time.strftime("%Y%m%d%H%M%S")
terms.sort(lambda a,b: cmp(len(b.protocols), len(a.protocols)))
print("Content-type: application/vnd.ms-excel")
print("Content-Disposition: attachment; filename=DrugAgentReport-%s.xls" % t)
print()

styles = cdrcgi.ExcelStyles()
sheet = styles.add_sheet("Terms")
styles.data = styles.style("align: horiz left")
widths = (60, 120, 20, 30)
labels = ("Preferred Name", "Other Names", "Count of Protocols",
          "Primary Protocol IDs")
assert(len(widths) == len(labels))
for i, chars in enumerate(widths):
    sheet.col(i).width = styles.chars_to_width(chars)
for i, label in enumerate(labels):
    sheet.write(0, i, label, styles.header)
row = 1
for term in terms:
    sheet.write(row, 0, term.name, styles.left)
    sheet.write(row, 2, len(term.protocols), styles.left)
    sheet.write(row, 1, "\n".join(term.otherNames), styles.left)
    sheet.write(row, 3, "\n".join(term.protocols), styles.left)
    row += 1
styles.book.save(sys.stdout)
