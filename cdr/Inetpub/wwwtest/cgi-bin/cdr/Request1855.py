#----------------------------------------------------------------------
#
# $Id: Request1855.py,v 1.2 2008-02-21 21:29:41 bkline Exp $
#
# "I would like to get a list of unique InterventionType and InterventionName 
# pairs for InscopeProtocols along with the Original Protocol Title. Please 
# exclude any pairs where the InterventionName has a Semantic Type of Drug 
# Combination.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2005/10/27 13:51:21  bkline
# Reports on protocol by intervention.
#
#----------------------------------------------------------------------
import cdrdb, cdrcgi, xml.sax.saxutils, sys, cgi

def fix(me):
    return me and xml.sax.saxutils.escape(me) or u""

nCols = 3
try:
    fields = cgi.FieldStorage()
    nCols = int(fields and fields.getvalue("cols") or "3")
    if nCols not in (2, 3):
        cdrcgi.bail("invalid value for cols")
except:
    pass
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("CREATE TABLE #drug_combo (id INTEGER)")
conn.commit()
cursor.execute("""\
    INSERT INTO #drug_combo
SELECT DISTINCT t.doc_id
           FROM query_term t
           JOIN query_term s
             ON t.int_val = s.doc_id
          WHERE s.path = '/Term/PreferredName'
            AND s.value = 'Drug/agent combination'
            AND t.path = '/Term/SemanticType/@cdr:ref'""", timeout = 300)
conn.commit()
#sys.stderr.write("%d #drug_combo rows\n" % cursor.rowcount)
if nCols == 3:
    cursor.execute("CREATE TABLE #t (p INT, i INT, t INT)")
    conn.commit()
    cursor.execute("""\
    INSERT INTO #t
SELECT DISTINCT i.doc_id, i.int_val, t.int_val
           FROM query_term i
           JOIN query_term t
             ON t.doc_id = i.doc_id
            AND LEFT(t.node_loc, 12) = LEFT(i.node_loc, 12)
          WHERE t.path = '/InScopeProtocol/ProtocolDetail/StudyCategory'
                       + '/Intervention/InterventionType/@cdr:ref'
            AND i.path = '/InScopeProtocol/ProtocolDetail/StudyCategory'
                       + '/Intervention/InterventionNameLink/@cdr:ref'
            AND i.int_val NOT IN (SELECT id FROM #drug_combo)""",
                                  timeout = 300)
    conn.commit()
    #sys.stderr.write("%d #t rows\n" % cursor.rowcount)
    cursor.execute("""\
SELECT DISTINCT t.doc_id, o.value
           FROM #t
LEFT OUTER JOIN query_term o
             ON o.doc_id = #t.p
            AND o.path = '/InScopeProtocol/ProtocolTitle'
LEFT OUTER JOIN query_term t
             ON o.doc_id = t.doc_id
            AND t.path = '/InScopeProtocol/ProtocolTitle/@Type'
            AND t.value = 'Original'
            AND LEFT(o.node_loc, 8) = LEFT(t.node_loc, 8)""", timeout = 300)
    oTitles = {}
    row = cursor.fetchone()
    while row:
        oTitles[row[0]] = row[1]
        row = cursor.fetchone()
    #sys.stderr.write("%d original titles\n" % len(oTitles))
    for docId in oTitles:
        if not oTitles[docId] or oTitles[docId].upper() == 'NO ORIGINAL TITLE':
            cursor.execute("""\
                SELECT p.value
                  FROM query_term p
                  JOIN query_term t
                    ON t.doc_id = p.doc_id
                   AND LEFT(p.node_loc, 8) = LEFT(t.node_loc, 8)
                 WHERE p.doc_id = ?
                   AND t.path = '/InScopeProtocol/ProtocolTitle/@Type'
                   AND p.path = '/InScopeProtocol/ProtocolTitle'
                   AND t.value = 'Professional'""", docId)
            rows = cursor.fetchall()
            if rows:
                oTitles[docId] = rows[0][0]
else:
    cursor.execute("CREATE TABLE #t (i INT, t INT)")
    conn.commit()
    cursor.execute("""\
    INSERT INTO #t
SELECT DISTINCT i.int_val, t.int_val
           FROM query_term i
           JOIN query_term t
             ON t.doc_id = i.doc_id
            AND LEFT(t.node_loc, 12) = LEFT(i.node_loc, 12)
          WHERE t.path = '/InScopeProtocol/ProtocolDetail/StudyCategory'
                       + '/Intervention/InterventionType/@cdr:ref'
            AND i.path = '/InScopeProtocol/ProtocolDetail/StudyCategory'
                       + '/Intervention/InterventionNameLink/@cdr:ref'
            AND i.int_val NOT IN (SELECT id FROM #drug_combo)""",
                                  timeout = 300)
    conn.commit()
    #sys.stderr.write("%d #t rows\n" % cursor.rowcount)

cursor.execute("""\
SELECT DISTINCT n.doc_id, n.value
           FROM query_term n
           JOIN #t
             ON n.doc_id = #t.i
          WHERE n.path = '/Term/PreferredName'""", timeout = 300)
tNames = {}
row = cursor.fetchone()
while row:
    tNames[row[0]] = row[1]
    row = cursor.fetchone()
cursor.execute("""\
SELECT DISTINCT n.doc_id, n.value
           FROM query_term n
          WHERE (n.doc_id IN (SELECT DISTINCT t FROM #t)
             OR n.doc_id IN (SELECT DISTINCT i FROM #t))
            AND n.path = '/Term/PreferredName'""", timeout = 300)
row = cursor.fetchone()
while row:
    tNames[row[0]] = row[1]
    row = cursor.fetchone()
#sys.stderr.write("%d term names\n" % len(tNames))
cursor.execute("SELECT * FROM #t")
rows = []
for row in cursor.fetchall():
    if nCols == 3:
        rows.append((tNames.get(row[2], "CAN'T FIND NAME FOR CDR%d" % row[2]),
                     tNames.get(row[1], "CAN'T FIND NAME FOR CDR%d" % row[1]),
                     oTitles[row[0]]))
    else:
        rows.append((tNames.get(row[1], "CAN'T FIND NAME FOR CDR%d" % row[1]),
                     tNames.get(row[0], "CAN'T FIND NAME FOR CDR%d" % row[0])))
rows.sort()
#sys.stderr.write("%d report rows\n" % len(rows))
if nCols == 3:
    html = [u"""\
<html>
 <head>
  <title>Protocol Interventions</title>
 </head>
 <body>
  <h1>Protocol Interventions</h1>
  <table border='1' cellspacing='0' cellpadding='2'>
   <tr>
    <th>Intervention Type</th>
    <th>Intervention Name</th>
    <th>Protocol Title</th>
   </tr>"""]
else:
    html = [u"""\
<html>
 <head>
  <title>Protocol Interventions</title>
 </head>
 <body>
  <h1>Protocol Interventions</h1>
  <table border='1' cellspacing='0' cellpadding='2'>
   <tr>
    <th>Intervention Type</th>
    <th>Intervention Name</th>
   </tr>"""]
for row in rows:
    if nCols == 3:
        html.append(u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>""" % (fix(row[0]), fix(row[1]), fix(row[2])))
    else:
        html.append(u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
   </tr>""" % (fix(row[0]), fix(row[1])))
html.append(u"""\
  </table>
 </body>
</html>""")
cdrcgi.sendPage(u"".join(html))
