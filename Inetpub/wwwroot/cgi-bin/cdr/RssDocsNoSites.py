#----------------------------------------------------------------------
#
# $Id: RssDocsNoSites.py,v 1.2 2006-05-17 01:40:32 bkline Exp $
#
# Report on RSS imports without sites.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2005/05/12 14:49:38  bkline
# New report for Sheri (request #1684).
#
#----------------------------------------------------------------------
import cdrdb, xml.dom.minidom, cdrcgi, cdr

class LeadOrg:
    def __init__(self, node):
        self.role  = None
        self.docId = None
        for child in node.childNodes:
            if child.nodeName == 'LeadOrganizationID':
                self.docId = child.getAttribute('cdr:ref')
            elif child.nodeName == 'LeadOrgRole':
                self.role = cdr.getTextContent(child)

class Doc:
    def __init__(self, cdrId, dom):
        self.cdrId = cdrId
        self.primaryID = None
        self.primaryLO = None
        self.status = None
        for node in dom.documentElement.childNodes:
            if node.nodeName == 'ProtocolIDs':
                self.primaryID = self.getPrimaryID(node)
            elif node.nodeName == 'ProtocolAdminInfo':
                self.getAdminInfo(node)
    def getPrimaryID(self, node):
        for child in node.childNodes:
            if child.nodeName == 'PrimaryID':
                for grandchild in child.childNodes:
                    if grandchild.nodeName == 'IDString':
                        return cdr.getTextContent(grandchild)
    def getAdminInfo(self, node):
        for child in node.childNodes:
            if child.nodeName == 'ProtocolLeadOrg':
                leadOrg = LeadOrg(child)
                if leadOrg.role == 'Primary':
                    self.primaryLO =  leadOrg.docId
            elif child.nodeName == 'CurrentProtocolStatus':
                self.status = cdr.getTextContent(child)
    def toHtml(self):
        return u"""\
   <tr>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (self.cdrId, self.primaryID, self.primaryLO, self.status or u"&nbsp;")

docs   = []
orgs   = {}
skip   = {}
conn   = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cdr.logwrite("RssDocsNoSites: starting")
cursor.execute("""\
    SELECT DISTINCT doc_id
               FROM query_term
              WHERE path LIKE '/InScopeProtocol/%/ExternalSite/%'""",
               timeout = 300)
for row in cursor.fetchall():
    skip[row[0]] = True
cdr.logwrite("RssDocsNoSites: skip %d docs with sites" % len(skip))
cursor.execute("""\
    SELECT d.cdr_id, doc.xml
      FROM import_doc d
      JOIN import_source s
        ON s.id = d.source
      JOIN import_disposition disp
        ON disp.id = d.disposition
      JOIN document doc
        ON doc.id = d.cdr_id
     WHERE s.name = 'RSS'
       AND disp.name = 'imported'
  ORDER BY d.cdr_id""", timeout = 300)
row = cursor.fetchone()
parsedDocs = 0
while row:
    cdrId, docXml = row
    if cdrId not in skip:
        parsedDocs += 1
        dom = xml.dom.minidom.parseString(docXml.encode('utf-8'))
        if not dom.getElementsByTagName('ExternalSite'):
            docs.append(Doc(cdrId, dom))
    row = cursor.fetchone()
cdr.logwrite("RssDocsNoSites: parsed %d docs" % parsedDocs)
path = '/Organization/OrganizationNameInformation/OfficialName/Name'
for doc in docs:
    if doc.primaryLO:
        values = cdr.getQueryTermValueForId(path, doc.primaryLO, conn)
        doc.primaryLO = values and values[0] or None
html = u"""\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>RSS Imports With No External Sites</title>
  <style type 'text/css'>
   body     { font-family: Arial, Helvetica, sans-serif }
   span.ti  { font-size: 14pt; font-weight: bold }
   span.sub { font-size: 12pt; font-weight: bold }
   th       { text-align: center; vertical-align: top; 
              font-size: 12pt; font-weight: bold }
   td       { text-align: left; vertical-align: top; 
              font-size: 12pt; font-weight: normal }
  </style>
 </head>
 <basefont face='Arial, Helvetica, sans-serif'>
 <body>
  <center>
   <span class='ti'>RSS Imports With No External Sites</span>
  </center>
  <br />
  <br />
  <table border='1' cellspacing='0' cellpadding='1'>
   <tr>
    <th>CDR ID</th>
    <th>Primary ID</th>
    <th>Primary LO</th>
    <th>Current Protocol Status</th>
   </tr>
"""
for doc in docs:
    html += doc.toHtml()
cdrcgi.sendPage(html + u"""\
  </table>
 </body>
</html>""")
