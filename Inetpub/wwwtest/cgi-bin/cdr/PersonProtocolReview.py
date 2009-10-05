#----------------------------------------------------------------------
#
# $Id: PersonProtocolReview.py,v 1.9 2005-06-22 16:45:11 bkline Exp $
#
# Report to assist editors in checking links to a specified person from
# protocols.
#
# $Log: not supported by cvs2svn $
# Revision 1.8  2004/11/08 21:07:32  venglisc
# Fixed query to eliminate multiple occurrences of display.  The two temp
# tables were not joined properly.
# Also minor modifications to split long strings of path names. (Bug 1397)
#
# Revision 1.7  2004/10/07 15:50:20  venglisc
# Increased timeout time for subqueries.
#
# Revision 1.6  2004/09/24 15:48:25  venglisc
# Reformatting report to follow output layout of other QC reports. (Bug 1261)
#
# Revision 1.5  2003/08/25 20:24:43  bkline
# Juggled sort order of report results at users' requets.
#
# Revision 1.4  2003/06/13 20:30:21  bkline
# Added identification of previous locations.
#
# Revision 1.3  2002/06/26 20:26:19  bkline
# Changed query to match new Person DocTitle format rules.
#
# Revision 1.2  2002/05/23 15:01:22  bkline
# Changed the sort logic to match the latest criteria.
#
# Revision 1.1  2002/05/22 18:42:11  bkline
# Lists all the protocols which link to a specified Person document.
#
#----------------------------------------------------------------------

import cdr, cdrdb, cdrcgi, cgi, re, string, time, xml.dom.minidom

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
name     = fields and fields.getvalue('Name') or None
id       = fields and fields.getvalue('Id')   or None
SUBMENU  = "Report Menu"
buttons  = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script   = "PersonProtocolReview.py"
title    = "CDR Administration"
section  = "Person Protocol Review Report"
header   = cdrcgi.header(title, title, section, script, buttons)
now      = time.localtime(time.time())
ellipsis = "&nbsp;. . . . . .&nbsp;"

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# If we don't have a request, put up the request form.
#----------------------------------------------------------------------
if not name and not id:
    form = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <TABLE BORDER='0'>
    <TR>
     <TD ALIGN='right'><B>Document ID:&nbsp;</B></TD>
     <TD><INPUT NAME='Id'></TD>
    </TR>
    <TR>
     <TD ALIGN='right'><B>Person Name:&nbsp;</B></TD>
     <TD><INPUT NAME='Name'>
      &nbsp;(e.g., Doroshow, James)
     </TD>
    </TR>
   </TABLE>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Get the document ID.
#----------------------------------------------------------------------
if id:
    digits = re.sub('[^\d]', '', id)
    id     = string.atoi(digits)
else:
    try:
        namePattern = name + "%"
        cursor.execute("""\
                SELECT DISTINCT d.id
                           FROM document d
                           JOIN doc_type t
                             ON t.id = d.doc_type
                          WHERE t.name = 'Person'
                            AND d.title LIKE ?""", namePattern)
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure looking up person name '%s': %s" % (name,
                                                                 info[1][0]))
    if len(rows) > 1: cdrcgi.bail("Ambiguous person name '%s'" % name)
    if len(rows) < 1: cdrcgi.bail("Unknown person '%s'" % name)
    id = rows[0][0]

#----------------------------------------------------------------------
# One for each connection between a protocol and a location fragment link.
#----------------------------------------------------------------------
class ProtocolPersonLink:
    def __init__(self, fragLink, protocol):
        self.fragLink        = fragLink
        self.protocol        = protocol
        self.roles           = {}
    def __cmp__(self, other):
        result = cmp(self.protocol.status, other.protocol.status)
        if result:
            return result
        return cmp(self.protocol.protId, other.protocol.protId)

#----------------------------------------------------------------------
# One for each of the ProtocolPersonLink.roles.
#----------------------------------------------------------------------
class PersonRole:
    def __init__(self, name):
        self.name            = name
        self.leadOrgPerson   = False
        self.partSitePerson  = False
        self.leadOrgContact  = False
        self.partSiteContact = False

#----------------------------------------------------------------------
# Information we need about each individual protocol.
#----------------------------------------------------------------------
class Protocol:
    def __init__(self, docId, protId, status):
        self.docId  = docId
        self.protId = protId
        self.status = status
        if status == 'Approved-not yet active':
            status = 'Approved'
        elif status == 'Temporarily closed':
            status = 'Temp closed'

#----------------------------------------------------------------------
# Create temporary tables for the person-protocol appearances.
#----------------------------------------------------------------------
try:
    # Lead Org Persons
    cursor.execute("""\
        CREATE TABLE #lop
           (protocol INTEGER      NOT NULL,
           frag_link VARCHAR(512) NOT NULL,
                role VARCHAR(512)     NULL,
          contact_id VARCHAR(512)     NULL)""")
    conn.commit()

    # Protocol Site Persons
    cursor.execute("""\
        CREATE TABLE #sp
           (protocol INTEGER      NOT NULL,
           frag_link VARCHAR(512) NOT NULL,
                role VARCHAR(512)     NULL,
               phone VARCHAR(512)     NULL,
               email VARCHAR(512)     NULL)""")
    conn.commit()

    # External Site Persons
    cursor.execute("""\
        CREATE TABLE #ep
           (protocol INTEGER NOT NULL,
               phone VARCHAR(512))""")
    conn.commit()
except Exception, e:
    cdrcgi.bail("Failure creating working tables: %s" % str(e))

#----------------------------------------------------------------------
# Populate the tables.
#----------------------------------------------------------------------
try:
    cursor.execute("""\
        INSERT INTO #lop
             SELECT p.doc_id, p.value, r.value, c.value
               FROM query_term p
    LEFT OUTER JOIN query_term r
                 ON r.doc_id = p.doc_id
                AND LEFT(r.node_loc, 12) = LEFT(p.node_loc, 12)
                AND r.path = '/InScopeProtocol/ProtocolAdminInfo'
                           + '/ProtocolLeadOrg/LeadOrgPersonnel/PersonRole'
    LEFT OUTER JOIN query_term c
                 ON c.doc_id = p.doc_id
                AND LEFT(c.node_loc, 12) = LEFT(p.node_loc, 12)
                AND c.path = '/InScopeProtocol/ProtocolAdminInfo'
                           + '/ProtocolLeadOrg/LeadOrgPersonnel'
                           + '/ProtocolSpecificContact/@cdr:id'
              WHERE p.path = '/InScopeProtocol/ProtocolAdminInfo'
                           + '/ProtocolLeadOrg/LeadOrgPersonnel'
                           + '/Person/@cdr:ref'
                AND p.int_val = ?""", id, timeout = 300)
    conn.commit()
    cursor.execute("""\
        INSERT INTO #sp
             SELECT p.doc_id, p.value, r.value, ph.value, e.value
               FROM query_term p
    LEFT OUTER JOIN query_term r
                 ON r.doc_id = p.doc_id
                AND LEFT(r.node_loc, 24) = LEFT(p.node_loc, 24)
                AND r.path = '/InScopeProtocol/ProtocolAdminInfo'
                           + '/ProtocolLeadOrg/ProtocolSites/OrgSite'
                           + '/OrgSiteContact/SpecificPerson/Role'
    LEFT OUTER JOIN query_term ph
                 ON ph.doc_id = p.doc_id
                AND LEFT(ph.node_loc, 24) = LEFT(p.node_loc, 24)
                AND ph.path = '/InScopeProtocol/ProtocolAdminInfo'
                            + '/ProtocolLeadOrg/ProtocolSites/OrgSite'
                            + '/OrgSiteContact/SpecificPerson/SpecificPhone'
    LEFT OUTER JOIN query_term e
                 ON e.doc_id = p.doc_id
                AND LEFT(e.node_loc, 24) = LEFT(p.node_loc, 24)
                AND e.path = '/InScopeProtocol/ProtocolAdminInfo'
                           + '/ProtocolLeadOrg/ProtocolSites/OrgSite'
                           + '/OrgSiteContact/SpecificPerson/SpecificEmail'
              WHERE p.path = '/InScopeProtocol/ProtocolAdminInfo'
                           + '/ProtocolLeadOrg/ProtocolSites/OrgSite'
                           + '/OrgSiteContact/SpecificPerson/Person/@cdr:ref'
                AND p.int_val = ?""", id, timeout = 300)
    conn.commit()
    cursor.execute("""\
        INSERT INTO #ep
    SELECT DISTINCT p1.doc_id, p2.value
               FROM query_term p1
    LEFT OUTER JOIN query_term p2
                 ON p1.doc_id = p2.doc_id
                AND LEFT(p1.node_loc, 16) = LEFT(p2.node_loc, 16)
                AND p2.path = '/InScopeProtocol/ProtocolAdminInfo'
                            + '/ExternalSites/ExternalSite/ExternalSitePI'
                            + '/ExternalSitePIPhone'
              WHERE p1.path = '/InScopeProtocol/ProtocolAdminInfo'
                            + '/ExternalSites/ExternalSite/ExternalSitePI'
                            + '/ExternalSitePIID/@cdr:ref'
                AND p1.int_val = ?""", id, timeout = 300)
    conn.commit()
except Exception, e:
    cdrcgi.bail("Failure populating working tables: %s" % str(e))

#----------------------------------------------------------------------
# Gather common information needed for all referenced protocols.
#----------------------------------------------------------------------
protocols = {}
try:
    cursor.execute("""\
 SELECT DISTINCT i.doc_id, i.value, s.value
            FROM query_term i
             JOIN query_term s
               ON s.doc_id = i.doc_id
            WHERE i.path = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
              AND s.path = '/InScopeProtocol/ProtocolAdminInfo'
                         + '/CurrentProtocolStatus'
              AND i.doc_id IN (SELECT protocol FROM #lop
                               UNION
                               SELECT protocol FROM #sp
                               UNION
                               SELECT protocol FROM #ep)""", timeout = 300)
    for docId, protId, status in cursor.fetchall():
        protocols[docId] = Protocol(docId, protId, status)
except Exception, e:
    cdrcgi.bail("Failure retrieving protocol information: %s" % str(e))

#----------------------------------------------------------------------
# Create or find ProtocolPersonLink object.
#----------------------------------------------------------------------
def lookupProtocolPersonLink(fragLink, docId):
    location = locations[fragLink] = locations.get(fragLink, {})
    if docId not in location:
        location[docId] = ProtocolPersonLink(fragLink, protocols[docId])
    return location[docId]

#----------------------------------------------------------------------
# Find or create PersonRole object.
#----------------------------------------------------------------------
def lookupPersonRole(roles, roleName):
    if roleName not in roles:
        role = roles[roleName] = PersonRole(roleName)
    else:
        role = roles[roleName]
    return role

#----------------------------------------------------------------------
# Add a row to a report table.
#----------------------------------------------------------------------
def addRow(table, cssClass, protocol, role, leadOrgPerson, partSitePerson,
           leadOrgContact, partSiteContact):
    table.append(u"""\
      <tr%s>
       <td>%s</td>
       <td>%s</td>
       <td>%s</td>
       <td>%s</td>
       <td align='center'>%s</td>
       <td align='center'>%s</td>
       <td align='center'>%s</td>
       <td align='center'>%s</td>
      </tr>""" % (cssClass,
                  protocol.docId,
                  protocol.protId,
                  protocol.status or u"&nbsp;",
                  role,
                  leadOrgPerson   and u"X" or u"&nbsp;",
                  partSitePerson  and u"X" or u"&nbsp;",
                  leadOrgContact  and u"X" or u"&nbsp;",
                  partSiteContact and u"X" or u"&nbsp;"))

#----------------------------------------------------------------------
# Find the CSS class that goes with a particular protocol status.
#----------------------------------------------------------------------
def lookupCssClass(protocolStatus):
    if not protocolStatus:
        return u" class='status_err'"
    elif protocolStatus not in ('Active', 'Approved'):
        return u" class='status_closed'"
    else:
        return u""

#----------------------------------------------------------------------
# Populate a map for each of the person's locations.
#----------------------------------------------------------------------
locations = {}
try:
    cursor.execute("SELECT * FROM #lop")
    for docId, fragLink, roleName, contactInfo in cursor.fetchall():
        protocolPersonLink = lookupProtocolPersonLink(fragLink, docId)
        roleName = roleName or "None"
        role = lookupPersonRole(protocolPersonLink.roles, roleName)
        role.leadOrgPerson = True
        if contactInfo:
            role.leadOrgContact = True

    cursor.execute("SELECT * FROM #sp")
    for docId, fragLink, roleName, phone, email in cursor.fetchall():
        protocolPersonLink = lookupProtocolPersonLink(fragLink, docId)
        roleName = roleName or "None"
        role = lookupPersonRole(protocolPersonLink.roles, roleName)
        role.partSitePerson = True
        if phone or email:
            role.partSiteContact = True
except Exception, e:
    raise
    cdrcgi.bail("Failure retrieving report data: %s" % str(e))

#----------------------------------------------------------------------
# Extract information from the Person document.
#----------------------------------------------------------------------
resp = cdr.filterDoc(session, 
                     ['set:Denormalization Person Set',
                      'name:Copy XML for Person 2',
                      'name:Person Protocol Review - Person Info'],
                     id)
if type(resp) in (str, unicode):
    cdrcgi.bail(resp)
html = unicode(resp[0], "utf-8")

#----------------------------------------------------------------------
# Build a table for each of the person's locations.
#----------------------------------------------------------------------
for fragLink in locations:
    docId, fragId = fragLink.split('#')
    table = [u"""\
   <table border='1' width='100%' cellspacing='0' cellpadding='1'>
    <tr>
     <td width='10%' align='center' valign='center' rowspan='2'>
      <b>CDR-ID</b>
     </td>
     <td width='20%' align='center' valign='center' rowspan='2'>
      <b>Primary Protocol ID</b>
     </td>
     <td width='20%' align='center' valign='center' rowspan='2'>
      <b>Current Protocol Status</b>
     </td>
     <td width='20%' align='center' valign='center' rowspan='2'>
      <b>Role</b>
     </td>
     <td valign='center' align='center' colspan='2'>
      <b>Occurs In</b>
     </td>
     <td valign='center' align='center' colspan='2'>
      <b>Specific Contact</b>
     </td>
    </tr>
    <tr>
     <td align='center' valign='center'>
      <b>Lead Org</b>
     </td>
     <td align='center' valign='center'>
      <b>Part Site</b>
     </td>
     <td align='center' valign='center'>
      <b>Lead Org</b>
     </td>
     <td align='center' valign='center'>
      <b>Part Site</b>
     </td>
    </tr>"""]

    protocolPersonLinks = locations[fragLink]
    keys = protocolPersonLinks.keys()
    keys.sort(lambda a, b: cmp(protocolPersonLinks[a],
                               protocolPersonLinks[b]))
    for key in keys:
        protocolPersonLink = protocolPersonLinks[key]
        cssClass           = lookupCssClass(protocolPersonLink.protocol.status)
        roleKeys           = protocolPersonLink.roles.keys()
        roleKeys.sort()
        for roleKey in roleKeys:
            role = protocolPersonLink.roles[roleKey]
            if role.leadOrgPerson:
                addRow(table, cssClass, protocolPersonLink.protocol, role.name,
                       True, False, role.leadOrgContact, False)
            if role.partSitePerson:
                addRow(table, cssClass, protocolPersonLink.protocol, role.name,
                       False, True, False, role.partSiteContact)
    table.append("""\
   </table>""")
    html = re.sub(u"@@FRAGMENTID\["+fragId+"]@@", u"\n".join(table), html)

#----------------------------------------------------------------------
# Add the external site links.
#----------------------------------------------------------------------
class ExternalSitePI:
    def __init__(self, docId):
        self.doc_id   = docId
        self.protocol = protocols[docId]
        self.phone    = False
cursor.execute("SELECT protocol, phone FROM #ep")
rows = cursor.fetchall()
table = u""
if rows:
    externalSitePIs = {}
    for (docId, phone) in rows:
        if docId in externalSitePIs:
            externalSitePI = externalSitePIs[docId]
        else:
            externalSitePI = externalSitePIs[docId] = ExternalSitePI(docId)
        if phone:
            externalSitePI.phone = True
    table = [u"""\
   <b>External sites</b>
   <br />
   <table border='1' cellspacing='0' cellpadding='1'>
    <tr>
     <td align='center' valign='center'>
      <b>CDR-ID</b>
     </td>
     <td align='center' valign='center'>
      <b>Primary Protocol ID</b>
     </td>
     <td align='center' valign='center'>
      <b>Current Protocol Status</b>
     </td>
     <td align='center' valign='center'>
      <b>Specific Contact</b>
     </td>
    </tr>"""]
    
    keys = externalSitePIs.keys()
    def compareProtocols(a, b):
        s1 = externalSitePIs[a]
        s2 = externalSitePIs[b]
        result = cmp(s1.protocol.status, s2.protocol.status)
        if result:
            return result
        return cmp(s1.protocol.protId, s2.protocol.protId)
    keys.sort(compareProtocols)
    for key in keys:
        externalSitePI = externalSitePIs[key]
        protocol = externalSitePI.protocol
        table.append("""\
      <tr%s>
       <td>%s</td>
       <td>%s</td>
       <td>%s</td>
       <td align='center'>%s</td>
      </tr>""" % (lookupCssClass(protocol.status),
                  protocol.docId,
                  protocol.protId,
                  protocol.status or u"&nbsp;",
                  externalSitePI.phone and "X" or "&nbsp;"))
    table.append("""\
     </table>""")
    table = u"\n".join(table)
    #cdrcgi.bail(table)
    #html = html.replace(u"</body>", table + u"</body>")
    #html = html.replace(u"</BODY>", table + u"</BODY>")
html = html.replace(u"@@EXTERNALSITES@@", table)

#----------------------------------------------------------------------
# If there is still a fragment ID left we don't have any protocols
# to display.
#----------------------------------------------------------------------
noprotocol = u"No protocols at this location"
html       = re.sub("@@FRAGMENTID\[.*]@@", noprotocol, html)

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
