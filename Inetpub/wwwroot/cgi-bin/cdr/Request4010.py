#----------------------------------------------------------------------
#
# $Id$
#
# Report on Oncore trials which are duplicates of trials we already
# have in the repository.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import urllib, cdrdb, cdr, cdrcgi, time, re

class Dup:
    def __init__(self, node, cursor):
        self.cdrId = node.attrib.get('DuplicateOf')
        self.oncoreId = node.attrib.get('OncoreID')
        self.title = u""
        self.nctIds = []
        self.originalIds = []
        self.firstPub = u""
        if self.cdrId:
            self.cdrId = int(re.sub("[^\\d]+", "", self.cdrId))
            cursor.execute("""\
                SELECT title, first_pub
                  FROM document
                 WHERE id = ?""", self.cdrId)
            rows = cursor.fetchall()
            if rows:
                self.title = rows[0][0]
                self.firstPub = rows[0][1] and str(rows[0][1])[:10]
            cursor.execute("""\
                SELECT t.value, i.value
                  FROM query_term t
                  JOIN query_term i
                    ON t.doc_id = i.doc_id
                   AND LEFT(t.node_loc, 8) = LEFT(i.node_loc, 8)
                 WHERE i.doc_id = ?
                   AND t.path IN ('/InScopeProtocol/ProtocolIDs/OtherID/IDType',
                              '/OutOfScopeProtocol/ProtocolIDs/OtherID/IDType')
                   AND i.path IN (
                           '/InScopeProtocol/ProtocolIDs/OtherID/IDString',
                           '/OutOfScopeProtocol/ProtocolIDs/OtherID/IDString')
                   AND t.value IN ('Institutional/Original',
                                   'ClinicalTrials.gov ID')""", self.cdrId)
            for idType, idString in cursor.fetchall():
                idString = idString.strip()
                if idString:
                    if idType == 'Institutional/Original':
                        self.originalIds.append(idString)
                    else:
                        self.nctIds.append(idString)
            cursor.execute("""\
                SELECT value
                  FROM query_term
                 WHERE path = '/CTGovProtocol/IDInfo/OrgStudyID'
                   AND doc_id = ?""", self.cdrId)
            for row in cursor.fetchall():
                self.originalIds.append(row[0].strip())
            cursor.execute("""\
                SELECT value
                  FROM query_term
                 WHERE path = '/CTGovProtocol/IDInfo/NCTID'
                   AND doc_id = ?""", self.cdrId)
            for row in cursor.fetchall():
                self.nctIds.append(row[0].strip())
    def toHtml(self):
        return u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (self.oncoreId,
       self.cdrId,
       self.nctIds and u" ".join(self.nctIds) or u"&nbsp;",
       self.originalIds and u" ".join(self.originalIds) or u"&nbsp;",
       self.firstPub or u"&nbsp;",
       self.title or u"&nbsp;")
etree  = cdr.importEtree()
host   = cdr.isProdHost() and cdr.EMAILER_PROD or cdr.EMAILER_DEV
url    = 'http://%s%s/oncore-id-mappings' % (host, cdr.EMAILER_CGI)
page   = urllib.urlopen(url).read()
tree   = etree.fromstring(page)
now    = time.strftime("%Y-%m-%d")
cursor = cdrdb.connect('CdrGuest').cursor()
dups   = [Dup(node, cursor) for node in tree.xpath('Trial[@DuplicateOf]')]
html   = [u"""\
<html>
 <head>
  <title>Oncore Duplicate Trials</title>
  <style type='text/css'>
   body { font-family: Arial, sans-serif }
   h1 { font-size: 1.3em }
   h1, h2 { text-align: center }
   h2, h3 { font-size: 1.1em }
   h1, h2, h3 { font-weight: bold }
   td, th { border: black 1px solid; padding: 3px }
   table { border-spacing: 0; border-collapse: collapse }
  </style>
 </head>
 <body>
  <h1>Oncore Duplicate Trials Report</h1>
  <h2>%s</h2>
  <h3>Trials marked as duplicates by CIAT: %d</h3>
  <table>
   <tr>
    <th>Oncore ID</th>
    <th>Duplicate of CDRID</th>
    <th>NCTID</th>
    <th>Institutional/OriginalID</th>
    <th>Date First Published</th>
    <th>DocTitle</th>
   </tr>
""" % (now, len(dups))]
for dup in dups:
    html.append(dup.toHtml())
html.append(u"""\
  </table>
 </body>
</html>
""")
html = u"".join(html)
cdrcgi.sendPage(html)
