import cdrdb, xml.dom.minidom, cdr, cdrcgi, cgi, sys

def fix(me):
    return me and cgi.escape(me) or u"&nbsp;"

class ProtId:
    def __init__(self, node, idType = None):
        self.idType = idType
        self.value  = None
        for child in node.childNodes:
            if child.nodeName == 'IDString':
                self.value = cdr.getTextContent(child).strip()
            elif not idType and child.nodeName == 'IDType':
                self.idType = cdr.getTextContent(child).strip()

class Trial:
    def __init__(self, cdrId, cursor):
        self.cdrId   = cdrId
        self.protId  = None
        self.ctgovId = None
        self.title   = None
        cursor.execute("SELECT xml FROM document WHERE id = ?", cdrId)
        try:
            rows = cursor.fetchall()
            dom = xml.dom.minidom.parseString(rows[0][0].encode('utf-8'))
        except:
            self.title = u"UNABLE TO PARSE DOCUMENT"
            sys.stderr.write("cdrId=%s\n" % cdrId)
            raise
            return
        for node in dom.documentElement.childNodes:
            if node.nodeName == 'ProtocolTitle':
                if node.getAttribute('Type') == 'Original':
                    title = cdr.getTextContent(node).strip()
                    if title:
                        self.title = title
            elif node.nodeName == 'ProtocolIDs':
                for child in node.childNodes:
                    if child.nodeName == 'PrimaryID':
                        protId = ProtId(child, 'Primary')
                        if protId.value:
                            self.protId = protId.value
                    if child.nodeName == 'OtherID':
                        protId = ProtId(child)
                        if protId.idType == 'ClinicalTrials.gov ID':
                            if protId.value:
                                self.ctgovId = protId.value
                                
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
   SELECT DISTINCT sponsor.doc_id
              FROM query_term sponsor
              JOIN query_term prot_source
                ON sponsor.doc_id = prot_source.doc_id
              JOIN query_term prot_status
                ON sponsor.doc_id = prot_status.doc_id
             WHERE sponsor.path     = '/InScopeProtocol/ProtocolSponsors'
                                    + '/SponsorName'
               AND prot_source.path = '/InScopeProtocol/ProtocolSources'
                                    + '/ProtocolSource/SourceName'
               AND prot_status.path = '/InScopeProtocol/ProtocolAdminInfo'
                                    + '/CurrentProtocolStatus'
               AND sponsor.value = 'Pharmaceutical/Industry'
               AND prot_status.value IN ('Active', 'Approved-not yet active',
                                         'Temporarily closed')
               AND prot_source.value IN ('NCI designated Cancer Center',
                                         'Investigator/contact email ' +
                                         'submission',
                                         'Investigator/contact mail ' +
                                         'submission',
                                         'Investigator/contact web submission')
                                         """)
trials = []
for row in cursor.fetchall():
    trials.append(Trial(row[0], cursor))
trials.sort(lambda a,b: cmp(a.protId, b.protId))
html = [u"""\
<html>
 <head>
  <title>InScope Pharmaceutical Trials</title>
  <style type='text/css'>
   body { font-family: Arial; }
   h1   { font-size: 14pt; color: blue; }
   td, th { font-size: 10pt; }
   th   { color: green; }
   td   { color: maroon; }
  </style>
 </head>
 <body>
  <center><h1>InScope Pharmaceutical Trials</h1></center>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>Primary ID</th>
    <th>CTGov ID</th>
    <th>Original Title</th>
   </tr>
"""]
for trial in trials:
    html.append(u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (fix(trial.protId), fix(trial.ctgovId), fix(trial.title)))
html.append(u"""\
  </table>
 </body>
</html>
""")
cdrcgi.sendPage(u"".join(html))
