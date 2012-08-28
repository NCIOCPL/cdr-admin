#----------------------------------------------------------------------
#
# $Id$
#
# Report for missing ClinicalTrialOfficeContactPhone
#
# BZIssue::1816
#
#----------------------------------------------------------------------
import cdrdb, sys, time, xml.sax.saxutils, cdr, cdrcgi

def fix(me):
    return me and  xml.sax.saxutils.escape(me) or u""

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("CREATE TABLE #prots (id INTEGER)")
conn.commit()
cursor.execute("""\
    INSERT INTO #prots
SELECT DISTINCT doc_id
           FROM query_term
          WHERE path = '/InScopeProtocol/ProtocolAdminInfo'
                     + '/CurrentProtocolStatus'
            AND value IN ('Active',
                          'Approved-not yet active',
                          'Temporarily closed')""")
conn.commit()
#sys.stderr.write("%s protocols\n" % cursor.rowcount)
cursor.execute("CREATE TABLE #orgs_with_phones (id INTEGER)")
conn.commit()
cursor.execute("""\
    INSERT INTO #orgs_with_phones
SELECT DISTINCT doc_id
           FROM query_term
          WHERE path = '/Organization/OrganizationLocations'
                     + '/ClinicalTrialsOfficeContact'
                     + '/ClinicalTrialsOfficeContactPhone'
            AND value <> ''""")
conn.commit()
#sys.stderr.write("%d orgs with phones\n" % cursor.rowcount)
cursor.execute("""\
    CREATE TABLE #orgs
             (id INTEGER,
            name NVARCHAR(255),
          nprots INTEGER)""")
conn.commit()
cursor.execute("""\
    INSERT INTO #orgs
         SELECT q.int_val, d.title, COUNT(DISTINCT q.doc_id)
           FROM query_term q
           JOIN #prots p
             ON p.id = q.doc_id
           JOIN document d
             ON d.id = q.int_val
           JOIN doc_type t
             ON t.id = d.doc_type
          WHERE t.name = 'Organization'
            AND q.path LIKE '/InScopeProtocol/%/@cdr:ref'
            AND q.int_val NOT IN (SELECT id FROM #orgs_with_phones)
       GROUP BY q.int_val, d.title""", timeout = 300)
#sys.stderr.write("%d orgs without phones\n" % cursor.rowcount)
conn.commit()
class Org:
    def __init__(self, docId, name, numProtocols):
        self.docId  = docId
        self.nProts = numProtocols
        self.name   = name.split(u';')[0]
        self.url    = None
cursor.execute("""\
    CREATE TABLE #us_orgs
             (id INTEGER,
            name NVARCHAR(255),
          nprots INTEGER)""")
conn.commit()
cursor.execute("""\
        INSERT INTO #us_orgs
    SELECT DISTINCT o.id, o.name, o.nprots
               FROM #orgs o
               JOIN query_term c
                 ON c.doc_id = o.id
              WHERE c.path LIKE '/Organization/%/Country/@cdr:ref'
                AND c.int_val = (SELECT doc_id
                                   FROM query_term
                                  WHERE path = '/Country/ISOAlpha2CountryCode'
                                    AND value = 'US')""")
#sys.stderr.write("%d US orgs without phones\n" % cursor.rowcount)
conn.commit()
orgs = {}
cursor.execute("SELECT * FROM #us_orgs")
for docId, title, nProts in cursor.fetchall():
    orgs[docId] = Org(docId, title, nProts)
cursor.execute("""\
    SELECT u.doc_id, u.value
      FROM query_term u
      JOIN #us_orgs o
        ON o.id = u.doc_id
     WHERE u.path = '/Organization/OrganizationLocations'
                  + '/OrganizationLocation/Location/WebSite/@cdr:xref'""")
rows = cursor.fetchall()
#sys.stderr.write("%d URLs loaded\n" % len(rows))
for docId, url in rows:
    if not orgs[docId].url:
        orgs[docId].url = url
keys = orgs.keys()
keys.sort(lambda a,b: cmp(orgs[a].docId, orgs[b].docId))
row = 2
doc = [u"<Book>",
       u" <Sheet name='Orgs without phones'>",
       u"  <Cell row='1' col='1'>CDR ID</Cell>",
       u"  <Cell row='1' col='2'>Org Name</Cell>",
       u"  <Cell row='1' col='3'>Protocols</Cell>",
       u"  <Cell row='1' col='4'>URL</Cell>"]
for key in keys:
    org = orgs[key]
    doc.append(u"  <Cell row='%d' col='1'>%d</Cell>" % (row, org.docId))
    doc.append(u"  <Cell row='%d' col='2'>%s</Cell>" % (row, fix(org.name)))
    doc.append(u"  <Cell row='%d' col='3'>%s</Cell>" % (row, org.nProts))
    doc.append(u"  <Cell row='%d' col='4'>%s</Cell>" % (row, fix(org.url)))
    row += 1
doc.append(u" </Sheet>")
doc.append(u"</Book>")
doc = u"\n".join(doc)
now = time.strftime("%Y%m%d%H%M%S")
xmlName = "d:/cdr/reports/Request1816-%s.xml" % now
xlsName = "d:/cdr/reports/Request1816-%s.xls" % now
script = "d:/cdr/bin/XmlToXls.pl"
fp = open(xmlName, "wb")
fp.write(doc.encode('utf-8'))
fp.close()
command = "%s %s %s" % (script, xmlName, xlsName)
result = cdr.runCommand(command)
if result.code:
    cdrcgi.bail(result.output)
else:
    url = "http://%s/CdrReports/Request1816-%s.xls" % (cdrcgi.WEBSERVER, now)
    print "Location:%s\n\n" % url
