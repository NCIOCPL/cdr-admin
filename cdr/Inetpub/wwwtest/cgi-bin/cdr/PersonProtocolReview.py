#----------------------------------------------------------------------
#
# $Id: PersonProtocolReview.py,v 1.5 2003-08-25 20:24:43 bkline Exp $
#
# Report to assist editors in checking links to a specified person from
# protocols.
#
# $Log: not supported by cvs2svn $
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
# Generate HTML for protocols linked to a specific location.
#----------------------------------------------------------------------
def showProtocols(fragId):
    pLinks = links.get(fragId, [])
    htmlFrag = """\
  <b>
   <font size='3'>Protocols at this location</font>
  </b>
  <br />
"""
    if not pLinks:
        return htmlFrag + """\
  No protocols
  <br />
  <br />
"""
    pLinks.sort(lambda a, b: cmp(a.sortKey, b.sortKey))
    for link in pLinks:
        htmlFrag += """\
  <table border = '0' cellpadding = '0' cellspacing = '2'>
   <tr>
    <td nowrap = '1' valign = 'top' align = 'right'>
     <font size = '3'>Protocol ID</font>
    <td>
    <td nowrap = '1' align = 'right' valign = 'top'>
     <font size = '3'>%s</font>
    </td>
    <td>
     <font size = '3'>%s</font>
    </td>
   </tr>
   <tr>
    <td nowrap = '1' valign = 'top' align = 'right'>
     <font size = '3'>Lead Org Role</font>
    <td>
    <td nowrap = '1' align = 'right' valign = 'top'>
     <font size = '3'>%s</font>
    </td>
    <td>
     <font size = '3'>%s</font>
    </td>
   </tr>
   <tr>
    <td nowrap = '1' valign = 'top' align = 'right'>
     <font size = '3'>Current Protocol Status</font>
    <td>
    <td nowrap = '1' align = 'right' valign = 'top'>
     <font size = '3'>%s</font>
    </td>
    <td>
     <font size = '3'>%s</font>
    </td>
   </tr>
   <tr>
    <td nowrap = '1' valign = 'top' align = 'right'>
     <font size = '3'>Role</font>
    <td>
    <td nowrap = '1' align = 'right' valign = 'top'>
     <font size = '3'>%s</font>
    </td>
    <td>
     <font size = '3'>%s</font>
    </td>
   </tr>
  </table>
  <br />
""" % (ellipsis, ", ".join(link.ids), 
       ellipsis, ", ".join(link.orgRoles),
       ellipsis, ", ".join(link.statuses),
       ellipsis, ", ".join(link.roles))
        if link.specificContact:
            htmlFrag += """\
  SpecificContact
  <br />
"""
            for child in link.specificContact.childNodes:
                if child.nodeName == "Line":
                    htmlFrag += """\
  %s
  <br />
""" % cdr.getTextContent(child)
            htmlFrag += """\
  <br />
"""

    return htmlFrag + """\
  <br />
"""

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
# Object type for representing a protocol link to our person document.
#----------------------------------------------------------------------
class P2PLink:
    def __init__(self, docId, linkType, ids, statuses, roles, orgRoles,
                 specificContact = None):
        self.docId              = docId
        self.linkType           = linkType
        self.ids                = ids
        self.statuses           = statuses
        self.roles              = roles
        self.orgRoles           = orgRoles
        self.specificContact    = specificContact
        self.sortKey            = 100
        if linkType in ('PrivatePracticeSite', 'SpecificPerson'):
            self.sortKey        = 200
        if 'Approved-not yet active' in statuses:
            self.sortKey       += 1
        elif 'Active' in statuses:
            self.sortKey       += 2
        elif 'Temporarily closed' in statuses:
            self.sortKey       += 3
        elif 'Closed' in statuses:
            self.sortKey       += 4
        elif 'Completed' in statuses:
            self.sortKey       += 5
        else: # unknown?
            self.sortKey       += 6
        
#----------------------------------------------------------------------
# Get all the protocols which link to this person.
#----------------------------------------------------------------------
pathStart = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg/'
linkPaths = [
    'LeadOrgPersonnel/Person/@cdr:ref',
    'ProtocolSites/OrgSite/OrgSiteContact/SpecificPerson/Person/@cdr:ref',
    'ProtocolSites/PrivatePracticeSite/PrivatePracticeSiteID/@cdr:ref'
]
statPath = 'LeadOrgProtocolStatuses/CurrentOrgStatus/StatusName'
for i in range(len(linkPaths)):
    linkPaths[i] = pathStart + linkPaths[i]
statPath = pathStart + statPath

try:
    query = """\
        SELECT DISTINCT link.doc_id, 
                        link.value
                   FROM query_term link
                   JOIN query_term org_status
                     ON org_status.doc_id = link.doc_id
                    AND LEFT(org_status.node_loc, 8) =
                        LEFT(link.node_loc, 8)
                  WHERE link.int_val = ?
                    AND link.path IN ('%s', '%s', '%s')
                    AND org_status.path = '%s'
                    AND org_status.value IN (
                        'Active',
                        'Approved-not yet active',
                        'Temporarily closed',
                        'Completed',
                        'Closed'
                        )""" % (linkPaths[0], 
                                linkPaths[1], 
                                linkPaths[2],
                                statPath)
    cursor.execute(query, id)
    #cdrcgi.bail("got %d rows" % len(cursor.fetchall()))
    links = {}
    for row in cursor.fetchall():
        linkPieces = row[1].split('#', 1)
        if len(linkPieces) == 2 and linkPieces[1]:
            fragId = linkPieces[1]
            if not links.has_key(fragId):
                links[fragId] = []
            resp = cdr.filterDoc(session,
                             ['name:Person Protocol Review Report Filter 2'],
                             row[0], parm = [('personLink', row[1])])
            if type(resp) in (type(''), type(u'')):
                cdrcgi.bail(resp)
            protocol = xml.dom.minidom.parseString(resp[0]).documentElement
            for child in protocol.childNodes:
                if child.nodeName in ('LeadOrgPersonnel',
                                      'PrivatePracticeSite',
                                      'SpecificPerson'):
                    linkType        = child.nodeName
                    ids             = []
                    statuses        = []
                    roles           = []
                    orgRoles        = []
                    specificContact = None
                    for grandchild in child.childNodes:
                        if grandchild.nodeName == 'Id':
                            ids.append(cdr.getTextContent(grandchild))
                        elif grandchild.nodeName == 'Status':
                            statuses.append(cdr.getTextContent(grandchild))
                        elif grandchild.nodeName == 'PersonRole':
                            roles.append(cdr.getTextContent(grandchild))
                        elif grandchild.nodeName == 'OrgRole':
                            orgRoles.append(cdr.getTextContent(grandchild))
                        elif grandchild.nodeName == 'SpecificContact':
                            specificContact = grandchild
                    pLink = P2PLink(row[0], linkType, ids, statuses, roles,
                                    orgRoles, specificContact)
                    links[fragId].append(pLink)

except cdrdb.Error, info:
    cdrcgi.bail('Failure fetching protocols: %s' % info[1][0])

#----------------------------------------------------------------------
# Extract information from the Person document.
#----------------------------------------------------------------------
resp = cdr.filterDoc(session, 
                     ['name:Person Protocol Review Report Filter 1'],
                     id)
if type(resp) in (type(''), type(u'')):
    cdrcgi.bail(resp)
person = xml.dom.minidom.parseString(resp[0]).documentElement
oplList = []
ppList = []
pName = None
pSuffix = ''
for child in person.childNodes:
    if child.nodeName == 'Name':
        pName = cdr.getTextContent(child)
    elif child.nodeName == 'ProfessionalSuffix':
        pSuffix = cdr.getTextContent(child)
    elif child.nodeName == 'OtherPracticeLocation':
        oplList.append(child)
    elif child.nodeName == 'PrivatePracticeLocation':
        ppList.append(child)
if pName is None:
    cdrcgi.bail("Failure extracting name for CDR%010d" % id)

#----------------------------------------------------------------------
# Start the page.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>CDR%010d - %s - %s</title>
  <meta name="ProgId" content="Word.Document">
 </head>
 <basefont face='Arial, Helvetica, sans-serif'>
 <body>
  <hr />
  <b>
   <font size='4'>PERSON PROTOCOL REVIEW REPORT</font>
  </b>
  <br />
  <br />
  <b>
   <font size='4'>Name</font>
  </b>
  <br />
  <br />
  %s
  <br />
  <br />
  <b>
   <font size='4'>Locations</font>
  </b>
  <br />
  <br />
  <b>
   <u>
    <font size='3'>Private Practice</font>
   </u>
  </b>
  <br />
  <br />
""" % (id, pName, time.strftime("%B %d, %Y"), pName + pSuffix)


#----------------------------------------------------------------------
# List the private practice locations.
#----------------------------------------------------------------------
num = 1
for pp in ppList:
    loc = None
    for child in pp.childNodes:
        if child.nodeName == 'Location':
            loc = child
            break
    if loc is None:
        cdrcgi.bail("Missing Location information for private practice %d" %
                    num)
    prevLoc = pp.getAttribute("PreviousLocation")
    if prevLoc:
        prevLoc = " (Previous Location = %s)" % prevLoc
    html += """\
  <b>
   <i>
    <font size='3'>%d.%s</font>
   </i>
  </b>
  <br />
  <font size='3'>
""" % (num, prevLoc)
    for child in loc.childNodes:
        if child.nodeName == 'Line':
            html += """\
  %s<br />
""" % cdr.getTextContent(child)
    html += """\
  </font>
  <br />
"""
    fragId = pp.getAttribute("id")
    if fragId:
        html += showProtocols(fragId)
    num += 1


#----------------------------------------------------------------------
# List the other practice locations.
#----------------------------------------------------------------------
html += """\
  <br />
  <br />
  <b>
   <u>
    <font size='3'>Other Practice Locations</font>
   </u>
  </b>
  <br />
  <br />
"""

num = 1
for opl in oplList:
    loc = None
    orgName = None
    pTitle = None
    for child in opl.childNodes:
        if child.nodeName == 'OrgName':
            orgName = cdr.getTextContent(child)
        elif child.nodeName == 'PersonTitle':
            pTitle = cdr.getTextContent(child)
        elif child.nodeName == 'Location':
            loc = child
    if not loc:
        cdrcgi.bail("Missing Location information")
    if not orgName:
        cdrcgi.bail("Missing org name for other practice location %d" % num)
    prevLoc = opl.getAttribute("PreviousLocation")
    if prevLoc:
        prevLoc = " (Previous Location = %s)" % prevLoc
    html += """\
  <b>
   <i>
    <font size='3'>%d. %s%s</font>
   </i>
  </b>
  <br />
  <font size='3'>
""" % (num, orgName, prevLoc)
    if pTitle:
        html += """\
  %s<br />
""" % pTitle
    for child in loc.childNodes:
        if child.nodeName == 'Line':
            html += """\
  %s<br />
""" % cdr.getTextContent(child)
    html += """\
  </font>
  <br />
"""
    fragId = opl.getAttribute("id")
    if fragId:
        html += showProtocols(fragId)
    num += 1


#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html + """\
 </body>
</html>
""")
