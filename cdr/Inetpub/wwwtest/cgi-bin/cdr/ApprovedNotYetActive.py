#----------------------------------------------------------------------
#
# $Id: ApprovedNotYetActive.py,v 1.2 2003-02-26 13:52:25 bkline Exp $
#
# Approved Not Yet Active Protocols Verification Report
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2003/01/22 23:28:30  bkline
# New report for issue #560.
#
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, time, xml.dom.minidom

#----------------------------------------------------------------------
# Protocol object.
#----------------------------------------------------------------------
class Protocol:
    def __init__(self, id, orgProtId):
        self.id        = id
        self.orgProtId = orgProtId

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
            orgName = ''
            orgProtId = ''
            pList = []
            for node in topNode.childNodes:
                if node.nodeName == "OrgName":
                    orgName = cdr.getTextContent(node)
                elif node.nodeName == "OrgProtId":
                    orgProtId = cdr.getTextContent(node)
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
            protocol = Protocol(row[0], orgProtId)
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
# Start the page.
#----------------------------------------------------------------------
today = time.strftime("%B %d, %Y")
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Approved Not Yet Active Protocols Verification Report - %s</title>
  <style type='text/css'>
   th,h1,h2 { font-family: Arial, sans-serif; font-size: 11pt;
              text-align: center; font-weight: bold; }
   td       { font-family: Arial, sans-serif; font-size: 10pt;
              text-align: left; }
  </style>
 </head>
 <body>
  <h1>Approved Not Yet Active Protocols Verification Report</h1>
  <h2>%s</h2>
  <br><br>
  <table border='1' cellspacing='0' cellpadding='1'>
   <tr>
    <th>UpdatePerson</th>
    <th>Email</th>
    <th>Phone</th>
    <th>LeadOrganization</th>
    <th nowrap='1'>Lead Org ProtocolID</th>
    <th nowrap='1'>CDR DocId</th>
    <th nowrap='1'>Status Change?</th>
   </tr>
""" % (today, today)

#----------------------------------------------------------------------
# Loop through the update persons, in surname order.
#----------------------------------------------------------------------
keys = pups.keys()
keys.sort()
for key in keys:
    pup = pups[key]
    if pup.email:
        pup.email = "<a href='mailto:%s'>%s</a>" % (pup.email, pup.email)
    pup.protocols.sort(lambda a,b: cmp(a.orgProtId, b.orgProtId))
    orgProtIds = ""
    docIds     = ""
    sep        = ""
    for prot in pup.protocols:
        orgProtIds += "%s%s" % (sep, prot.orgProtId)
        docIds     += "%sCDR%010d" % (sep, prot.id)
        sep = "<br>"
    html += """\
   <tr>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top' nowrap='1'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td>&nbsp;</td>
   </tr>
""" % (pup.name    or "&nbsp;",
       pup.email   or "&nbsp;",
       pup.phone   or "&nbsp;",
       pup.leadOrg or "&nbsp;",
       orgProtIds  or "&nbsp;",
       docIds      or "&nbsp;")

#----------------------------------------------------------------------
# Show the report.
#----------------------------------------------------------------------
cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>
""")
