#----------------------------------------------------------------------
#
# $Id: ApprovedNotYetActive.py,v 1.5 2009-05-19 19:34:22 venglisc Exp $
#
# Approved Not Yet Active Protocols Verification Report
#
# $Log: not supported by cvs2svn $
# Revision 1.4  2009/02/19 15:38:34  bkline
# Fixed typo in format string passed to time.strftime().
#
# Revision 1.3  2008/09/02 18:51:57  bkline
# Rewritten as an Excel report, with title column added (#4257).
#
# Revision 1.2  2003/02/26 13:52:25  bkline
# Issue 611: "Please modify this report to include an additional
# criteria -- Only include protocols that have a publishable version."
# Lakshmi, 2003-02-25.
#
# Revision 1.1  2003/01/22 23:28:30  bkline
# New report for issue #560.
#
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, time, xml.dom.minidom, ExcelWriter

#----------------------------------------------------------------------
# Get the protocol's original title.
#----------------------------------------------------------------------
protTitles = {}
def lookupOriginalTitle(cursor, docId):
    if docId not in protTitles:
        cursor.execute("""\
            SELECT pt.value
              FROM query_term pt
              JOIN query_term tt
                ON tt.doc_id = pt.doc_id
               AND LEFT(pt.node_loc, 4) = LEFT(tt.node_loc, 4)
             WHERE pt.path = '/InScopeProtocol/ProtocolTitle'
               AND tt.path = '/InScopeProtocol/ProtocolTitle/@Type'
               AND tt.value = 'Original'
               AND tt.doc_id = ?""", docId, timeout = 300)
        rows = cursor.fetchall()
        protTitles[docId] = rows and rows[0][0] or u""
    return protTitles[docId]

#----------------------------------------------------------------------
# Protocol object.
#----------------------------------------------------------------------
class Protocol:
    def __init__(self, id, orgProtId, updMode):
        self.id        = id
        self.orgProtId = orgProtId
        self.updMode   = updMode or ''

#----------------------------------------------------------------------
# Protocol update person object.
#----------------------------------------------------------------------
class PUP:
    def __init__(self, name, email, phone, leadOrg):
        self.name      = name
        self.email     = email
        self.phone     = phone
        self.leadOrg   = leadOrg
        self.protocols = []
        
#----------------------------------------------------------------------
# Connect to the database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
    curs = conn.cursor()
except:
    cdrcgi.bail("Unable to connect to the CDR database")

#----------------------------------------------------------------------
# Find the protocols which belong in the report.
#----------------------------------------------------------------------
path = "/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg" \
       "/LeadOrgProtocolStatuses/CurrentOrgStatus/StatusName"
try:
    curs.execute("""\
        SELECT v.id, MAX(v.num)
          FROM doc_version v
          JOIN query_term q
            ON q.doc_id = v.id
          JOIN document d
            ON d.id = q.doc_id
         WHERE v.publishable = 'Y'
           AND d.active_status = 'A'
           AND path = '%s'
           AND value = 'Approved-not yet active'
      GROUP BY v.id""" % path)
    rows = curs.fetchall()
except:
    raise
    cdrcgi.bail("Database failure selecting protocol documents")

#----------------------------------------------------------------------
# Collect the information.
#----------------------------------------------------------------------
filter = ['name:Approved Not Yet Active Protocols Report Filter']
pups = {}
for row in rows:
    resp = cdr.filterDoc('guest', filter, row[0], docVer = row[1])
    if type(resp) in (type(''), type(u'')):
        cdrcgi.bail(resp)
    try:
        elem = xml.dom.minidom.parseString(resp[0]).documentElement
    except:
        cdrcgi.bail("Failure parsing filtered protocol "
                    "CDR%010d version %d" % (row[0], row[1]))

    for topNode in elem.childNodes:
        if topNode.nodeName == "LeadOrg":
            orgName   = ''
            orgProtId = ''
            updMode   = ''
            pList     = []
            for node in topNode.childNodes:
                if node.nodeName == "OrgName":
                    orgName = cdr.getTextContent(node)
                elif node.nodeName == "OrgProtId":
                    orgProtId = cdr.getTextContent(node)
                elif node.nodeName == "UpdateMode":
                    updMode = cdr.getTextContent(node)
                elif node.nodeName == "PUP":
                    givenName = ''
                    middleInitial = ''
                    surname = ''
                    phone = ''
                    email = ''
                    for child in node.childNodes:
                        if child.nodeName == "GivenName":
                            givenName = cdr.getTextContent(child)
                        elif child.nodeName == "MiddleInitial":
                            middleInitial = cdr.getTextContent(child)
                        elif child.nodeName == "Surname":
                            surname = cdr.getTextContent(child)
                        elif child.nodeName == "Phone":
                            phone = cdr.getTextContent(child)
                        elif child.nodeName == "Email":
                            email = cdr.getTextContent(child)
                    pList.append((givenName, middleInitial, surname, phone,
                                  email))
            protocol = Protocol(row[0], orgProtId, updMode)
            for p in pList:
                givenName, middleInitial, surname, phone, email = p
                name = (givenName + " " + middleInitial).strip()
                name += " " + surname
                name = name.strip()
                key = (surname, name, phone, email, orgName)
                if not pups.has_key(key):
                    pup = PUP(name, email, phone, orgName)
                    pups[key] = pup
                else:
                    pup = pups[key]
                pup.protocols.append(protocol)

#----------------------------------------------------------------------
# Start the report.
#----------------------------------------------------------------------
#today = time.strftime("%B %d, %Y")
today = time.strftime("%Y-%m-%d")
try:
    import msvcrt, os, sys
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
except:
    pass
book = ExcelWriter.Workbook()
sheet = book.addWorksheet("ANYA Protocols")
stamp = time.strftime("%Y%m%d%H%M%S")
font = ExcelWriter.Font(size = 12, bold = True)
align = ExcelWriter.Alignment('Center', 'Bottom', wrap = True)
style = book.addStyle(font = font, alignment = align)
row = sheet.addRow(1, style)
title = "Approved Not Yet Active Protocols Verification Report"
row.addCell(1, title, mergeAcross = 8)
row = sheet.addRow(2, style)
row.addCell(1, today, mergeAcross = 8)
sheet.addCol(1, 100)
sheet.addCol(2, 200)
sheet.addCol(3, 100)
sheet.addCol(4, 400)
sheet.addCol(5, 200)
sheet.addCol(6, 100)
sheet.addCol(7, 100)
sheet.addCol(8, 400)
sheet.addCol(9,  60)
row = sheet.addRow(4, style)
row.addCell(1, u"UpdatePerson")
row.addCell(2, u"Email")
row.addCell(3, u"Phone")
row.addCell(4, u"LeadOrganization")
row.addCell(5, u"Lead Org ProtocolID")
row.addCell(6, u"CDR DocId")
row.addCell(7, u"Status Change?")
row.addCell(8, u"Protocol Title")
row.addCell(9, u"Update Mode")
align = ExcelWriter.Alignment('Left', 'Top', wrap = True)
style = book.addStyle(alignment = align)

#----------------------------------------------------------------------
# Loop through the update persons, in surname order.
#----------------------------------------------------------------------
keys = pups.keys()
keys.sort()
rowNumber = 5
for key in keys:
    pup = pups[key]
    pup.protocols.sort(lambda a,b: cmp(a.orgProtId, b.orgProtId))
    mergeDown = 0
    if len(pup.protocols) > 1:
        mergeDown = len(pup.protocols) - 1
    row = sheet.addRow(rowNumber, style)
    row.addCell(1, pup.name or u"")
    if pup.email:
        row.addCell(2, pup.email, href = 'mailto:%s' % pup.email)
    row.addCell(3, pup.phone or u"")
    row.addCell(4, pup.leadOrg or u"")
    if pup.protocols:
        protTitle = lookupOriginalTitle(curs, pup.protocols[0].id)
        row.addCell(5, pup.protocols[0].orgProtId)
        row.addCell(6, u"CDR%010d" % pup.protocols[0].id)
        row.addCell(8, protTitle)
        row.addCell(9, pup.protocols[0].updMode)
    for p in pup.protocols[1:]:
        rowNumber += 1
        row = sheet.addRow(rowNumber, style)
        protTitle = lookupOriginalTitle(curs, p.id)
        row.addCell(5, p.orgProtId)
        row.addCell(6, u"CDR%010d" % p.id)
        row.addCell(8, protTitle)
        row.addCell(9, pup.protocols[0].updMode)
    rowNumber += 1

#----------------------------------------------------------------------
# Send the report.
#----------------------------------------------------------------------
print "Content-type: application/vnd.ms-excel"
print "Content-Disposition: attachment; filename=anya-%s.xls" % stamp
print
book.write(sys.stdout, True)
