import urllib, cdrdocobject, cdrdb, xml.dom.minidom, cgi

def getPerson(trackerId, persons, conn):
    filt = 'Person Contact Fragment With Name'
    cursor = conn.cursor()
    cursor.execute("""\
       SELECT int_val
         FROM query_term
        WHERE path = '/Mailer/Recipient/@cdr:ref'
          AND doc_id = ?""", trackerId)
    personId = cursor.fetchall()[0][0]
    cursor.close()
    if personId not in persons:
        person = cdrdocobject.Person.CipsContact(personId, conn, filt)
        persons[personId] = person
    return persons[personId]
    
class Trial:
    def __init__(self, node):
        self.cdrId = int(node.getAttribute('cdrId'))
        self.trackerId = int(node.getAttribute('trackerId'))
        self.protId = node.getAttribute('protId')
        self.posted = node.getAttribute('posted')

class Batch:
    def __init__(self, node, persons, conn):
        self.name = node.getAttribute('name')
        self.address = node.getAttribute('address')
        self.mailed = node.getAttribute('mailed')
        self.person = None
        self.lastResponse = None
        self.domain = self.address.split('@')[1]
        self.trials = []
        self.responses = 0
        for child in node.childNodes:
            if child.nodeName == 'Trial':
                trial = Trial(child)
                self.trials.append(trial)
                if trial.posted:
                    self.responses += 1
                    if trial.posted > self.lastResponse:
                        self.lastResponse = trial.posted
                if not self.person:
                    self.person = getPerson(trial.trackerId, persons, conn)
    def __cmp__(self, other):
        diff = cmp(self.domain, other.domain)
        if diff:
            return diff
        return cmp(self.name, other.name)
    def toHtml(self):
        rowClass = len(self.trials) > self.responses and 'slacker' or 'done'
        phone = org = "None"
        if self.person:
            phone = self.person.getPhone() or "None"
            orgs = self.person.getOrgs()
            if orgs:
                org = orgs[0]
        return u"""\
   <tr class='%s'>
    <td>%s</td>
    <td>%d</td>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (rowClass, cgi.escape(self.name), len(self.trials), self.responses,
       cgi.escape(phone),
       self.lastResponse, cgi.escape(org))

conn = cdrdb.connect('CdrGuest')
url = 'http://pdqupdate.cancer.gov/u/vmailer-status.py'
xmlDoc = urllib.urlopen(url).read()
dom = xml.dom.minidom.parseString(xmlDoc)
persons = {}
batches = []
for node in dom.documentElement.childNodes:
    if node.nodeName == 'Batch':
        batch = Batch(node, persons, conn)
        if batch.trials:
            batches.append(batch)
batches.sort()
html = [u"""\
<html>
 <head>
  <title>VMailer Status</title>
  <style type='text/css'>
   body { font-family: Arial, sans-serif; }
   h1 { font-size: 14pt; color: maroon; }
   th { color: blue; }
   th, td { font-size: 11pt; }
   .done { color: green; }
   .slacker { color: red; }
  </style>
 <body>
  <h1>VMailer Status</h1>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>Name</th>
    <th># Mailers</th>
    <th># Responses</th>
    <th>Phone</th>
    <th>Last Response</th>
    <th>Organization</th>
   </tr>
"""]
for batch in batches:
    html.append(batch.toHtml())
html.append(u"""\
  </table>
 </body>
</html>""")
html = u"".join(html).encode('utf-8')
print """\
Content-type: html; charset=utf-8
"""
print html
