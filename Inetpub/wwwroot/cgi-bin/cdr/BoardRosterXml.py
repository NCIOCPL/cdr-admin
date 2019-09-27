#----------------------------------------------------------------------
# Service to fetch board member information.
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, time, lxml.etree as etree
from cdrapi import db

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
boardId    = fields.getvalue("board")
memberId   = fields.getvalue("member")

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = db.connect(user="CdrGuest")
    cursor = conn.cursor()
except Exception as e:
    cdrcgi.sendPage('<Failure>%s</Failure>' % e, 'xml')

#----------------------------------------------------------------------
# Look up title of a board, given its ID.
#----------------------------------------------------------------------
def getBoardName(id):
    try:
        cursor.execute("SELECT title FROM document WHERE id = ?", id)
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail('Failure looking up title for CDR%s' % id)
        return cleanTitle(rows[0][0])
    except Exception as e:
        cdrcgi.sendPage('<Failure>%s</Failure' % e, 'xml')

#----------------------------------------------------------------------
# Remove cruft from a document title.
#----------------------------------------------------------------------
def cleanTitle(title):
    semicolon = title.find(';')
    if semicolon != -1:
        title = title[:semicolon]
    return title.strip()

#----------------------------------------------------------------------
# Get the information for the Board Manager
#----------------------------------------------------------------------
def getBoardManagerInfo(orgId):
    try:
        cursor.execute("""\
SELECT path, value
 FROM query_term
 WHERE path like '/Organization/PDQBoardInformation/BoardManager%%'
 AND   doc_id = ?
 ORDER BY path""", orgId)

    except Exception as e:
        cdrcgi.bail('Database query failure for BoardManager: %s' % e)
    return cursor.fetchall()

#----------------------------------------------------------------------
# Add the specific information to the boardInfo records
#----------------------------------------------------------------------
def addSpecificContactInfo(boardIds, boardInfo):
    newBoardInfo = []
    try:
        cursor.execute("""\
    SELECT g.doc_id, g.value AS GE, h.value, q.value as SpPhone,
           f.value as SpFax, e.value as SpEmail
      FROM query_term g
LEFT OUTER JOIN query_term h
        ON g.doc_id = h.doc_id
       AND h.path = '/PDQBoardMemberInfo/GovernmentEmployee/@HonorariaDeclined'
LEFT OUTER JOIN query_term f
        ON g.doc_id = f.doc_id
       AND f.path = '/PDQBoardMemberInfo/BoardMemberContact' +
                    '/SpecificBoardMemberContact/BoardContactFax'
LEFT OUTER JOIN query_term e
        ON g.doc_id = e.doc_id
       AND e.path = '/PDQBoardMemberInfo/BoardMemberContact/' +
                    'SpecificBoardMemberContact/BoardContactEmail'
LEFT OUTER JOIN query_term q
        ON g.doc_id = q.doc_id
       AND q.path = '/PDQBoardMemberInfo/BoardMemberContact' +
                    '/SpecificBoardMemberContact/BoardContactPhone'
     WHERE g.doc_id IN (%s)
       AND g.path = '/PDQBoardMemberInfo/GovernmentEmployee'
  ORDER BY q.path""" % ','.join(["'%d'" % id for id in boardIds]))
    except Exception as e:
        cdrcgi.bail('Database query failure for SpecificInfo: %s' % e +
                    '<br>Board has No Board Members')

    rows = cursor.fetchall()

    # Add the specific info to the boardInfo records
    # ----------------------------------------------
    for member in boardInfo:
        memCount = len(member)
        for cdrId, ge, honor, phone, fax, email in rows:
            if member[4] == cdrId:
                member = member + [ge, honor or None, phone or None,
                                   fax or None, email or None]
        if memCount == len(member):
            member = member + [None, None, None, None, None]
        newBoardInfo.append(member)
    return newBoardInfo


# ---------------------------------------------------------------------
# A non-government employee may decline to receive a honorarium.
# Returning the appropriate value for the person.
# ---------------------------------------------------------------------
def checkHonoraria(govEmployee, declined = ''):
    if govEmployee == 'Yes':
        return ''
    elif govEmployee == 'Unknown':
        return ''
    elif govEmployee == 'No':
        if declined == 'Yes':
            return '*'
        else:
            return ''

#----------------------------------------------------------------------
# Object for one PDQ board member.
#----------------------------------------------------------------------
class BoardMember:
    now = time.strftime("%Y-%m-%d")
    boards = {}
    def __init__(self, docId, eicStart, eicFinish, termStart, name, boardId):
        self.id        = docId
        self.name      = cleanTitle(name)
        self.isEic     = (eicStart and eicStart <= BoardMember.now and
                          (not eicFinish or eicFinish > BoardMember.now))
        self.eicStart  = eicStart
        self.eicFinish = eicFinish
        self.termStart = termStart
        self.boardId   = boardId
        self.boardName = BoardMember.boards.get(boardId)
        if not self.boardName:
            self.boardName = BoardMember.boards[boardId] = getBoardName(boardId)
    def __cmp__(self, other):
        if self.isEic == other.isEic:
            return cmp(self.name.upper(), other.name.upper())
        elif self.isEic:
            return -1
        return 1
    def toNode(self):
        node = etree.Element('BoardMember')
        etree.SubElement(node, 'DocId').text = str(self.id)
        etree.SubElement(node, 'Name').text = self.name
        etree.SubElement(node, 'IsEic').text = self.isEic and 'Yes' or 'No'
        etree.SubElement(node, 'TermStart').text = str(self.termStart)
        etree.SubElement(node, 'BoardName').text = self.boardName
        etree.SubElement(node, 'BoardId').text = str(self.boardId)
        return node

def getDocTree(cdrId):
    cursor.execute("SELECT xml FROM document WHERE id = ?", cdrId)
    return etree.fromstring(cursor.fetchall()[0][0])

def addChild(node, name, value):
    if value:
        etree.SubElement(node, name).text = value

class MemberDetails:
    #boards = {}
    def __init__(self, docId):
        self.docId = docId
        self.person = self.contact = self.contactMode = self.govt = None
        self.honorariaDeclined = contactId = personId = self.personId = None
        tree = getDocTree(docId)
        for node in tree.findall('BoardMemberName'):
            personId = cdr.exNormalize(node.get("{cips.nci.nih.gov/cdr}ref"))
            self.personId = personId[1]
            personTree = getDocTree(self.personId)
            for node in tree.findall('BoardMemberContact'):
                self.contact = self.Contact(personTree, node)
        for node in tree.findall('BoardMemberContactMode'):
            self.contactMode = node.text
        for node in tree.findall('GovernmentEmployee'):
            self.govt = node.text == 'Yes'
            if node.get('HonorariaDeclined') == 'Yes':
                self.honorariaDeclined = True
        self.person = self.Person(personTree)
    def toNode(self):
        node = etree.Element('BoardMember')
        etree.SubElement(node, 'DocId').text = str(self.docId)
        etree.SubElement(node, 'PersonId').text = str(self.personId)
        if self.person and self.person.name:
            node.append(self.person.name.toNode())
        if self.contact:
            node.append(self.contact.toNode())
        if self.govt is not None:
            value = self.govt and 'Yes' or 'No'
            etree.SubElement(node, 'GovernmentEmployee').text = value
        if self.honorariaDeclined:
            etree.SubElement(node, 'HonorariaDeclined').text = 'Yes'
        return node
    class Person:
        class Name:
            def __init__(self, node):
                self.first = self.mid = self.last = self.gen = self.fmt = None
                self.suffixes = []
                for child in node:
                    if child.tag == 'GivenName':
                        self.first = child.text
                    elif child.tag == 'MiddleInitial':
                        self.mid = child.text
                    elif child.tag == 'SurName':
                        self.last = child.text
                    elif child.tag == 'GenerationSuffix':
                        self.gen = child.text
                    elif child.tag == 'NameFormat':
                        self.fmt = child.text
                    elif child.tag == 'ProfessionalSuffix':
                        for grandchild in child:
                            if grandchild.tag in ('StandardProfessionalSuffix',
                                                  'CustomProfessionalSuffix'):
                                self.suffixes.append(grandchild.text)
            def toNode(self):
                node = etree.Element('Name')
                addChild(node, 'First', self.first)
                addChild(node, 'Middle', self.mid)
                addChild(node, 'Last', self.last)
                addChild(node, 'Gen', self.gen)
                addChild(node, 'Format', self.fmt)
                for suffix in self.suffixes:
                    addChild(node, 'Suffix', suffix)
                return node
        def __init__(self, tree):
            self.name = None
            for node in tree.findall('PersonNameInformation'):
                self.name = MemberDetails.Person.Name(node)
    class Contact:
        def __init__(self, tree, contact):
            self.phone = self.fax = self.email = location = contactId = None
            for child in contact.findall('SpecificBoardMemberContact'):
                for grandchild in child:
                    if grandchild.tag == 'BoardContactPhone':
                        self.phone = MemberDetails.Contact.Phone(grandchild)
                    elif grandchild.tag == 'BoardContactEmail':
                        self.email = MemberDetails.Contact.Email(grandchild)
                    elif grandchild.tag == 'BoardContactFax':
                        self.fax = grandchild.text
            if self.phone and self.fax and self.email:
                return
            for child in contact.findall('PersonContactID'):
                contactId = child.text
            #print "contactId = %s" % contactId
            if not contactId:
                return
            for child in tree.findall('PersonLocations/OtherPracticeLocation'):
                locId = child.get("{cips.nci.nih.gov/cdr}id")
                #print "location ID: %s" % locId
                if locId == contactId:
                    location = MemberDetails.Contact.Other(child)
                    break
            if not location:
                path = 'PersonLocations/PrivatePractice/PrivatePracticeLocation'
                for child in tree.findall(path):
                    if child.get("{cips.nci.nih.gov/cdr}id") == contactId:
                        location = MemberDetails.Contact.Detail(child)
                        break
            if not location:
                for child in tree.findall('PersonLocations/Home'):
                    if child.get("{cips.nci.nih.gov/cdr}id") == contactId:
                        location = MemberDetails.Contact.Detail(child)
                        break
            if location:
                self.phone = self.phone or location.phone
                self.fax = self.fax or location.fax
                self.email = self.email or location.email
        def toNode(self):
            node = etree.Element('Contact')
            if self.phone:
                node.append(self.phone.toNode())
            addChild(node, 'Fax', self.fax)
            if self.email:
                node.append(self.email.toNode())
            return node
        class Phone:
            def __init__(self, node):
                self.number = node.text
                self.public = node.get('Public') != 'No'
            def toNode(self):
                node = etree.Element('Phone')
                addChild(node, 'Number', self.number)
                addChild(node, 'Public', self.public and 'Yes' or 'No')
                return node
        class Email:
            def __init__(self, node):
                self.address = node.text
                self.public = node.get('Public') != 'No'
            def toNode(self):
                node = etree.Element('Email')
                addChild(node, 'Address', self.address)
                addChild(node, 'Public', self.public and 'Yes' or 'No')
                return node
        class Detail:
            def __init__(self, node):
                phone = tollFree = self.phone = self.fax = self.email = None
                for child in node:
                    if child.tag == 'Phone':
                        phone = MemberDetails.Contact.Phone(child)
                    elif child.tag == 'TollFreePhone':
                        tollFree = MemberDetails.Contact.Phone(child)
                    elif child.tag == 'Fax':
                        self.fax = child.text
                    elif child.tag == 'Email':
                        self.email = MemberDetails.Contact.Email(child)
                self.phone = tollFree or phone
        class Other:
            def __init__(self, node):
                phone = tollFree = self.phone = self.fax = self.email = None
                for child in node:
                    if child.tag == 'SpecificPhone':
                        phone = MemberDetails.Contact.Phone(child)
                    elif child.tag == 'SpecificTollFreePhone':
                        tollFree = MemberDetails.Contact.Phone(child)
                    elif child.tag == 'SpecificFax':
                        self.fax = child.text
                    elif child.tag == 'SpecificEmail':
                        self.email = MemberDetails.Contact.Email(child)
                self.phone = tollFree or phone
                if not (self.phone and self.fax and self.email):
                    for child in node.findall('OrganizationLocation'):
                        orgId = child.get("{cips.nci.nih.gov/cdr}ref")
                        strId, intId, fragId = cdr.exNormalize(orgId)
                        if fragId:
                            orgTree = getDocTree(intId)
                            path = 'OrganizationLocations/OrganizationLocation'
                            for loc in orgTree.findall(path):
                                locId = loc.get("{cips.nci.nih.gov/cdr}id")
                                if locId == fragId:
                                    for det in loc.findall('Location'):
                                        cls = MemberDetails.Contact.Detail
                                        detail = cls(det)
                                        self.phone = self.phone or detail.phone
                                        self.fax = self.fax or detail.fax
                                        self.email = self.email or detail.email
                                    break

#----------------------------------------------------------------------
# Select the list of board members associated to a board (passed in
# by the selection of the user) along with start/end dates.
#----------------------------------------------------------------------
def allBoardMembers():
    try:
        cursor.execute("""\
 SELECT DISTINCT member.doc_id, eic_start.value, eic_finish.value,
                 term_start.value, person_doc.title, member.int_val
            FROM query_term member
            JOIN query_term curmemb
              ON curmemb.doc_id = member.doc_id
             AND LEFT(curmemb.node_loc, 4) = LEFT(member.node_loc, 4)
            JOIN query_term person
              ON person.doc_id = member.doc_id
            JOIN document person_doc
              ON person_doc.id = person.doc_id
 LEFT OUTER JOIN query_term eic_start
              ON eic_start.doc_id = member.doc_id
             AND LEFT(eic_start.node_loc, 4) = LEFT(member.node_loc, 4)
             AND eic_start.path   = '/PDQBoardMemberInfo/BoardMembershipDetails'
                              + '/EditorInChief/TermStartDate'
 LEFT OUTER JOIN query_term eic_finish
              ON eic_finish.doc_id = member.doc_id
             AND LEFT(eic_finish.node_loc, 4) = LEFT(member.node_loc, 4)
             AND eic_finish.path  = '/PDQBoardMemberInfo/BoardMembershipDetails'
                              + '/EditorInChief/TermEndDate'
 LEFT OUTER JOIN query_term term_start
              ON term_start.doc_id = member.doc_id
             AND LEFT(term_start.node_loc, 4) = LEFT(member.node_loc, 4)
             AND term_start.path = '/PDQBoardMemberInfo/BoardMembershipDetails'
                              + '/TermStartDate'
           WHERE member.path  = '/PDQBoardMemberInfo/BoardMembershipDetails'
                              + '/BoardName/@cdr:ref'
             AND curmemb.path = '/PDQBoardMemberInfo/BoardMembershipDetails'
                              + '/CurrentMember'
             AND person.path  = '/PDQBoardMemberInfo/BoardMemberName/@cdr:ref'
             AND curmemb.value = 'Yes'
             AND person_doc.active_status = 'A'""")
        rows = cursor.fetchall()
        root = etree.Element('BoardMembers')
        for docId, eic_start, eic_finish, term_start, name, boardId in rows:
            boardMember = BoardMember(docId, eic_start, eic_finish,
                                      term_start, name, boardId)
            root.append(boardMember.toNode())
        return etree.tostring(root, pretty_print=True, encoding="unicode")
    except Exception as e:
        raise
        cdrcgi.sendPage('<Failure>%s</Failure>' % e, 'xml')

def getBoardMember(cdrId):
    filters = ['set:Denormalization PDQBoardMemberInfo Set']
    # filters.append('name:Copy XML for Person 2')
    response = cdr.filterDoc('guest', filters, cdrId)
    if isinstance(response, (str, bytes)):
        cdrcgi.sendPage("<Failure>%s</Failure>" % response, 'xml')
    return response[0]

def collectMembersForBoard(boardId):
    try:
        cursor.execute("""\
 SELECT DISTINCT b.doc_id
            FROM query_term b
            JOIN query_term c
              ON c.doc_id = b.doc_id
             AND LEFT(c.node_loc, 4) = LEFT(b.node_loc, 4)
            JOIN active_doc a
              ON a.id = c.doc_id
           WHERE b.path = '/PDQBoardMemberInfo/BoardMembershipDetails'
                        + '/BoardName/@cdr:ref'
             AND c.path = '/PDQBoardMemberInfo/BoardMembershipDetails'
                        + '/CurrentMember'
             AND c.value = 'Yes'
             AND b.int_val = ?""", boardId)
        docIds = [row[0] for row in cursor.fetchall()]
        root = etree.Element('Board')
        etree.SubElement(root, 'BoardId').text = str(boardId)
        etree.SubElement(root, 'BoardName').text = getBoardName(boardId)
        for docId in docIds:
            root.append(MemberDetails(docId).toNode())
        return etree.tostring(root, pretty_print=True, encoding="unicode")
    except Exception as e:
        cdrcgi.sendPage("<Failure>%s</Failure>" % e, 'xml')

if memberId:
    details = MemberDetails(int(memberId))
    opts = dict(pretty_print=True, encoding="unicode")
    docXml = etree.tostring(details.toNode(), **opts)
    cdrcgi.sendPage(docXml, 'xml')
    #cdrcgi.sendPage(getBoardMember(int(memberId)), 'xml')
elif boardId:
    doc = collectMembersForBoard(boardId)
    cdrcgi.sendPage(doc, 'xml')
else:
    cdrcgi.sendPage(allBoardMembers(), 'xml')
