#----------------------------------------------------------------------
#
# $Id: PersonProtocolReview.py,v 1.8 2004-11-08 21:07:32 venglisc Exp $
#
# Report to assist editors in checking links to a specified person from
# protocols.
#
# $Log: not supported by cvs2svn $
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
    htmlFrag += """\
  <table border = '1' cellpadding = '0' cellspacing = '2'>
   <tr>
    <td width='25%%' align='center' valign='bottom'>
     <b>Protocol ID</b>
    </td>
    <td width='15%%' align='center' valign='bottom'>
     <b>CDR-ID</b>
    </td>
    <td width='15%%' align='center' valign='bottom'>
     <b>Org Protocol Status</b>
    </td>
    <td width='15%%' align='center' valign='bottom'>
     <b>Overall Protocol Status</b>
    </td>
    <td width='15%%' align='center' valign='bottom'>
     <b>Lead Org Role</b>
    </td>
    <td width='25%%' align='center' valign='bottom'>
     <b>Role</b>
    </td>
   </tr>
"""

    for link in pLinks:
        htmlFrag += """\
    <tr>
    <td>
     <font size = '3'>%s</font>
    </td>
    <td>
     <font size = '3'>%s</font>
    </td>
    <td>
     <font size = '3'>%s</font>
    </td>
    <td>
     <font size = '3'>%s</font>
    </td>
    <td>
     <font size = '3'>%s</font>
    </td>
    <td>
     <font size = '3'>%s</font>
    </td>
   </tr>
""" % (link.ids, 'none', link.statuses, 'none', link.orgRoles, link.roles)

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
  </table>
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

# Recreate two Temp tables for this run
# -------------------------------------
try:
    query = """\
        CREATE TABLE #persprotrev1
          (doc_id          varchar(512) NOT NULL, 
           person_fragment varchar(512) NOT NULL, 
           protocol_id     INTEGER      NOT NULL,
           protocol_status varchar(512) NOT NULL, 
           person_id       varchar(512) NOT NULL, 
           islead          varchar(10)  NOT NULL
          )
"""
    cursor.execute(query)
except cdrdb.Error, info:
    cdrcgi.bail('Failure creating #persprotrev1: %s' % info[1][0])


try:
    query = """\
        CREATE TABLE #persprotrev2 
          (protocol_id          INTEGER      NOT NULL, 
           person_fragment varchar(512) NOT NULL,
           role            varchar(512) NOT NULL,
           roletype        varchar(10)  NOT NULL, 
           spec_info       varchar(1)
          )
"""
    cursor.execute(query)
except cdrdb.Error, info:
    cdrcgi.bail('Failure creating #persprotrev2: %s' % info[1][0])

# Populate first temp table
# -------------------------
try:
    query = """\
       INSERT INTO #persprotrev1
       SELECT ProtID.value doc_id, CDRID.value person_fragment, 
              CDRID.doc_id protocol_id,  Status.value  protocol_status, 
              CDRID.int_val person_id, 
              CASE WHEN CDRID.path =   '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                                     + '/LeadOrgPersonnel/Person/@cdr:ref'  THEN 'Lead'
                   WHEN CDRID.path =   '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                                     + '/ProtocolSites/OrgSite/OrgSiteContact'
                                     + '/SpecificPerson/Person/@cdr:ref'    THEN 'Site'
                   ELSE 'Unknown'
              END islead 
         FROM query_term CDRID
         JOIN query_term ProtID
           ON CDRID.doc_id = ProtID.doc_id
         JOIN query_term Status
           ON CDRID.doc_id = Status.doc_id
        WHERE CDRID.int_val = ?    -- Person ID is passed to the script
          AND (CDRID.path =   '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                            + '/LeadOrgPersonnel/Person/@cdr:ref'
           OR CDRID.path  =   '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                            + '/ProtocolSites/OrgSite/OrgSiteContact'
                            + '/SpecificPerson/Person/@cdr:ref'
              )
          AND ProtID.path = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
          AND Status.path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
        ORDER BY Status.value, protID.value, CDRID.doc_id, IsLead
"""
    cursor.execute(query, id)
except cdrdb.Error, info:
    cdrcgi.bail('Failure populating #persprotrev1: %s' % info[1][0])


# Populate second temp table
# --------------------------
try:
    query = """\
      INSERT INTO #persprotrev2
      SELECT role.doc_id, person.value, role.value, 'Lead', null
        FROM query_term role
        JOIN query_term person
          ON role.doc_id = person.doc_id
       WHERE role.path   =   '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                           + '/LeadOrgPersonnel/PersonRole'
         AND person.path =   '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                           + '/LeadOrgPersonnel/Person/@cdr:ref'
         AND role.doc_id in (select protocol_id from #persprotrev1)
         AND person.int_val = %s
         AND left(role.node_loc, 12) = left(person.node_loc, 12)
       ORDER BY role.doc_id
""" % id
    cursor.execute(query, timeout = 120)
except cdrdb.Error, info:
    cdrcgi.bail('Failure populating #persprotrev2 - Lead: %s' % info[1][0])

# Populate second temp table
# --------------------------
try:
    query = """\
      INSERT INTO #persprotrev2
      SELECT role.doc_id, person.value, role.value, 'Site', NULL
        FROM query_term role
        JOIN query_term person
          ON role.doc_id = person.doc_id
       WHERE role.path   =   '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                           + '/ProtocolSites/OrgSite/OrgSiteContact/SpecificPerson/Role'
         AND person.path =   '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                           + '/ProtocolSites/OrgSite/OrgSiteContact/SpecificPerson'
                           + '/Person/@cdr:ref'
         AND role.doc_id in (select protocol_id from #persprotrev1)
         AND person.int_val = %s
         AND left(role.node_loc, 24) = left(person.node_loc, 24)
""" % id 
    cursor.execute(query, timeout = 120)
    conn.commit()
except cdrdb.Error, info:
    cdrcgi.bail('Failure populating #persprotrev2 - Site: %s' % info[1][0])

# Update special contact information
# ----------------------------------
try:
    query = """\
      UPDATE #persprotrev2 SET spec_info = 'Y'
      WHERE EXISTS (
            SELECT protocol.doc_id Protocol, protocol.value Person 
              FROM query_term protocol
              JOIN query_term specific
                ON protocol.doc_id = specific.doc_id
              JOIN #persprotrev1
                ON protocol.doc_id = #persprotrev1.protocol_id
               AND protocol.value  = #persprotrev1.person_fragment
             WHERE protocol.path =   '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                                   + '/LeadOrgPersonnel/Person/@cdr:ref'
               AND specific.path =   '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                                   + '/LeadOrgPersonnel/ProtocolSpecificContact/@cdr:id'
               AND left(protocol.node_loc, 8) = left(specific.node_loc, 8)
               AND #persprotrev2.protocol_id = protocol.doc_id
               AND #persprotrev2.person_fragment = protocol.value  
               AND #persprotrev2.roletype = 'Lead'
            )
"""
    cursor.execute(query, timeout = 120)
    conn.commit()
except cdrdb.Error, info:
    cdrcgi.bail('Failure updating #persprotrev2 - Lead: %s' % info[1][0])

# Update special contact information
# ----------------------------------
try:
    query = """\
      UPDATE #persprotrev2 SET spec_info = 'Y'
       WHERE EXISTS (
             SELECT protocol.doc_id Protocol, protocol.value Person
               FROM query_term protocol
               JOIN query_term specific
                 ON protocol.doc_id = specific.doc_id
               JOIN #persprotrev1
                 ON protocol.doc_id = #persprotrev1.protocol_id
                AND protocol.value  = #persprotrev1.person_fragment
              WHERE protocol.path  =   '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                                     + '/ProtocolSites/OrgSite/OrgSiteContact'
                                     + '/SpecificPerson/Person/@cdr:ref'
                AND (specific.path =   '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                                     + '/ProtocolSites/OrgSite/OrgSiteContact'
                                     + '/SpecificPerson/SpecificPhone'
                 OR specific.path  =   '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                                     + '/ProtocolSites/OrgSite/OrgSiteContact'
                                     + '/SpecificPerson/SpecificEmail'
             )
         AND left(protocol.node_loc, 24) = left(specific.node_loc, 24)
         AND #persprotrev2.protocol_id = protocol.doc_id
         AND #persprotrev2.person_fragment = protocol.value  
         AND #persprotrev2.roletype = 'Site'
)
"""
    cursor.execute(query, timeout = 120)
    conn.commit()
except cdrdb.Error, info:
    cdrcgi.bail('Failure updating #persprotrev2 - Site: %s' % info[1][0])

links = {}

#----------------------------------------------------------------------
# Extract information from the Person document.
#----------------------------------------------------------------------
resp = cdr.filterDoc(session, 
                     ['set:Denormalization Person Set',
		      'name:Copy XML for Person 2',
		      'name:Person Protocol Review - Person Info'],
                     id)
html = unicode(resp[0], "utf-8")
if type(resp) in (type(''), type(u'')):
    cdrcgi.bail(resp)
#----------------------------------------------------------------------
# Start the page.
#----------------------------------------------------------------------

try:
    query = """\
        SELECT DISTINCT person_fragment 
          FROM #persprotrev1 
"""
    cursor.execute(query)
except cdrdb.Error, info:
    cdrcgi.bail('Failure selecting fragment IDs: %s' % info[1][0])
fragId = cursor.fetchall()

frag = []
for row in fragId:
    id,frag = row[0].split('#')
    # cdrcgi.bail("id = %s, frag = %s" % (id, frag))
    prottable = """
    <table border="1" width="100%" cellspacing="0" cellpadding="0">
"""
    # Create the table header 
    # -----------------------
    tabheader = """
    <tr>

     <td width="15%" align="center" valign="bottom">
      <b>CDR-ID</b>
     </td>
     <td width="20%" align="center" valign="bottom">
      <b>Lead Org Protocol ID</b>
     </td>
     <td width="20%" align="center" valign="bottom">
      <b>Lead Org Current Protocol Status</b>

     </td>
     <td width="15%" align="center" valign="bottom">
      <b>Role</b>
     </td>
     <td valign="bottom"> 
      <table border="1" cellpadding="0" cellspacing="0" frame="void">
       <tr> 
        <td align="center" colspan="2" align="center">
         <b>Occurs in</b>

        </td>
       </tr>
       <tr>
        <td align="center" width="50%">
         <b>Lead Org</b>
        </td>
        <td align="center" width="50%">
         <b>Part Site</b>
 
        </td>
       </tr>
      </table>
     </td>
     <td valign="bottom"> 
      <table border="1" cellpadding="0" cellspacing="0" frame="void">
       <tr> 
        <td align="center" colspan="2" align="center">
         <b>Specific Contact</b>

        </td>
       </tr>
       <tr>
        <td align="center" width="50%">
         <b>Lead Org</b>
        </td>
        <td align="center" width="50%">
         <b>Part Site</b>
 
        </td>
       </tr>
      </table>
     </td>
    </tr>
"""
    # Select the protocol rows from the temp tables by fragment ID
    # ------------------------------------------------------------
    #cdrcgi.bail(id + "#" + frag)
    try:
        query = """\
                SELECT v1.protocol_id, v1.doc_id,  
                       CASE WHEN v1.protocol_status = 'Approved-not yet active'
		              THEN 'Approved'
                            WHEN v1.protocol_status = 'Temporarily closed' 
			      THEN 'Temp closed'
                            ELSE v1.protocol_status
                       END protocol_status, 
                       v2.role, v1.islead, v2.roletype, 
		       COALESCE (v2.spec_info, 'N') spec_info
                  FROM #persprotrev1 v1
                  JOIN #persprotrev2 v2
                    ON v1.protocol_id = v2.protocol_id
                   AND v1.person_fragment = v2.person_fragment
                   AND v1.islead = v2.roletype
                 WHERE v1.person_fragment = '%s'
                 ORDER BY v1.protocol_status, v1.doc_id
""" % (id + "#" + frag)

        cursor.execute(query)
    except cdrdb.Error, info:
        cdrcgi.bail('Failure selecting fragment IDs: %s' % info[1][0])

    protocols = cursor.fetchall()

    # Create a row for the protocol table one record at a time
    # The first four elements are placed into one cell each.
    # A background color is being set based on the status of the protocol
    # -------------------------------------------------------------------
    protrow = ""
    for prot in protocols:
	if prot[2] == 'Active' or prot[2] == 'Approved':
            protrow += """
      <tr>
       <td>%s</td>
       <td>%s</td>
       <td>%s</td>
       <td>%s</td>
""" % (prot[0], prot[1], prot[2], prot[3])
	elif prot[2] == '':
            protrow += """
      <tr class="status_err">
       <td>%s</td>
       <td>%s</td>
       <td>%s</td>
       <td>%s</td>
""" % (prot[0], prot[1], prot[2], prot[3])
	else:
            protrow += """
      <tr class="status_closed">
       <td>%s</td>
       <td>%s</td>
       <td>%s</td>
       <td>%s</td>
""" % (prot[0], prot[1], prot[2], prot[3])

	# The fifth and sixth cells are populated based on the contend of 
	# the query element five indicating if the information is for a 
	# Lead org (Lead) or Participant (Site).
	# ----------------------------------------------------------------
        if prot[4] == 'Lead':
            protrow += """
       <td>
        <table width="100%" border="1" cellpadding="0" cellspacing="0" frame="void">
	 <tr>
          <td align="center" width="50%">X</td>
          <td align="center" width="50%"></td>
	 </tr>
	</table>
       </td>
"""
        else:
            protrow += """
       <td>
        <table width="100%" border="1" cellpadding="0" cellspacing="0" frame="void">
	 <tr>
          <td align="center" width="50%"></td>
          <td align="center" width="50%">X</td>
	 </tr>
	</table>
       </td>
"""
	# The last two columns specify if the person included specific
	# information or not.
	# For the combination (Lead, Y) mark the seventh column with an X
	# For the combination (Site, Y) mark the eight column with an X
	# Otherwise no X is placed in either column
	# ---------------------------------------------------------------
        if prot[5] == 'Lead' and prot[6] == 'Y':
            protrow += """
       <td>
        <table width="100%" border="1" cellpadding="0" cellspacing="0" frame="void">
	 <tr>
          <td align="center" width="50%">X</td>
          <td align="center" width="50%"></td>
	 </tr>
	</table>
       </td>
"""
        elif prot[5] == 'Site' and prot[6] == 'Y':
            protrow += """
       <td>
        <table width="100%" border="1" cellpadding="0" cellspacing="0" frame="void">
	 <tr>
          <td align="center" width="50%"></td>
          <td align="center" width="50%">X</td>
	 </tr>
	</table>
       </td>
      </tr>
"""
        else:
            protrow += """
       <td>
        <table width="100%" border="1" cellpadding="0" cellspacing="0" frame="void">
	 <tr>
          <td align="center" width="50%">&nbsp;</td>
          <td align="center" width="50%"></td>
	 </tr>
	</table>
       </td>
      </tr>
"""
    prottable += tabheader + protrow
    prottable += """
   </table> 
"""

    html    = re.sub("@@FRAGMENTID\["+frag+"]@@", prottable, html)

# If there is still a fragment ID left we don't have any protocols
# to display.
# ----------------------------------------------------------------
noprotocol = "No protocol at this location"
html    = re.sub("@@FRAGMENTID\[.*]@@", noprotocol, html)

#----------------------------------------------------------------------
# Send the page back to the browser.
#----------------------------------------------------------------------
cdrcgi.sendPage(html)
