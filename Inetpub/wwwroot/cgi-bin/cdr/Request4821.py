#----------------------------------------------------------------------
#
# $Id$
#
# "The ad hoc query - Drug terms without definitions on active trials"
# times out each time we run it. Other queries appear to be fine"
#
# BZIssue::4821
#
#----------------------------------------------------------------------
import cdrdb, time, cgi, cdrcgi

start = time.time()
conn = cdrdb.connect('CdrGuest')
conn.setAutoCommit(True)
cursor = conn.cursor()
cursor.execute("CREATE TABLE #drugs (doc_id INTEGER)")
cursor.execute("CREATE TABLE #defs (doc_id INTEGER)")
cursor.execute("CREATE TABLE #active (doc_id INTEGER)")
cursor.execute("CREATE TABLE #links (doc_id INTEGER)")
cursor.execute("""\
    INSERT INTO #defs
SELECT DISTINCT doc_id
           FROM query_term
          WHERE path = '/Term/Definition/DefinitionText/@cdr:id'""")
cursor.execute("""\
    INSERT INTO #drugs
SELECT DISTINCT doc_id
           FROM query_term
          WHERE path = '/Term/SemanticType/@cdr:ref'
            AND int_val = (SELECT doc_id
                             FROM query_term
                            WHERE path = '/Term/PreferredName'
                              AND value = 'Drug/agent')""")
cursor.execute("""\
    DELETE FROM #drugs
          WHERE doc_id IN (SELECT doc_id FROM #defs)""")
cursor.execute("""\
    INSERT INTO #active
SELECT DISTINCT doc_id
           FROM query_term
          WHERE path IN ('/CTGovProtocol/OverallStatus',
                         '/InScopeProtocol/ProtocolAdminInfo' +
                         '/CurrentProtocolStatus')
            AND value IN ('Enrolling by Invitation', 'Active',
                          'Approved-Not Yet Active', 'Not Yet Active')""")
cursor.execute("""\
    INSERT INTO #links
SELECT DISTINCT q.int_val
           FROM query_term q
           JOIN #active a
             ON a.doc_id = q.doc_id
          WHERE q.path LIKE '/InScope/%/@cdr:ref'
             OR q.path LIKE '/CTGovProtocol/%/@cdr:ref'""")
cursor.execute("""\
SELECT DISTINCT n.doc_id AS "CDR ID", 
                n.value AS "Preferred Name"
           FROM query_term n
           JOIN #drugs d
             ON d.doc_id = n.doc_id
           JOIN #links l
             ON n.doc_id = l.doc_id
          WHERE n.path = '/Term/PreferredName'
       ORDER BY 1""")
rows = cursor.fetchall()
title = u"Drug Terms Without Definitions (But Linked by Active Trials)"
html = [u"""\
<html>
 <head>
  <title>%s</title>
  <style type='text/css'>
   * { font-family: Arial, sans-serif; font-size: 10pt; }
   h1 { font-size: 14pt; }
  </style>
 </head>
 <body>
  <h1>%s</h1>
  <table cellspacing='0' cellpadding='2' border='1'>
   <tr>
    <th>CDR ID</th>
    <th>Preferred Name</th>
   </tr>
""" % (title, title)]
for docId, termName in rows:
    html.append(u"""\
   <tr>
    <td>%d</td>
    <td>%s</td>
   </tr>
""" % (docId, cgi.escape(termName)))
html.append(u"""\
  </table>
  <p style='font-size: 8pt; color: green;'>%d rows, %.2f seconds</p>
 </body>
</html>""" % (len(rows), time.time() - start))
cdrcgi.sendPage(u"".join(html))
