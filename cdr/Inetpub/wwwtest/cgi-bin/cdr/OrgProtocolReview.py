#----------------------------------------------------------------------
#
# $Id: OrgProtocolReview.py,v 1.1 2003-08-11 15:50:11 bkline Exp $
#
# Report to assist editors in checking links to a specified org from
# protocols.
#
# $Log: not supported by cvs2svn $
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
script   = "OrgProtocolReview.py"
title    = "CDR Administration"
section  = "Organization Protocol Review Report"
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
     <TD ALIGN='right'><B>Organization Name:&nbsp;</B></TD>
     <TD><INPUT NAME='Name'>
     </TD>
    </TR>
   </TABLE>
   <BR>
   [NOTE: This report can take several minutes to prepare; please be patient.]
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
   <font size='3'>Active, Approved, Temporarily Closed Protocols
                  at this location</font>
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
# Allow the user to select from a list of protocols matching title string.
#----------------------------------------------------------------------
def putUpSelection(rows):
    options = ""
    selected = " SELECTED"
    for row in rows:
        options += """\
    <OPTION VALUE='CDR%010d'%s>CDR%010d: %s</OPTION>
""" % (row[0], selected, row[0], row[1])
        selected = ""
    form = u"""\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <H3>Select organization for report:<H3>
   <SELECT NAME='Id'>
    %s
   </SELECT>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session, options)
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
                SELECT DISTINCT d.id, d.title
                           FROM document d
                           JOIN doc_type t
                             ON t.id = d.doc_type
                          WHERE t.name = 'Organization'
                            AND d.title LIKE ?""", namePattern,
                       timeout = 300)
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure looking up person name '%s': %s" % (name,
                                                                 info[1][0]))
    if len(rows) > 1: putUpSelection(rows)
    if len(rows) < 1: cdrcgi.bail("Unknown organization '%s'" % name)
    id = rows[0][0]

#----------------------------------------------------------------------
# Object for a protocol person.
#----------------------------------------------------------------------
class ProtPerson:
    def __init__(self, name):
        self.name  = name
        self.roles = []

#----------------------------------------------------------------------
# Object type for representing a protocol link to our org document.
#----------------------------------------------------------------------
class ProtLink:
    def __init__(self, docId, protId, loStat):
        self.docId              = docId
        self.protId             = protId
        self.orgStat            = None
        self.loStat             = loStat
        self.personnel          = {}
        self.isLeadOrg          = 0
        self.isOrgSite          = 0
        
#----------------------------------------------------------------------
# Build the base html for the report.
#----------------------------------------------------------------------
filters  = ['name:Organization Protocol Review Report Filter 1',
            'name:Organization Protocol Review Report Filter 2']
response = cdr.filterDoc('guest', filters, id)
if type(response) in (type(''), type(u'')):
    cdrcgi.bail(response)
html = unicode(response[0], 'utf-8')

#----------------------------------------------------------------------
# Shorten role names (at Sheri's request 2003-07-01).
#----------------------------------------------------------------------
def mapRole(role):
    ucRole = role.upper()
    if ucRole == "PRINCIPAL INVESTIGATOR":
        return "PI"
    elif ucRole == "STUDY COORDINATOR":
        return "SC"
    elif ucRole == "PROTOCOL CO-CHAIR":
        return "CC"
    elif ucRole == "PROTOCOL CHAIR":
        return "PC"
    elif ucRole == "UPDATE PERSON":
        return "PUP"
    elif ucRole == "RESEARCH COORDINATOR":
        return "RC"
    return role

#----------------------------------------------------------------------
# Get all the protocols which link to this organization.
#----------------------------------------------------------------------
protLinks = {}
try:

    #------------------------------------------------------------------
    # Links to this org as the lead organization.
    #------------------------------------------------------------------
    cursor.execute("""\
SELECT DISTINCT prot_id.value, prot_id.doc_id, org_stat.value,
                person.title, person_role.value
           FROM query_term org_id
           JOIN query_term prot_id
             ON prot_id.doc_id = org_id.doc_id
            AND LEFT(prot_id.node_loc, 8) = LEFT(org_id.node_loc, 8)
           JOIN query_term org_stat
             ON org_stat.doc_id = org_id.doc_id
            AND LEFT(org_stat.node_loc, 8) = LEFT(org_id.node_loc, 8)
           JOIN query_term person_id
             ON person_id.doc_id = org_id.doc_id
            AND LEFT(person_id.node_loc, 8) = LEFT(org_id.node_loc, 8)
           JOIN query_term person_role
             ON person_role.doc_id = person_id.doc_id
            AND LEFT(person_role.node_loc, 12) = LEFT(person_id.node_loc, 12)
           JOIN document person
             ON person.id = person_id.int_val
          WHERE org_id.int_val   = ?
            AND org_id.path      = '/InScopeProtocol/ProtocolAdminInfo'
                                 + '/ProtocolLeadOrg/LeadOrganizationID'
                                 + '/@cdr:ref'
            AND prot_id.path     = '/InScopeProtocol/ProtocolAdminInfo'
                                 + '/ProtocolLeadOrg/LeadOrgProtocolID'
            AND org_stat.path    = '/InScopeProtocol/ProtocolAdminInfo'
                                 + '/ProtocolLeadOrg/LeadOrgProtocolStatuses'
                                 + '/CurrentOrgStatus/StatusName'
            AND person_id.path   = '/InScopeProtocol/ProtocolAdminInfo'
                                 + '/ProtocolLeadOrg/LeadOrgPersonnel'
                                 + '/Person/@cdr:ref'
            AND person_role.path = '/InScopeProtocol/ProtocolAdminInfo'
                                 + '/ProtocolLeadOrg/LeadOrgPersonnel'
                                 + '/PersonRole'
            /*
            AND org_stat.value IN ('Active',
                                   'Approved-not yet active',
                                   'Temporarily closed') */""", id,
                   timeout = 500)
    for protId, docId, orgStat, personName, role in cursor.fetchall():
        semicolon = personName.find(';')
        if semicolon != -1:
            personName = personName[:semicolon]
        key = (protId, docId, orgStat)
        if not protLinks.has_key(key):
            protLinks[key] = protLink = ProtLink(docId, protId, orgStat)
        else:
            protLink = protLinks[key]
        protLink.isLeadOrg = 1
        if personName:
            if personName not in protLink.personnel:
                person = ProtPerson(personName)
                protLink.personnel[personName] = person
            else:
                person = protLink.personnel[personName]
            role = mapRole(role)
            if role and role not in person.roles:
                person.roles.append(role)

    #------------------------------------------------------------------
    # Links to this org as participating org with specific person.
    #------------------------------------------------------------------
    cursor.execute("""\
SELECT DISTINCT prot_id.value, prot_id.doc_id, org_stat.value,
                person.title, person_role.value, lo_stat.value
           FROM query_term org_id
           JOIN query_term prot_id
             ON prot_id.doc_id = org_id.doc_id
            AND LEFT(prot_id.node_loc, 8) = LEFT(org_id.node_loc, 8)
           JOIN query_term org_stat
             ON org_stat.doc_id = org_id.doc_id
            AND LEFT(org_stat.node_loc, 16) = LEFT(org_id.node_loc, 16)
           JOIN query_term person_id
             ON person_id.doc_id = org_id.doc_id
            AND LEFT(person_id.node_loc, 16) = LEFT(org_id.node_loc, 16)
           JOIN query_term person_role
             ON person_role.doc_id = person_id.doc_id
            AND LEFT(person_role.node_loc, 20) = LEFT(person_id.node_loc, 20)
           JOIN document person
             ON person.id = person_id.int_val
           JOIN query_term lo_stat
             ON lo_stat.doc_id = org_stat.doc_id
            AND LEFT(lo_stat.node_loc, 8) = LEFT(org_stat.node_loc, 8)
          WHERE org_id.int_val   = ?
            AND org_id.path      = '/InScopeProtocol/ProtocolAdminInfo'
                                 + '/ProtocolLeadOrg/ProtocolSites'
                                 + '/OrgSite/OrgSiteID/@cdr:ref'
            AND prot_id.path     = '/InScopeProtocol/ProtocolAdminInfo'
                                 + '/ProtocolLeadOrg/LeadOrgProtocolID'
            AND org_stat.path    = '/InScopeProtocol/ProtocolAdminInfo'
                                 + '/ProtocolLeadOrg/ProtocolSites'
                                 + '/OrgSite/OrgSiteStatus'
            AND person_id.path   = '/InScopeProtocol/ProtocolAdminInfo'
                                 + '/ProtocolLeadOrg/ProtocolSites'
                                 + '/OrgSite/OrgSiteContact'
                                 + '/SpecificPerson/Person/@cdr:ref'
            AND person_role.path = '/InScopeProtocol/ProtocolAdminInfo'
                                 + '/ProtocolLeadOrg/ProtocolSites'
                                 + '/OrgSite/OrgSiteContact'
                                 + '/SpecificPerson/Role'
            AND lo_stat.path     = '/InScopeProtocol/ProtocolAdminInfo'
                                 + '/ProtocolLeadOrg/LeadOrgProtocolStatuses'
                                 + '/CurrentOrgStatus/StatusName'
/*
            AND org_stat.value IN ('Active',
                                   'Approved-not yet active',
                                   'Temporarily closed')
                                   */""", id, timeout = 500)
    for protId, docId, orgStat, personName, role, loStat in cursor.fetchall():
        semicolon = personName.find(';')
        if semicolon != -1:
            personName = personName[:semicolon]
        key = (protId, docId, loStat)
        if not protLinks.has_key(key):
            protLinks[key] = protLink = ProtLink(docId, protId, loStat)
        else:
            protLink = protLinks[key]
        protLink.isOrgSite = 1
        protLink.orgStat = orgStat
        if personName:
            if personName not in protLink.personnel:
                person = ProtPerson(personName)
                protLink.personnel[personName] = person
            else:
                person = protLink.personnel[personName]
            role = mapRole(role)
            if role and role not in person.roles:
                person.roles.append(role)

    #------------------------------------------------------------------
    # Links to this org as participating org with generic person.
    #------------------------------------------------------------------
    cursor.execute("""\
SELECT DISTINCT prot_id.value, prot_id.doc_id, org_stat.value,
                person.value, lo_stat.value
           FROM query_term org_id
           JOIN query_term prot_id
             ON prot_id.doc_id = org_id.doc_id
            AND LEFT(prot_id.node_loc, 8) = LEFT(org_id.node_loc, 8)
           JOIN query_term org_stat
             ON org_stat.doc_id = org_id.doc_id
            AND LEFT(org_stat.node_loc, 16) = LEFT(org_id.node_loc, 16)
           JOIN query_term person
             ON person.doc_id = org_id.doc_id
            AND LEFT(person.node_loc, 16) = LEFT(org_id.node_loc, 16)
           JOIN query_term lo_stat
             ON lo_stat.doc_id = org_stat.doc_id
            AND LEFT(lo_stat.node_loc, 8) = LEFT(org_stat.node_loc, 8)
          WHERE org_id.int_val   = ?
            AND org_id.path      = '/InScopeProtocol/ProtocolAdminInfo'
                                 + '/ProtocolLeadOrg/ProtocolSites'
                                 + '/OrgSite/OrgSiteID/@cdr:ref'
            AND prot_id.path     = '/InScopeProtocol/ProtocolAdminInfo'
                                 + '/ProtocolLeadOrg/LeadOrgProtocolID'
            AND org_stat.path    = '/InScopeProtocol/ProtocolAdminInfo'
                                 + '/ProtocolLeadOrg/ProtocolSites'
                                 + '/OrgSite/OrgSiteStatus'
            AND person.path      = '/InScopeProtocol/ProtocolAdminInfo'
                                 + '/ProtocolLeadOrg/ProtocolSites'
                                 + '/OrgSite/OrgSiteContact'
                                 + '/GenericPerson/PersonTitle'
            AND lo_stat.path     = '/InScopeProtocol/ProtocolAdminInfo'
                                 + '/ProtocolLeadOrg/LeadOrgProtocolStatuses'
                                 + '/CurrentOrgStatus/StatusName'
/*
            AND org_stat.value IN ('Active',
                                   'Approved-not yet active',
                                   'Temporarily closed')
                                   */ """, id, timeout = 500)
    for protId, docId, orgStat, personName, loStat in cursor.fetchall():
        key = (protId, docId, loStat)
        if not protLinks.has_key(key):
            protLinks[key] = protLink = ProtLink(docId, protId, loStat)
        else:
            protLink = protLinks[key]
        protLink.isOrgSite = 1
        protLink.orgStat = orgStat
        if personName and personName not in protLink.personnel:
            protLink.personnel[personName] = ProtPerson(personName)

except cdrdb.Error, info:
    cdrcgi.bail('Failure fetching protocols: %s' % info[1][0])

#----------------------------------------------------------------------
# Build the table.
#----------------------------------------------------------------------
table = """\
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th rowspan='2'>Protocol ID</th>
    <th rowspan='2'>Doc ID</th>
    <th rowspan='2'>Lead Org Status</th>
    <th rowspan='2'>Org Status</th>
    <th colspan='2'>Participation</th>
    <th rowspan='2'>Person</th>
   </tr>
   <tr>
    <th>Lead Org</th>
    <th>Org Site</th>
   </tr>
"""

#----------------------------------------------------------------------
# Sort by status, then by protocol id.
#----------------------------------------------------------------------
keys = protLinks.keys()
statusOrder = {
    'ACTIVE': 1,
    'APPROVED-NOT YET ACTIVE': 2,
    'TEMPORARILY CLOSED': 3,
    'CLOSED': 4,
    'COMPLETED': 5
    }
def sorter(a, b):
    # key[0] is protId; key[1] is docId; key[2] is lead org status
    if a[2] == b[2]:
        if a[0] == b[0]:
            return cmp(a[1], b[1])
        return cmp(a[0], b[0])
    return cmp(statusOrder.get(a[2].upper(), 999),
               statusOrder.get(b[2].upper(), 999))
keys.sort(sorter)
for key in keys:
    protLink = protLinks[key]
    person = ""
    for protPerson in protLink.personnel:
        pp = protLink.personnel[protPerson]
        if person:
            person += "<br>\n"
        person += pp.name
        if pp.roles:
            sep = " ("
            for role in pp.roles:
                person += sep + role
                sep = ", "
            person += ")"
    if not person:
        person = "&nbsp;"
    leadOrg = protLink.isLeadOrg and "X" or "&nbsp;"
    orgSite = protLink.isOrgSite and "X" or "&nbsp;"
    if not protLink.orgStat:
        protLink.orgStat = protLink.loStat
    table += """\
   <tr>
    <td valign='top'>%s</td>
    <td valign='top' align='center'>%d</td>
    <td valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td valign='top' align='center'>%s</td>
    <td valign='top' align='center'>%s</td>
    <td valign='top'>%s</td>
   </tr>
""" % (protLink.protId, protLink.docId, protLink.loStat, protLink.orgStat,
       leadOrg, orgSite, person)

cdrcgi.sendPage(html.replace("@@DOC-ID@@", "CDR%010d" % id)
                    .replace("@@TABLE@@", table))
cdrcgi.sendPage("""\
<html>
 <head>
  <title>%d</title>
 </head>
 <body>
%s
 </body>
</html>""" % (id, table))

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
