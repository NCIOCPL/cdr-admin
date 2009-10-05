#----------------------------------------------------------------------
#
# $Id: Request3935.py,v 1.1 2008-04-17 18:46:41 bkline Exp $
#
# "We need an adhoc report listing protocols that have terms other than
# drug/agent terms in the Intervention Name field.  Some of the CAM
# interventions have been entered into the Intervention Name field
# instead of Intervention Type and so are not being retrieved on Cancer.gov
# as CAM trials.  The report should show CDRID, Protocol Title,
# Intervention Type, Intervention Name.  I can put in a sample as soon
# as I can run the Protocol Intervention report since it should be
# similar.I would like to get a list of unique InterventionType and
# InterventionName...."
#
# ".... This can look like the Protocol Interventions with Title report,
# except add in the CDR ID of the protocol in a column right before the
# title column."
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, cdrcgi, sys, cgi

def fix(me):
    if not me:
        return "&nbsp;"
    me = unicode(me).strip()
    if not me:
        return "&nbsp;"
    return cgi.escape(me)

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("CREATE TABLE #drug_agent (id INTEGER)")
conn.commit()
cursor.execute("""\
    INSERT INTO #drug_agent
SELECT DISTINCT t.doc_id
           FROM query_term t
           JOIN query_term s
             ON t.int_val = s.doc_id
          WHERE s.path = '/Term/PreferredName'
            AND s.value = 'Drug/agent'
            AND t.path = '/Term/SemanticType/@cdr:ref'""", timeout = 600)
conn.commit()
#sys.stderr.write("%d #drug_combo rows\n" % cursor.rowcount)
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
            AND i.int_val NOT IN (SELECT id FROM #drug_agent)""",
                                  timeout = 600)
conn.commit()
cursor.execute("""\
    INSERT INTO #t
SELECT DISTINCT i.doc_id, i.int_val, t.int_val
           FROM query_term i
           JOIN query_term t
             ON t.doc_id = i.doc_id
            AND LEFT(t.node_loc, 12) = LEFT(i.node_loc, 12)
          WHERE t.path = '/CTGovProtocol/PDQIndexing/StudyCategory'
                       + '/Intervention/InterventionType/@cdr:ref'
            AND i.path = '/CTGovProtocol/PDQIndexing/StudyCategory'
                       + '/Intervention/InterventionNameLink/@cdr:ref'
            AND i.int_val NOT IN (SELECT id FROM #drug_agent)""", timeout = 600)

#sys.stderr.write("%d #t rows\n" % cursor.rowcount)
cursor.execute("SELECT DISTINCT p FROM #t")
oTitles = {}
for row in cursor.fetchall():
    oTitles[row[0]] = u""
cursor.execute("""\
SELECT DISTINCT t.doc_id, o.value
           FROM #t
           JOIN query_term o
             ON o.doc_id = #t.p
            AND o.path = '/InScopeProtocol/ProtocolTitle'
            JOIN query_term t
             ON o.doc_id = t.doc_id
            AND t.path = '/InScopeProtocol/ProtocolTitle/@Type'
            AND t.value = 'Original'
            AND LEFT(o.node_loc, 8) = LEFT(t.node_loc, 8)""", timeout = 600)
row = cursor.fetchone()
while row:
    oTitles[row[0]] = row[1]
    row = cursor.fetchone()
cursor.execute("""\
    SELECT DISTINCT doc_id, value
               FROM query_term
              WHERE path = '/CTGovProtocol/OfficialTitle'""", timeout = 600)
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
            cursor.execute("""\
                SELECT value
                  FROM query_term
                 WHERE path = '/CTGovProtocol/BriefTitle'
                   AND doc_id = ?""", docId, timeout = 300)
            rows = cursor.fetchall()
            if rows:
                oTitles[docId] = rows[0][0]

tNames = {}
#cursor.execute("""\
#SELECT DISTINCT n.doc_id, n.value
#           FROM query_term n
#           JOIN #t
#             ON n.doc_id = #t.i
#          WHERE n.path = '/Term/PreferredName'""", timeout = 600)
#row = cursor.fetchone()
#while row:
#    tNames[row[0]] = row[1]
#    row = cursor.fetchone()
cursor.execute("""\
SELECT DISTINCT n.doc_id, n.value
           FROM query_term n
          WHERE (n.doc_id IN (SELECT DISTINCT t FROM #t)
             OR n.doc_id IN (SELECT DISTINCT i FROM #t))
            AND n.path = '/Term/PreferredName'""", timeout = 600)
row = cursor.fetchone()
while row:
    tNames[row[0]] = row[1]
    row = cursor.fetchone()
#sys.stderr.write("%d term names\n" % len(tNames))
cursor.execute("SELECT * FROM #t")
rows = []
for row in cursor.fetchall():
    rows.append((tNames.get(row[2], "CAN'T FIND NAME FOR CDR%d" % row[2]),
                 tNames.get(row[1], "CAN'T FIND NAME FOR CDR%d" % row[1]),
                 row[0],
                 oTitles[row[0]]))
rows.sort()
#sys.stderr.write("%d report rows\n" % len(rows))
html = [u"""\
<html>
 <head>
  <title>Non-Drug/Agent Protocol Interventions</title>
 </head>
 <body>
  <h1>Non-Drug/Agent Protocol Interventions</h1>
  <h2>(This report excludes diagnostic procedure and molecular genetic
       technique interventions.)</h2>
  <table border='1' cellspacing='0' cellpadding='2'>
   <tr>
    <th>Intervention Type</th>
    <th>Intervention Name</th>
    <th>Protocol CDR ID</th>
    <th>Protocol Title</th>
   </tr>"""]
for row in rows:
    interventionType = fix(row[0])
    if interventionType.upper() in ('MULTIMODALITY THERAPY',
                                    'DIAGNOSTIC PROCEDURE',
                                    'MOLECULAR GENETIC TECHNIQUE'):
        continue
    html.append(u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>""" % (interventionType, fix(row[1]), row[2], fix(row[3])))
html.append(u"""\
  </table>
 </body>
</html>""")
cdrcgi.sendPage(u"".join(html))
