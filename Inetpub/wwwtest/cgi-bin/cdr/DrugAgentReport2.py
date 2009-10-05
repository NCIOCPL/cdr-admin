#----------------------------------------------------------------------
#
# $Id: DrugAgentReport2.py,v 1.3 2006-07-20 22:49:50 ameyer Exp $
#
# Request #1602 (second report on Drug/Agent terms).
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2005/05/25 19:00:05  bkline
# Added new columns requested by Sheri (request #1695).
#
# Revision 1.1  2005/03/24 21:15:04  bkline
# Drug/Agent Other Names Report.
#
#----------------------------------------------------------------------
import cdrdb, cgi, pyXLWriter, sys, time

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
        cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE path = '/Term/PreferredName'
               AND doc_id = ?""", id)
        rows = cursor.fetchall()
        if rows:
            self.name = rows[0][0]
        cursor.execute("""\
   SELECT DISTINCT n.value, t.value, v.value, r.value, s.value
              FROM query_term n
              JOIN query_term t
                ON n.doc_id = t.doc_id
               AND LEFT(n.node_loc, 4) = LEFT(t.node_loc, 4)
   LEFT OUTER JOIN query_term v
                ON v.doc_id = t.doc_id
               AND LEFT(v.node_loc, 4) = LEFT(t.node_loc, 4)
               AND v.path = '/Term/OtherName/SourceInformation'
                          + '/VocabularySource/SourceCode'
   LEFT OUTER JOIN query_term r
                ON r.doc_id = t.doc_id
               AND LEFT(r.node_loc, 4) = LEFT(t.node_loc, 4)
               AND r.path = '/Term/OtherName/SourceInformation/ReferenceSource'
   LEFT OUTER JOIN query_term s
                ON s.doc_id = t.doc_id
               AND LEFT(s.node_loc, 12) = LEFT(v.node_loc, 12)
               AND s.path = '/Term/OtherName/SourceInformation'
                          + '/VocabularySource/SourceTermId'
             WHERE n.path = '/Term/OtherName/OtherTermName'
               AND t.path = '/Term/OtherName/OtherNameType'
               AND n.doc_id = ?""", id)
        for row in cursor.fetchall():
            self.otherNames.append(row)
        self.otherNames.sort(lambda a,b: cmp(a[0].upper(), b[0].upper()))

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
for row in cursor.fetchall():
    terms.append(Term(row[0]))
t = time.strftime("%Y%m%d%H%M%S")
terms.sort(lambda a,b: cmp(a.name, b.name))
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=DrugAgentReport-%s.xls" % t
print

workbook = pyXLWriter.Writer(sys.stdout)
worksheet = workbook.add_worksheet("Terms")

format = workbook.add_format()
format.set_bold();
format.set_color('white')
format.set_bg_color('blue')
format.set_align('center')

worksheet.set_column(0, 7)
worksheet.set_column(1, 50)
worksheet.set_column(2, 50)
worksheet.set_column(3, 25)
worksheet.set_column(4, 30)
worksheet.set_column(5, 8)
worksheet.write([0, 0], "CDR ID", format)
worksheet.write([0, 1], "Preferred Name", format)
worksheet.write([0, 2], "Other Names", format)
worksheet.write([0, 3], "Other Name Type", format)
worksheet.write([0, 4], "Source", format)
worksheet.write([0, 5], "SourceID", format)
row = 1

def fix(name):
    return (name.replace(u'\u2120', u'(SM)')
                .replace(u'\u2122', u'(TM)')
                .encode('latin-1', 'ignore'))
for term in terms:
    worksheet.write([row, 0], term.id)
    worksheet.write_string([row, 1], fix(term.name))
    for i in range(len(term.otherNames)):
        name = fix(term.otherNames[i][0])
        nameType = fix(term.otherNames[i][1])
        worksheet.write_string([row, 2], name)
        worksheet.write_string([row, 3], nameType)
        if term.otherNames[i][2]:
            worksheet.write_string([row, 4], fix(term.otherNames[i][2] +
                                                 " Vocabulary"))
        elif term.otherNames[i][3]:
            worksheet.write_string([row, 4], fix(term.otherNames[i][3]))
        if term.otherNames[i][4]:
            worksheet.write_string([row, 5], fix(term.otherNames[i][4]))
        row += 1
    if not term.otherNames:
        row += 1
workbook.close()
