#----------------------------------------------------------------------
#
# $Id$
#
# Mapped orgs without phones.
#
#----------------------------------------------------------------------
import cdrdb

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("CREATE TABLE #t (id INTEGER, flag CHAR)")
conn.commit()
cursor.execute("""\
    INSERT INTO #t
         SELECT m.doc_id, 'N'
           FROM external_map m
           JOIN external_map_usage u
             ON u.id = m.usage
          WHERE u.name = 'CTEP_Institution_Code'
            AND m.doc_id IS NOT NULL""")
conn.commit()
cursor.execute("""\
    UPDATE #t
       SET flag = 'Y'
     WHERE id IN (SELECT doc_id
                    FROM query_term
                   WHERE path = '/Organization/OrganizationLocations'
                              + '/ClinicalTrialsOfficeContact'
                              + '/ClinicalTrialsOfficeContactPhone'
                     AND value IS NOT NULL
                     AND value <> '')""")
conn.commit()
cursor.execute("""\
    UPDATE #t
       SET flag = 'Y'
     WHERE id IN (SELECT p.doc_id
                    FROM query_term p
                    JOIN query_term i
                      ON i.doc_id = p.doc_id
                     AND LEFT(i.node_loc, 8) = LEFT(p.node_loc, 8)
                    JOIN query_term c
                      ON c.doc_id = p.doc_id
                     AND c.value  = i.value
                   WHERE p.path = '/Organization/OrganizationLocations'
                                + '/OrganizationLocation/Location/Phone'
                     AND i.path = '/Organization/OrganizationLocations'
                                + '/OrganizationLocation/Location/@cdr:id'
                     AND c.path = '/Organization/OrganizationLocations'
                                + '/CIPSContact'
                     AND c.value <> '')""")
conn.commit()
cursor.execute("""\
    UPDATE #t
       SET flag = 'Y'
     WHERE id IN (SELECT p.doc_id
                    FROM query_term p
                    JOIN query_term i
                      ON i.doc_id = p.doc_id
                     AND LEFT(i.node_loc, 8) = LEFT(p.node_loc, 8)
                    JOIN query_term c
                      ON c.doc_id = p.doc_id
                     AND c.value  = i.value
                   WHERE p.path = '/Organization/OrganizationLocations'
                                + '/OrganizationLocation/Location'
                                + '/TollFreePhone'
                     AND i.path = '/Organization/OrganizationLocations'
                                + '/OrganizationLocation/Location/@cdr:id'
                     AND c.path = '/Organization/OrganizationLocations'
                                + '/CIPSContact'
                     AND c.value <> '')""")
conn.commit()
#cursor.execute("SELECT COUNT(*) FROM #t")
#print cursor.fetchall()[0][0]
cursor.execute("SELECT DISTINCT id FROM #t WHERE flag = 'N'")
rows = cursor.fetchall()
print """\
Content-type: text/plain
"""
for row in rows:
    print row[0]
