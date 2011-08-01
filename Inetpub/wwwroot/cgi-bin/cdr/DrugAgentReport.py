#----------------------------------------------------------------------
#
# $Id$
#
# Request #1191 (report on Drug/Agent terms).
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, ExcelWriter, sys, time

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

class Term:
    def __init__(self, id):
        self.id         = id
        self.name       = u""
        self.otherNames = []
        self.protocols  = []
        cursor.execute("""\
            SELECT value, path
              FROM query_term
             WHERE path in ('/Term/PreferredName',
                            '/Term/OtherName/OtherTermName')
               AND doc_id = ?""", id)
        for name, path in cursor.fetchall():
            if path == '/Term/PreferredName':
                self.name = name
            else:
                self.otherNames.append(name)
        self.otherNames.sort(lambda a,b: cmp(a.upper(), b.upper()))
        cursor.execute("""\
            SELECT q3.value
              FROM document d
              JOIN query_term q1
                ON q1.doc_id = d.id
              JOIN query_term q2
                ON q2.doc_id = d.id
              JOIN query_term q3
                ON q3.doc_id = d.id
             WHERE q1.path = '/InScopeProtocol/ProtocolAdminInfo'
                           + '/CurrentProtocolStatus'
               AND q2.path = '/InScopeProtocol/ProtocolDetail/StudyCategory'
                           + '/Intervention/InterventionNameLink/@cdr:ref'
               AND q3.path = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
               AND q1.value IN ('Active', 'Approved-not yet active')
               AND q2.int_val = ?""", id)
        for row in cursor.fetchall():
            if row[0] not in self.protocols:
                self.protocols.append(row[0])
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
terms = []
#file = open("DrugAgentReport.txt", "w")
for row in cursor.fetchall():
    term = Term(row[0])
    #file.write("%d %s\n" % (term.id, term.name.encode('latin-1', 'replace')))
    #for otherName in term.otherNames:
    #    file.write("\tother name: %s\n" % otherName.encode('latin-1',
    #                                                       'replace'))
    #for protocol in term.protocols:
    #    file.write("\tprotocol: %s\n" % protocol.encode('latin-1', 'replace'))
    terms.append(term)
    #sys.stderr.write("\rLoaded %d terms" % len(terms))
#sys.exit(0)
#sys.stderr.write("\n")
t = time.strftime("%Y%m%d%H%M%S")
terms.sort(lambda a,b: cmp(len(b.protocols), len(a.protocols)))
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=DrugAgentReport-%s.xls" % t
print 

workbook = ExcelWriter.Workbook()
worksheet = workbook.addWorksheet("Terms")
align = ExcelWriter.Alignment('Center')
font = ExcelWriter.Font('white', bold=True)
interior = ExcelWriter.Interior('blue')
headerStyle = workbook.addStyle(alignment=align, font=font, interior=interior)
centerStyle = workbook.addStyle(alignment=align)
worksheet.addCol(1, 300)
worksheet.addCol(2, 300)
worksheet.addCol(3, 100)
worksheet.addCol(4, 100)
row = worksheet.addRow(1, headerStyle)
row.addCell(1, "Preferred Name")
row.addCell(2, "Other Names")
row.addCell(3, "Count of Protocols")
row.addCell(4, "Primary Protocol IDs")
rowNum = 2
leftAlign = workbook.addStyle(alignment=ExcelWriter.Alignment('Left'))
for term in terms:
    if not term.protocols:
        continue
    row = worksheet.addRow(rowNum)
    row.addCell(1, term.name, leftAlign)
    row.addCell(3, len(term.protocols))
    i = 0
    totalRows = max(len(term.otherNames), len(term.protocols))
    while i < totalRows:
        if i:
            rowNum += 1
            row = worksheet.addRow(rowNum)
        if i < len(term.otherNames):
            row.addCell(2, term.otherNames[i], style=leftAlign)
        if i < len(term.protocols):
            row.addCell(4, term.protocols[i], style=leftAlign)
        i += 1
    rowNum += 1
workbook.write(sys.stdout, True)
