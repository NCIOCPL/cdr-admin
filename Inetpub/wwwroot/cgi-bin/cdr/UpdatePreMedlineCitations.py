#----------------------------------------------------------------------
# Update premedline citations that have had their statuses changed
# since they were last imported or updated.
#
# BZIssue::5150
#----------------------------------------------------------------------
import cdr, cdrdb, lxml.etree as etree, cgi, cdrcgi, copy
import requests

class Citation:
    def __init__(self, pmId, cdrId, status):
        self.pmId = pmId.strip()
        self.cdrId = cdrId
        self.status = status.strip()
        self.pubmedArticle = None
    def updateDoc(self):
        if not self.pubmedArticle:
            raise Exception("PubmedArticle %s dropped" % self.pmId)
        node = copy.deepcopy(self.pubmedArticle.node)
        etree.strip_elements(node, "CommentsCorrectionsList")
        obj = cdr.getDoc(session, self.cdrId, 'Y', getObject=True)
        errors = cdr.checkErr(obj)
        if errors:
            raise Exception("getDoc(): %s" % cgi.escape(errors))
        doc = etree.XML(obj.xml)
        for child in doc.findall("PubmedArticle"):
            doc.replace(child, node)
            obj.xml = etree.tostring(doc, xml_declaration=True,
                                     encoding="utf-8")
            comment = "pre-medline citation updated (issue #5150)"
            response = cdr.repDoc(session, doc=str(obj), val="Y", ver="Y",
                                  checkIn="Y", showWarnings=True,
                                  reason=comment, comment=comment)
            if response[0]:
                return "updated"
            raise Exception("repDoc(): %s" % repr(response[1]))
        raise Exception("PubmedArticle missing from CDR document")

class PubmedArticle:
    class PMID:
        def __init__(self, node):
            try:
                self.version = int(node.get("Version"))
            except:
                self.version = 0
            self.value = node.text.strip()
        def __repr__(self):
            return repr("PMID", self.version, self.value)
        def __cmp__(self, other):
            return cmp(self.version, other.version)
    def __init__(self, node):
        self.node = node
        self.pmIds = []
        self.status = None
        for child in node.findall("MedlineCitation"):
            self.status = child.get("Status")
            for grandchild in child.findall("PMID"):
                self.pmIds.append(self.PMID(grandchild))
        self.pmIds.sort()
    def getLastId(self):
        return self.pmIds and self.pmIds[-1].value or None

def displayErrors(errors):
    if not errors:
        return u""
    html = [u'<p class="errors">']
    sep = u""
    for error in errors:
        html.append(cgi.escape(error))
        html.append(sep)
        sep = u"<br />"
    html.append(u"</p>")
    return u"".join(html)

errors = []
url = "http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
fields = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
if not session:
    cdrcgi.bail("Not logged in")
error = cdr.checkErr(session)
if error:
    cdrcgi.bail(error)
if not cdr.canDo(session, "MODIFY DOCUMENT", "Citation"):
    cdrcgi.bail("You must be authorized to replace Citation documents "
                "to run this script.")
cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
SELECT DISTINCT s.doc_id, s.value, i.value
           FROM query_term s
           JOIN query_term i
             ON i.doc_id = s.doc_id
          WHERE s.path = '/Citation/PubmedArticle/MedlineCitation/@Status'
            AND i.path = '/Citation/PubmedArticle/MedlineCitation/PMID'
            AND s.value IN ('In-Process', 'Publisher', 'In-data-review')""")
citations = {}
pmIds = set()
for cdrId, status, pmId in cursor.fetchall():
    pmIds.add(pmId)
    if pmId in citations:
        errors.append("%s for CDR%d (%s) and CDR%d (%s)" %
                      (pmId, cdrId, status,
                       citations[pmId].cdrId, citations[pmId].status))
    else:
        citations[pmId] = Citation(pmId, cdrId, status)
data = {
    "db": "pubmed",
    "id": ",".join(list(pmIds)),
    "retmode": "xml"
}
docXml = requests.post(url, data).content
## fp = open("nlm-reply.xml", "w")
## fp.write(docXml)
## fp.close()
doc = etree.XML(docXml)
for node in doc.findall("PubmedArticle"):
    article = PubmedArticle(node)
    if len(article.pmIds) != 1:
        errors.append("PMIDs: " + repr(article.pmIds))
        continue
    pmId = article.getLastId()
    if pmId in citations:
        citations[pmId].pubmedArticle = article
    else:
        errors.append("unexpected article with PMID %s" % pmid)
html = [u"""\
<html>
 <head>
  <title>Citation Status Changes</title>
  <style type="text/css">
   .errors { font-weight: bold; color: red }
   h1 { color: maroon; font-size: 16pt }
  </style>
 </head>
 <body>
  <h1>Citation Status Changes</h1>
  %s
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>PMID</th>
    <th>CDR ID</th>
    <th>Old Status</th>
    <th>New Status</th>
    <th>Notes</th>
   </tr>
""" % displayErrors(errors)]
changed = updated = 0
for pmid in citations:
    citation = citations[pmid]
    pubmedStatus = None
    if citation.pubmedArticle:
        pubmedStatus = citation.pubmedArticle.status
    if citation.status != pubmedStatus:
        changed += 1
        try:
            notes = citation.updateDoc()
            updated += 1
        except Exception, e:
            notes = '<span class="errors">%s</span>' % cgi.escape(str(e))
        cdr.unlock(session, citation.cdrId)
        html.append(u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (citation.pmId, citation.cdrId, citation.status,
       pubmedStatus or "<span class='errors'>Missing</span>",
       notes))
html.append(u"""\
  </table>
 </body>
 <p style='color: green'
 >%d pre-medline citations examined; %d statuses changed</p>
 </html>""" % (len(citations), changed))
cdrcgi.sendPage(u"".join(html))
