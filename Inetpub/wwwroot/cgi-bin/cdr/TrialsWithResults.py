#----------------------------------------------------------------------
#
# $Id$
#
# Summary list of published clinical trial results by CTEP ID.  This
# is one of three services provided for CTEP.  This service requires
# no parameters, and returns a single XML response document in the form:
#
#  <TrialsWithResults>
#    <Trial ctepid='...'>
#      <Article pmid='...' date='yyyy-mm-dd'/>
#      <Article pmid='...' date='yyyy-mm-dd'/>
#      :
#      :
#    </Trial>
#    <Trial ctepid='...'>
#      <Article pmid='...' date='yyyy-mm-dd'/>
#      :
#    </Trial>
#      :
#      :
#  </TrialsWithResults>
#
# Program logic:
#
# 1. Collect all trials which have a CTEP ID
# 2. Collect PubMed ID and date of last CDR version for all Citations
# 3. For each trial from step 1:
#    * If there is at least one PublishedResult or RelatedPublication:
#      * Include the trial in the response, with its CTEP ID
#      * For each PublishedResult or RelatedPublication article:
#        * List the article's ID and date from step 2
#
# See also:
#   GetPubResults.py
#   LookupNctId.py
#
# BZIssue::1408
# BZIssue::1579
#
#----------------------------------------------------------------------
import cdr, cdrdb, re

class Citation:
    def __init__(self, id):
        self.cdrId      = id
        self.pmid       = None
        self.date       = None
        lastVersions    = cdr.lastVersions('guest', 'CDR%d' % id)
        lastPub         = lastVersions[1]
        if lastPub == -1:
            raise Exception('no publishable versions for citation CDR%d' % id)
        cursor.execute("""\
            SELECT dt
              FROM doc_version
             WHERE id = ?
               AND num = ?""", (id, lastPub))
        rows = cursor.fetchall()
        self.date = str(rows[0][0])[:10]
        cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE path IN ('/Citation/PubmedArticle/NCBIArticle/PMID',
                            '/Citation/PubmedArticle/MedlineCitation/PMID')
               AND doc_id = ?""", id)
        rows = cursor.fetchall()
        if not rows:
            raise Exception("CDR%d: no PMID found" % id)
        self.pmid = rows[0]

pattern = re.compile(r"[-\s]")
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
    CREATE TABLE #ctep_trials
         (cdr_id INTEGER,
         ctep_id VARCHAR(255))""")
conn.commit()
cursor.execute("""\
    CREATE TABLE #pm_cites
         (cdr_id INTEGER,
             ver INTEGER,
            pmid VARCHAR(16),
        ver_date DATETIME NULL)""")
conn.commit()
cursor.execute("""\
       INSERT INTO #ctep_trials
   SELECT DISTINCT c.doc_id, c.value
              FROM query_term c
              JOIN query_term ct
                ON ct.doc_id = c.doc_id
             WHERE c.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
               AND ct.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
               AND LEFT(c.node_loc, 8) = LEFT(ct.node_loc, 8)
               AND ct.value = 'CTEP ID'""")
conn.commit()
cursor.execute("""\
        INSERT INTO #pm_cites (cdr_id, ver, pmid)
             SELECT q.doc_id, MAX(v.num), q.value
               FROM query_term q
               JOIN doc_version v
                 ON v.id = q.doc_id
              WHERE path = '/Citation/PubmedArticle/MedlineCitation/PMID'
           GROUP BY q.doc_id, q.value""")
conn.commit()
cursor.execute("""\
        INSERT INTO #pm_cites (cdr_id, ver, pmid)
             SELECT q.doc_id, MAX(v.num), q.value
               FROM query_term q
               JOIN doc_version v
                 ON v.id = q.doc_id
              WHERE path = '/Citation/PubmedArticle/NCBIArticle/PMID'
           GROUP BY q.doc_id, q.value""")
conn.commit()
cursor.execute("""\
        UPDATE #pm_cites
           SET ver_date = (SELECT dt
                             FROM doc_version
                            WHERE id = cdr_id
                              AND num = ver)""")
citations = {}
cursor.execute("SELECT cdr_id, pmid, ver_date FROM #pm_cites")
rows = cursor.fetchall()
for row in rows:
    citations[row[0]] = (row[1].strip(), row[2])
cursor.execute("""\
        SELECT t.ctep_id, c.int_val
          FROM #ctep_trials t
          JOIN query_term c
            ON c.doc_id = t.cdr_id
         WHERE c.path IN ('/InScopeProtocol/PublishedResults' +
                          '/Citation/@cdr:ref',
                          '/InScopeProtocol/RelatedPublications' +
                          '/RelatedCitation/@cdr:ref')""")
rows = cursor.fetchall()
trialCitationSets = {}
for ctepId, citeId in rows:
    ctepId = ctepId.strip()
    if citeId in citations:
        if ctepId in trialCitationSets:
            trialCitationSet = trialCitationSets[ctepId]
        else:
            trialCitationSet = trialCitationSets[ctepId] = set()
        trialCitationSet.add(citeId)
ctepIds = trialCitationSets.keys()
ctepIds.sort()
lines = ["<TrialsWithResults>"]
for ctepId in ctepIds:
    citeIds = list(trialCitationSets[ctepId])
    citeIds.sort(lambda a,b: cmp(citations[a][0], citations[b][0]))
    lines.append(" <Trial ctepid='%s'>" % ctepId.strip())
    for citeId in citeIds:
        cite = citations[citeId]
        lines.append("  <Article pmid='%s' date='%s'/>" % (cite[0].strip(),
                                                           cite[1][:10]))
    lines.append(" </Trial>")
lines.append("</TrialsWithResults>")
print "Content-type: text/xml"
print ""
print '\n'.join(lines)
