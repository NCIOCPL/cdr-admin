#----------------------------------------------------------------------
#
# $Id$
#
# Map Lab Analysis/Biomarker studies
#
# BZIssue:4487
# BZIssue:4532
#
#----------------------------------------------------------------------
import cdrdb, xml.dom.minidom, cdrdocobject, cgi, cdrcgi, time

def fix(me):
    if not me:
        return u""
    return cgi.escape(me)

start = time.time()
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()

cursor.execute("""\
    SELECT DISTINCT a.id, a.title
               FROM active_doc a
               JOIN query_term_pub t
                 ON t.doc_id = a.id
              WHERE t.path = '/InScopeProtocol/ProtocolDetail/StudyType'
                AND t.value = 'Research study'""", timeout = 300)
rows = cursor.fetchall()
statuses = ('Withdram from PDQ', 'Withdrawn', 'Active',
            'Approved-not yet active', 'Status not known',
            'Withdrawn from PDQ', 'Completed',
            'No valid lead organization status found.',
            'Temporarily closed', '', 'Enrolling by invitation') #, 'Closed')
protocols = {}
for docId, docTitle in rows:
    cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
    docXml = cursor.fetchall()[0][0]
    dom = xml.dom.minidom.parseString(docXml.encode('utf-8'))
    protocol = cdrdocobject.Protocol(docId, dom.documentElement)
    if protocol.hadStatus('2007-12-26', '2007-12-26', statuses):
        armsOrGroups = dom.getElementsByTagName('ArmsOrGroups')
        outcomes = dom.getElementsByTagName('Outcome')
        regInfo = dom.getElementsByTagName('RegulatoryInformation')
        interventions = dom.getElementsByTagName('Intervention')
        completionDates = dom.getElementsByTagName('CompletionDate')
        if not armsOrGroups or not outcomes:
            protocol.docTitle = docTitle
            protocol.armsOrGroups = armsOrGroups
            protocol.outcomes = outcomes
            protocol.regInfo = regInfo
            protocol.interventions = interventions
            protocol.completionDates = completionDates
            protocols[docId] = protocol
docIds = protocols.keys()
docIds.sort()
html = [u"""\
<html>
 <head>
  <title>Research Studies For Request 4487</title>
  <style type='text/css'>
   body { font-family: Arial, sans-serif; }
   h1   { font-size: 16pt; color: maroon; }
   table { border-spacing: 0; border-collapse: collapse; empty-cells: show; }
   th, td { font-size: 11pt; border: black solid 1px; }
   td { vertical-align: top; }
   th { color: blue; }
   .footnote { font-size: 8pt; color: green; margin-top: 25px; }
   .center { text-align: center; vertical-align: middle; }
  </style>
 </head>
 <body>
  <h1>Research Studies For Request 4487</h1>
  <table>
   <tr>
    <th>CDR ID</th>
    <th>Doc Title</th>
    <th>Current Protocol Status</th>
    <th>Has ArmsOrGroups?</th>
    <th>Has Outcome?</th>
    <th>Has Intervention?</th>
    <th>Has RegulatoryInformation?</th>
    <th>Has CompletionDate?</th>
   </tr>
"""]
for docId in docIds:
    protocol = protocols[docId]
    html.append(u"""\
   <tr>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
    <td class='center'>%s</td>
    <td class='center'>%s</td>
    <td class='center'>%s</td>
    <td class='center'>%s</td>
    <td class='center'>%s</td>
   </tr>
""" % (docId, fix(protocol.docTitle), protocol.status,
       protocol.armsOrGroups and u"X" or u"",
       protocol.outcomes and u"X" or u"",
       protocol.interventions and u"X" or u"",
       protocol.regInfo and u"X" or u"",
       protocol.completionDates and u"X" or u""))
elapsed = time.time() - start
footnote = "[%d rows; processing time %d milliseconds]" % (len(docIds), 
                                                           int(1000*elapsed))
html.append(u"""\
  </table>
  <div class='footnote'>%s</div>
 </body>
</html>
""" % footnote)
cdrcgi.sendPage(u"".join(html))
