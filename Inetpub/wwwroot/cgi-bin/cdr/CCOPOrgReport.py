#----------------------------------------------------------------------
#
# $Id: CCOPOrgReport.py,v 1.3 2004-03-30 21:13:47 bkline Exp $
#
# The NCI Funded CCOP/MBCCOP Organization Report will serve as an
# additional QC report to check the accuracy of Principal Investigator's
# and Complex Affiliations on CCOP/MBCCOP's records and to identify
# co-investigators that need to be removed from documents.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2004/03/29 21:34:17  bkline
# Modified logic to only pick up active persons.
#
# Revision 1.1  2004/03/23 21:44:39  bkline
# New report for Sheri (see Bugzilla entry #1117).
#
#----------------------------------------------------------------------
import cdr, cdrdb, cgi, cdrcgi, xml.dom.minidom

#NCI-funded minority community clinical oncology program
#NCI-funded community clinical oncology program

#----------------------------------------------------------------------
# Establish a couple of database connections.
#----------------------------------------------------------------------
conn   = cdrdb.connect('CdrGuest')
cursor = conn.cursor()

#----------------------------------------------------------------------
# Initialize some collections.
#----------------------------------------------------------------------
orgs          = {}
persons       = {}
states        = {}
orgShortNames = {}

#----------------------------------------------------------------------
# Conditional debugging.
#----------------------------------------------------------------------
DEBUGGING = 0
def debugLog(what):
    if DEBUGGING:
        import sys
        sys.stderr.write(what)
        sys.stderr.write('\n')

#----------------------------------------------------------------------
# Find all the organizations.
#----------------------------------------------------------------------
class Organization:
    def __init__(self, id):
        self.id      = id
        self.name    = None
        self.state   = None
        self.persons = []
        cursor.execute("SELECT xml FROM document WHERE id = ?", id)
        rows = cursor.fetchall()
        dom = xml.dom.minidom.parseString(rows[0][0].encode('utf-8'))
        for node in dom.documentElement.childNodes:
            if node.nodeName == 'OrganizationNameInformation':
                self.name = self.__getName(node)
            elif node.nodeName == 'OrganizationLocations':
                self.state = self.__getState(node)
        self.__loadPersons()
        debugLog("organization %d: %s [%s]" % (id, self.name, self.state))
    def __getName(self, node):
        for child in node.childNodes:
            if child.nodeName == 'OfficialName':
                for grandChild in child.childNodes:
                    if grandChild.nodeName == 'Name':
                        return cdr.getTextContent(grandChild)
    def __getState(self, node):
        locs = {}
        cipsContact = None
        for child in node.childNodes:
            #debugLog("Node Name: %s" % child.nodeName)
            if child.nodeName == 'OrganizationLocation':
                loc = self.Location(child)
                locs[loc.id] = loc
            elif child.nodeName == 'CIPSContact':
                cipsContact = cdr.getTextContent(child)
        if cipsContact and locs.has_key(cipsContact):
            return locs[cipsContact].state
    def __loadPersons(self):
        cursor.execute("""\
   SELECT DISTINCT d.id, d.title
              FROM document d
              JOIN query_term q
                ON q.doc_id = d.id
              JOIN query_term s
                ON s.doc_id = d.id
             WHERE q.path = '/Person/PersonLocations/OtherPracticeLocation' +
                            '/OrganizationLocation/@cdr:ref'
               AND q.int_val = ?
               AND s.path = '/Person/Status/CurrentStatus'
               AND s.value = 'Active'""", self.id)
        rows = cursor.fetchall()
        for row in rows:
            self.persons.append(self.Person(row[0], row[1]))
    class Location:
        def __init__(self, node):
            self.state = None
            self.id    = None
            for child in node.childNodes:
                if child.nodeName == 'Location':
                    self.id = child.getAttribute('cdr:id')
                    for gc in child.childNodes:
                        if gc.nodeName == 'PostalAddress':
                            for ggc in gc.childNodes:
                                if (ggc.nodeName == 'PoliticalSubUnit_State'):
                                    self.state = self.__getState(ggc)
        def __getState(self, node):
            attr = node.getAttribute("cdr:ref")
            debugLog("stateAttr: %s" % attr)
            if attr:
                id = cdr.exNormalize(attr)
                intId = id[1]
                if not states.has_key(intId):
                    cursor.execute("""\
                        SELECT value
                          FROM query_term
                         WHERE path = '/PoliticalSubUnit' +
                                      '/PoliticalSubUnitFullName'
                           AND doc_id = ?""", intId)
                    rows = cursor.fetchall()
                    debugLog("rows: %s" % rows)
                    states[intId] = (rows and rows[0][0] or None)
                return states[intId]
    class Person:
        def __init__(self, id, title):
            self.id           = id
            self.title        = title
            self.name         = self.__getName(title)
            self.roles        = {}
            self.affiliations = {}
            cursor.execute("SELECT xml FROM document WHERE id = ?", id)
            rows = cursor.fetchall()
            if rows:
                dom = xml.dom.minidom.parseString(rows[0][0].encode('utf-8'))
                for node in dom.documentElement.childNodes:
                    if node.nodeName == 'PersonLocations':
                        for child in node.childNodes:
                            if child.nodeName == 'OtherPracticeLocation':
                                self.__getLocationInfo(child)
            #debugLog("person %d: %s" % (id, self.name))
            #for role in self.roles:
            #    debugLog("role: %s" % role)
            #for affil in self.affiliations:
            #    debugLog("affiliation: %s" % affil)
        def __getLocationInfo(self, node):
            for child in node.childNodes:
                if child.nodeName == 'ComplexAffiliation':
                    for gc in child.childNodes:
                        if gc.nodeName == 'Organization':
                            self.__addOrganization(gc)
                        elif gc.nodeName == 'RoleAtAffiliatedOrganization':
                            role = cdr.getTextContent(gc)
                            self.roles[role] = 1
                #elif child.nodeName == 'PersonRole':
                #    self.roles[cdr.getTextContent(child)] = 1
        def __addOrganization(self, node):
            id = node.getAttribute('cdr:ref')
            if id:
                id = cdr.exNormalize(id)
                intId = id[1]
                if orgShortNames.has_key(intId):
                    self.affiliations[orgShortNames[intId]] = 1
                else:
                    cursor.execute("""\
                        SELECT value
                          FROM query_term
                         WHERE path = '/Organization' +
                                      '/OrganizationNameInformation' +
                                      '/ShortName/Name'
                           AND doc_id = ?""", intId)
                    rows = cursor.fetchall()
                    if rows and rows[0][0]:
                        shortName = rows[0][0]
                        orgShortNames[intId] = shortName
                        self.affiliations[shortName] = 1
        def __getName(self, title):
            semicolon = title.find(';')
            if semicolon != -1:
                return title[:semicolon].strip()
            else:
                return title.strip()
cursor.execute("""\
 SELECT DISTINCT q.doc_id
            FROM query_term q
            JOIN document d
              ON d.id = q.doc_id
           WHERE q.path = '/Organization/OrganizationType'
             AND q.value IN ('NCI-funded community clinical oncology program',
                             'NCI-funded minority community clinical ' +
                             'oncology program')
             AND d.active_status = 'A'""")
rows = cursor.fetchall()
for row in rows:
    org = Organization(row[0])
    if not orgs.has_key(org.state):
        orgs[org.state] = []
    orgs[org.state].append(org)

#----------------------------------------------------------------------
# Generate the report.
#----------------------------------------------------------------------
html = u"""\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>NCI Funded CCOP/MBCCOP Organization Report</title>
  <style type='text/css'>
   body { font-family: Arial }
   h1   { font-size: 14pt; font-weight: bold }
   h2   { font-size: 12pt; font-weight: bold }
  </style>
 </head>
 <body>
  <center>
   <hr>
   <h1>NCI Funded CCOP/MBCCOP Organization Report</h1>
   <br><br>
  </center>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>State</th>
    <th>CCOP Name</th>
    <th>Person/Role</th>
    <th>Complex Affiliation</th>
   </tr>
"""

keys = orgs.keys()
keys.sort()
for state in keys:
    orgsInState = orgs[state]
    orgsInState.sort(lambda a,b: cmp(a.name, b.name))
    col1 = u"<b>%s</b>" % (state and cgi.escape(state).upper() or u"[NONE]")
    for org in orgsInState:
        col2 = u"%s (%d)" % (cgi.escape(org.name), org.id)
        if not org.persons:
            html += u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
   </tr>
""" % (col1, col2)
            col1 = u"&nbsp;"
        else:
            org.persons.sort(lambda a,b: cmp(a.name, b.name))
            for person in org.persons:
                col3 = u"%s (%d)" % (cgi.escape(person.name), person.id)
                for role in person.roles:
                    col3 += ", %s" % cgi.escape(role)
                if not person.affiliations:
                    col4 = u"&nbsp;"
                else:
                    affiliations = person.affiliations.keys()
                    affiliations.sort()
                    br = u""
                    col4 = u""
                    for affiliation in affiliations:
                        col4 += u"%s%s" % (br, cgi.escape(affiliation))
                        br = u"<br>"
                html += """\
   <tr>
    <td align='center'>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (col1, col2, col3, col4)
                col1 = col2 = u"&nbsp;"
                
cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>""")
