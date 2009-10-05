#----------------------------------------------------------------------
#
# $Id: Request2862.py,v 1.3 2007-10-31 17:43:09 bkline Exp $
#
# "We need a report that will display Liaison Office trials and the Lead
# organization contact information for the Liaison office to use."
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------

import cdrdb, cdrdocobject, sys, cdr, xml.dom.minidom, ExcelWriter, time

if sys.platform == "win32":
    import os, msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

debugging = False

# Magic CDR IDs and other values from requirement specs.
EORTC    = 'CDR0000029246'
FNCLCC   = 'CDR0000030236'
PUPS     = '(360795, 479054)'
BRUSSELS = 'NCI Liaison Office-Brussels'
TITLE    =  'NCI Liaison Office Trial Contacts for Abstract Review'

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("CREATE TABLE #brussels (id INTEGER)")
conn.commit()
cursor.execute("CREATE TABLE #pups (id INTEGER)")
conn.commit()
cursor.execute("CREATE TABLE #active (id INTEGER)")
conn.commit()
if debugging:
    sys.stderr.write("tables created\n")
cursor.execute("""\
    INSERT INTO #brussels
    SELECT DISTINCT doc_id
      FROM query_term_pub
     WHERE path = '/InScopeProtocol/ProtocolSources/ProtocolSource/SourceName'
       AND value = ?""", BRUSSELS, timeout = 300)
conn.commit()
if debugging:
    sys.stderr.write("#brussels populated\n")
cursor.execute("""\
    INSERT INTO #pups
    SELECT DISTINCT p.doc_id
      FROM query_term_pub p
      JOIN query_term_pub r
        ON p.doc_id = r.doc_id
       AND LEFT(p.node_loc, 12) = LEFT(r.node_loc, 12)
     WHERE p.path = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                  + '/LeadOrgPersonnel/Person/@cdr:ref'
       AND r.path = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                  + '/LeadOrgPersonnel/PersonRole'
       AND r.value = 'Update person'
       AND p.doc_id IN %s""" % PUPS, timeout = 300)
conn.commit()
if debugging:
    sys.stderr.write("#pups populated\n")
cursor.execute("""\
    INSERT INTO #active
    SELECT DISTINCT doc_id
      FROM query_term_pub
     WHERE path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
       AND value IN ('Active',
                     'Approved-not yet active',
                     'Temporarily closed')""", timeout = 300)
conn.commit()
if debugging:
    sys.stderr.write("#active populated\n")
cursor.execute("""\
    SELECT DISTINCT d.id, v.doc_version, d.first_pub
      FROM document d
      JOIN pub_proc_cg c
        ON d.id = c.id
      JOIN #active a
        ON a.id = d.id
      JOIN pub_proc_doc v
        ON v.pub_proc = c.pub_proc
       AND v.doc_id = d.id
     WHERE (d.id IN (SELECT id from #brussels)
        OR d.id IN (SELECT id from #pups))
       AND d.active_status = 'A'""", timeout = 300)
rows = cursor.fetchall()
if debugging:
    sys.stderr.write("%d rows selected\n" % len(rows))

def getElementText(parent, name):
    nodes = parent.getElementsByTagName(name)
    return nodes and cdr.getTextContent(nodes[0]) or None

def addSheet(wb, styles, protocols, title):
    ws = wb.addWorksheet(title)
    col = 1
    for width in (40, 200, 70, 70, 200, 100, 100):
        ws.addCol(col, width)
        col += 1
    row = ws.addRow(1, styles.title, 20)
    row.addCell(1, TITLE, style = styles.title, mergeAcross = 7)
    countRow = ws.addRow(2, styles.header)
    row = ws.addRow(4, styles.header)
    col = 1
    for name in ('DocID', 'Primary Protocol ID', 'Date First\nPublished',
                 'Date Last\nModified', 'LO Personnel', 'Phone', 'Email'):
        row.addCell(col, name, style = styles.header)
        col += 1
    n = 0
    rowNum = 5
    for protocol in protocols:
        if title in protocol.sheets:
            n += 1
            url = ("http://www.cancer.gov/clinicaltrials/"
                   "view_clinicaltrials.aspx?version=healthprofessional&"
                   "cdrid=%d" % protocol.docId)
            person = protocol.persons and protocol.persons[0] or ProtPerson()
            row = ws.addRow(rowNum)
            row.addCell(1, protocol.docId, style = styles.right)
            row.addCell(2, protocol.protId, style = styles.url, href = url)
            row.addCell(3, protocol.firstPub, style = styles.center)
            row.addCell(4, protocol.lastMod, style = styles.center)
            row.addCell(5, person.makeCellString(), style = styles.left)
            row.addCell(6, person.phone, style = styles.left)
            row.addCell(7, person.email, style = styles.left)
            rowNum += 1
            for person in protocol.persons[1:]:
                row = ws.addRow(rowNum)
                row.addCell(5, person.makeCellString(), style = styles.left)
                row.addCell(6, person.phone, style = styles.left)
                row.addCell(7, person.email, style = styles.left)
                rowNum += 1
    countRow.addCell(1, "Total Number of Trials: %d" % n,
                     style = styles.header, mergeAcross = 7)

class Styles:
    def __init__(self, wb):

        # Create the style for the title of a sheet.
        font        = ExcelWriter.Font(name = 'Arial', size = 16, bold = True)
        align       = ExcelWriter.Alignment('Center', 'Center')
        self.title  = wb.addStyle(alignment = align, font = font)

        # Create the style for the column headers.
        font        = ExcelWriter.Font(name = 'Arial', size = 10, bold = True)
        align       = ExcelWriter.Alignment('Left', 'Center', True)
        self.header = wb.addStyle(alignment = align, font = font)

        # Create the style for the linking cells.
        font        = ExcelWriter.Font('blue', None, 'Arial', size = 10)
        align       = ExcelWriter.Alignment('Left', 'Top', True)
        self.url    = wb.addStyle(alignment = align, font = font)

        # Create the style for the left-aligned cells.
        font        = ExcelWriter.Font(name = 'Arial', size = 10)
        self.left   = wb.addStyle(alignment = align, font = font)
        
        # Create the style for the centered cells.
        align       = ExcelWriter.Alignment('Center', 'Top', True)
        self.center = wb.addStyle(alignment = align, font = font)
        
        # Create the style for the right-aligned cells.
        align       = ExcelWriter.Alignment('Right', 'Top', True)
        self.right  = wb.addStyle(alignment = align, font = font)

class Person:
    __persons = {}
    def __init__(self, node):
        self.name = None
        self.phone = ""
        self.email = ""
        for child in node.childNodes:
            if child.nodeName == 'PersonNameInformation':
                self.name = cdrdocobject.PersonalName(child)
            elif child.nodeName == 'PersonLocations':
                cipsContact = getElementText(child, 'CIPSContact')
                for loc in child.childNodes:
                    if loc.nodeName in ('OtherPracticeLocation',
                                        'PrivatePractice'):
                        if loc.getAttribute('cdr:id') == cipsContact:
                            self.phone = getElementText(loc, 'Phone') or ""
                            self.email = getElementText(loc, 'Email') or ""
                            if not self.phone:
                                self.phone = getElementText(child,
                                                     'SpecificPhone') or ""
                            if not self.email:
                                self.email = getElementText(child,
                                                     'SpecificEmail') or ""
    @classmethod
    def getPerson(cls, docId, cursor):
        if docId not in cls.__persons:
            cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
            rows = cursor.fetchall()
            if not rows:
                cls.__persons[docId] = None
            else:
                dom = xml.dom.minidom.parseString(rows[0][0].encode('utf-8'))
                cls.__persons[docId] = Person(dom.documentElement)
        return cls.__persons.get(docId)

class ProtPerson:
    __roles = { "PRINCIPAL INVESTIGATOR": "PI",
                "PROTOCOL CHAIR": "PC",
                "PROTOCOL CO-CHAIR": "co-chair",
                "UPDATE PERSON": "PUP",
                "RESEARCH COORDINATOR": "RC",
                "STUDY COORDINATOR": "SC"
    }
    def __init__(self, node = None, mailAbstractTo = None, cursor = None):
        self.name = ""
        self.role = ""
        self.phone = ""
        self.email = ""
        self.mailTo = False
        if not node:
            return
        if node.getAttribute('cdr:id') == mailAbstractTo:
            self.mailTo = True
        person = None
        for child in node.childNodes:
            if child.nodeName == 'Person':
                idAttr = child.getAttribute('cdr:ref')
                try:
                    docId = cdr.exNormalize(idAttr)[1]
                    person = Person.getPerson(docId, cursor)
                except:
                    pass
            elif child.nodeName == 'PersonRole':
                self.role = cdr.getTextContent(child)
            elif child.nodeName == 'ProtocolSpecificContact':
                self.phone = getElementText(child, 'Phone') or ""
                self.email = getElementText(child, 'Email') or ""
        if person:
            self.name = "%s, %s" % (person.name.getSurname(),
                                    person.name.getGivenName())
            self.phone = self.phone or person.phone
            self.email = self.email or person.email
    def makeCellString(self):
        if not self.name and not self.role:
            return u""
        return u"%s%s (%s)" % (self.mailTo and "Mail to: " or "",
                               self.name,
                               ProtPerson.__roles.get(self.role.upper(),
                                                      self.role))

class LeadOrg:
    def __init__(self, node, mailAbstractTo, cursor):
        self.docId = None
        self.primary = getElementText(node, 'LeadOrgRole') == 'Primary'
        self.persons = []
        for child in node.childNodes:
            if child.nodeName == 'LeadOrganizationID':
                self.docId = child.getAttribute('cdr:ref')
            elif child.nodeName == 'LeadOrgPersonnel':
                self.persons.append(ProtPerson(child, mailAbstractTo, cursor))
            
class Protocol:
    def __init__(self, docId, docVer, firstPub, cursor):
        self.docId = docId
        self.docVer = docVer
        self.protId = None
        self.firstPub = str(firstPub)[:10]
        self.lastMod = None
        self.persons = []
        self.sheets = ["All Trials"]
        cursor.execute("""\
            SELECT xml
              FROM doc_version
             WHERE id = ?
               AND num = ?""", (docId, docVer))
        docXml = cursor.fetchall()[0][0]
        dom = xml.dom.minidom.parseString(docXml.encode('utf-8'))
        for node in dom.documentElement.childNodes:
            if node.nodeName == 'DateLastModified':
                self.lastMod = cdr.getTextContent(node)
            elif node.nodeName == 'ProtocolIDs':
                for child in node.childNodes:
                    if child.nodeName == 'PrimaryID':
                        self.protId = getElementText(child, 'IDString')
            elif node.nodeName == 'ProtocolAdminInfo':
                mailAbstractTo = getElementText(node, 'MailAbstractTo')
                for child in node.childNodes:
                    if child.nodeName == 'ProtocolLeadOrg':
                        org = LeadOrg(child, mailAbstractTo, cursor)
                        if org.primary:
                            if org.docId == EORTC:
                                self.sheets.append("EORTC")
                            elif org.docId == FNCLCC:
                                self.sheets.append("FNCLCC")
                        self.persons += org.persons
    def __cmp__(self, other):
        return cmp(self.protId, other.protId)

protocols = []
for docId, docVer, firstPub in rows:
    protocol = Protocol(docId, docVer, firstPub, cursor)
    protocols.append(protocol)
    if debugging:
        sys.stderr.write("\rparsed %d of %d protocols" % (len(protocols),
                                                          len(rows)))
protocols.sort()

wb      = ExcelWriter.Workbook()
styles  = Styles(wb)
addSheet(wb, styles, protocols, "All Trials")
addSheet(wb, styles, protocols, "EORTC")
addSheet(wb, styles, protocols, "FNCLCC")
now = time.strftime("%Y%m%d%H%M%S")
filename = "Brussels-%s.xls" % now
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=%s" % filename
print
wb.write(sys.stdout, True)
