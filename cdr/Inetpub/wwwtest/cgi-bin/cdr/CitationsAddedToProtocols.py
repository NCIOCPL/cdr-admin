#----------------------------------------------------------------------
#
# $Id: CitationsAddedToProtocols.py,v 1.1 2005-08-29 20:32:23 bkline Exp $
#
# We need a report to check which citations (Published Results and Related
# Publications) have been added to protocols in a given time frame. It will
# use the <EntryDate> within the Published Results and Related Publications
# element in the Protocol document.The Glossary Terms by Status Report will
# server as a QC report to check which glossary terms were created within a
# given time frame with a particular status set.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, cdrcgi, string, time, xml.dom.minidom

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = fields and fields.getvalue("Session") or None
request  = cdrcgi.getRequest(fields)
fromDate = fields and fields.getvalue('FromDate') or None
toDate   = fields and fields.getvalue('ToDate') or None
title    = "CDR Administration"
instr    = "Citations Added to Protocols Report"
buttons  = ["Submit Request", "Report Menu", cdrcgi.MAINMENU, "Log Out"]
script   = "CitationsAddedToProtocols.py"
header   = cdrcgi.header(title, title, instr, script, buttons)
   

#----------------------------------------------------------------------
# Handle requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == "Report Menu":
    cdrcgi.navigateTo("Reports.py", session)
elif request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# As the user for the report parameters.
#----------------------------------------------------------------------
if not fromDate or not toDate:
    now         = time.localtime(time.time())
    toDateNew   = time.strftime("%Y-%m-%d", now)
    then        = list(now)
    then[1]    -= 1
    then[2]    += 1
    then        = time.localtime(time.mktime(then))
    fromDateNew = time.strftime("%Y-%m-%d", then)
    toDate      = toDate or toDateNew
    fromDate    = fromDate or fromDateNew
    form        = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <TABLE BORDER='0'>
    <TR>
     <TD><B>Start Date:&nbsp;</B></TD>
     <TD><INPUT NAME='FromDate' VALUE='%s'>&nbsp;
         (use format YYYY-MM-DD for dates, e.g. 2005-06-22)</TD>
    </TR>
    <TR>
     <TD><B>End Date:&nbsp;</B></TD>
     <TD><INPUT NAME='ToDate' VALUE='%s'>&nbsp;</TD>
    </TR>
   </TABLE>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session, fromDate, toDate)
    cdrcgi.sendPage(header + form)

def extractIntVal(v):
    try:
        idForms = cdr.exNormalize(v)
        return idForms[1]
    except Exception, e:
        cdrcgi.bail("extractIntVal: %s" % str(e))

class Citation:
    def __init__(self, node, protocol):
        self.citeId     = None
        self.citeSource = None
        self.enteredBy  = None
        self.entryDate  = None
        self.protocol   = protocol
        for child in node.childNodes:
            if child.nodeName in ('RelatedCitation', 'Citation'):
                docId = child.getAttribute('cdr:ref')
                self.citeId = extractIntVal(docId)
            elif child.nodeName == 'CitationSource':
                self.citeSource = cdr.getTextContent(child).strip()
            elif child.nodeName == 'EnteredBy':
                self.enteredBy = cdr.getTextContent(child).strip()
            elif child.nodeName == 'EntryDate':
                self.entryDate = cdr.getTextContent(child).strip()
    def makeLink(self, session):
        url = u"QcReport.py?DocId=CDR%010d&Session=%s" % (self.citeId, session)
        return u"<a href='%s'>%d</a>" % (url, self.citeId)

class Protocol:
    def __init__(self, id, versions):
        self.id = id
        if versions[0] != -1 and versions[0] == versions[1]:
            self.lastVersionPublishable = True
        else:
            self.lastVersionPublishable = False

relatedPublications = []
publishedResults = []
protocols = {}
rpProtocols = {}
prProtocols = {}
rpCitations = {}
prCitations = {}

#----------------------------------------------------------------------
# Create/display the report.
#----------------------------------------------------------------------
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
    SELECT DISTINCT doc_id
               FROM query_term
              WHERE path IN ('/InScopeProtocol/RelatedPublications/EntryDate',
                             '/InScopeProtocol/PublishedResults/EntryDate')
                AND value BETWEEN '%s' AND '%s'""" % (fromDate, toDate))
for row in cursor.fetchall():
    versions = cdr.lastVersions('guest', 'CDR%010d' % row[0])
    protocol = Protocol(row[0], versions)
    cursor.execute("SELECT xml FROM document WHERE id = ?", row[0])
    dom = xml.dom.minidom.parseString(cursor.fetchall()[0][0].encode('utf-8'))
    for node in dom.documentElement.childNodes:
        if node.nodeName == 'RelatedPublications':
            citation = Citation(node, protocol)
            if citation.entryDate >= fromDate and citation.entryDate <= toDate:
                relatedPublications.append(citation)
                rpProtocols[row[0]] = protocol
                rpCitations[citation.citeId] = citation
        if node.nodeName == 'PublishedResults':
            citation = Citation(node, protocol)
            if citation.entryDate >= fromDate and citation.entryDate <= toDate:
                publishedResults.append(citation)
                prProtocols[row[0]] = protocol
                prCitations[citation.citeId] = citation
def sorter(a, b):
    protIdCmp = cmp(a.protocol.id, b.protocol.id)
    if protIdCmp:
        return protIdCmp
    return cmp(a.citeId, b.citeId)

def makeTable(citations, html):
    html.append(u"""\
  <table border='1' cellspacing='0' cellpadding='2'>
   <tr>
    <th>Protocol CDR ID</th>
    <th>Citation CDR ID</th>
    <th>Citation Source</th>
    <th>Entered by</th>
    <th>Entry Date</th>
    <th>Last Version Pub?</th>
   </tr>""")
    citations.sort(sorter)
    for citation in citations:
        html.append(u"""\
   <tr>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>""" % (citation.protocol.id,
               citation.makeLink(session),
               citation.citeSource,
               citation.enteredBy,
               citation.entryDate,
               citation.protocol.lastVersionPublishable and "Y" or "N"))
    html.append(u"""\
  </table>""")
    
html = [u"""\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Citations Added to Protocols</title>
  <style type 'text/css'>
   body    { font-family: Arial, Helvetica, sans-serif }
   .t1     { font-size: 14pt; font-weight: bold }
   .t2     { font-size: 12pt; font-weight: bold }
   th      { font-size: 12pt; font-weight: bold }
   td      { font-size: 12pt; font-weight: normal }
  </style>
 </head>
 <body>
  <center>
   <span class='t1'>Citations Added to Protocols</span>
   <br />
   <br />
   <span class='t2'>%s to %s</span>
  </center>
  <span class='t1'><u>Published Results</u> - %d</span><br />
  <span class='t2'>Unique Citations - %d</span><br />
  <span class='t2'>Unique Protocols - %d</span><br />""" %
        (fromDate, toDate, len(publishedResults), len(prCitations),
         len(prProtocols))]
makeTable(publishedResults, html)
html.append(u"""\
  <br />
  <br />
  <span class='t1'><u>Related Publications</u> - %d</span><br />
  <span class='t2'>Unique Citations - %d</span><br />
  <span class='t2'>Unique Protocols - %d</span><br />""" %
            (len(relatedPublications), len(rpCitations), len(rpProtocols)))
makeTable(relatedPublications, html)
html.append(u"""\
 </body>
</html>
""")
cdrcgi.sendPage(u"\n".join(html))
