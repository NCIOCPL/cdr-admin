#----------------------------------------------------------------------
#
# $Id: DrugAgentReport.py,v 1.1 2004-05-11 17:50:34 bkline Exp $
#
# Request #1191 (report on Drug/Agent terms).
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, pyXLWriter, sys, time

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

#file = open("b:/tmp/DrugAgentReport.xls", "wb")
#workbook = pyXLWriter.Writer(file)
workbook = pyXLWriter.Writer(sys.stdout)
worksheet = workbook.add_worksheet("Terms")

format = workbook.add_format()
format.set_bold();
format.set_color('white')
format.set_bg_color('blue')
format.set_align('center')

worksheet.set_column(0, 50)
worksheet.set_column(1, 50)
worksheet.set_column(2, 18)
worksheet.set_column(3, 20)
worksheet.write([0, 0], "Preferred Name", format)
worksheet.write([0, 1], "Other Names", format)
worksheet.write([0, 2], "Count of Protocols", format)
worksheet.write([0, 3], "Primary Protocol IDs", format)
baseRow = 1
for term in terms:
    if not term.protocols:
        continue
    worksheet.write([baseRow, 0], term.name.encode('latin-1', 'replace'))
    worksheet.write([baseRow, 2], len(term.protocols))
    for i in range(len(term.otherNames)):
        val = term.otherNames[i].encode('latin-1', 'replace')
        worksheet.write([baseRow + i, 1], val)
    for i in range(len(term.protocols)):
        val = term.protocols[i].encode('latin-1', 'replace')
        worksheet.write([baseRow + i, 3], val)
    rowsToSkip = 1
    if len(term.otherNames) > rowsToSkip:
        rowsToSkip = len(term.otherNames)
    if len(term.protocols) > rowsToSkip:
        rowsToSkip = len(term.protocols)
    baseRow += rowsToSkip + 1
    #sys.stderr.write("\rWrote %d rows" % baseRow)
workbook.close()
