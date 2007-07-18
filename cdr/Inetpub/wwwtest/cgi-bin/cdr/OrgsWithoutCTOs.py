import cdr, cdrdb, cdrcgi, cgi, re, string, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
SUBMENU = "Report Menu"
buttons = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "OrgsWithoutCTOs.py"
title   = "CDR Administration"
section = """Organizations (without CTO's) Linked to Protocols"""
header  = cdrcgi.header(title, title, section, script, buttons)

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
# Class for storing the organization information
#----------------------------------------------------------------------
class Organization:
    def __init__(self, id, name, phone, website):
        self.id = id
        splitName = name.split(";")
        self.name = splitName[0]
        self.phone = phone
        self.websiteURL = website
        self.websiteHTML = website.replace(';',';<wbr>').replace('?','?<wbr>').replace("""/""","""/<wbr>""")

organizations = {}

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#--------------------------------------------------
# Fetch the data
#--------------------------------------------------
sQuery ="""SELECT d.id, d.title, phone.value, website.value
             FROM document d
             JOIN query_term status
               ON status.doc_id = d.id
             JOIN query_term country
               ON country.doc_id = d.id
             JOIN query_term phone
               ON phone.doc_id = d.id
             JOIN query_term website
               ON website.doc_id = d.id
            WHERE status.path = '/Organization/Status/CurrentStatus'
              AND status.value = 'Active'
              AND country.path = '/Organization/OrganizationLocations/OrganizationLocation/Location/PostalAddress/Country'
              AND country.value = 'U.S.A.'
              AND phone.path = '/Organization/OrganizationLocations/OrganizationLocation/Location/Phone'
              AND website.path = '/Organization/OrganizationLocations/OrganizationLocation/Location/WebSite/@cdr:xref'
              AND d.doc_type = 22
              AND d.id not in ( SELECT distinct(doc_id)
                                  FROM query_term 
                                 WHERE path like '/Organization/OrganizationLocations/ClinicalTrialsOfficeContact/%%')
              AND d.id in ( SELECT distinct(q.int_val)
                              FROM query_term q
                              JOIN query_term protocol_status
                                ON protocol_status.doc_id = q.doc_id 
                             WHERE q.path = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg/LeadOrganizationID/@cdr:ref'
                               AND protocol_status.path = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
                               AND protocol_status.value in ('Active','Approved-not yet active','Temporarily closed'))
    """

try:
    cursor.execute(sQuery,timeout=300)
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database query failure: %s' % info[1][0])
for id, name, phone, website in rows:
    if id not in organizations:
        organizations[id] = Organization(id,name,phone,website)

#----------------------------------------------------------------------
# Make the list of organizations
#----------------------------------------------------------------------
def makeOrganizationTable(organizations):
    keys = organizations.keys()
    keys.sort(lambda a,b: cmp(organizations[a].name, organizations[b].name))
    BGColor = "white"
    html = u"""\
"""
    for key in keys:
        organization = organizations[key]
        html += """\
        <TR style='background-color: %s;'>
         <TD>%s</TD>
         <TD>%s</TD>
         <TD>%s</TD>
         <TD><a href ='%s'>%s</a></TD>
        </TR>
""" % (BGColor,organization.id, organization.name,organization.phone,organization.websiteURL,organization.websiteHTML)
        if BGColor == 'white':
            BGColor = 'Gainsboro'
        else:
            BGColor = 'white'
    return html
        
#--------------------------------------------------
# display the report
#--------------------------------------------------
now     = time.localtime(time.time())
sDate   = time.strftime("%b %d, %Y", now)

form = """\
<style type='text/css'>
   table.cdr
   {
      font-size: 10pt;
      font-family:'Arial';
      color:blue;
      margin-bottom: 10pt;
      font-weight:normal;
      padding: 1px;
      border: 0;
   }
   table.cdr td
   {   
      color:blue;
      font-weight:normal;
      padding: 1px;
      align: left;
   }
   table.cdr th 
   {
      font-size: 10pt;
      font-family:'Arial';
      color:white;
      font-weight:bold;
      background-color: blue;
      align: center;
      valign: top;
   }
   h2 { font-size: 12pt; font-family:Arial; color:black; font-weight:bold}
  </style>
  
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <div align = 'center'>
   <h2>%s<br>%s</h2>
   </div>
   <TABLE class="cdr">
   <COL WIDTH = "8%%">
   <COL WIDTH = "43%%">
   <COL WIDTH = "12%%">
   <COL WIDTH = "37%%">
    <TR>
     <TH>Document ID</TH>
     <TH>Organization</TH>
     <TH>Phone</TH>
     <TH>Website</TH>
    </TR>
    %s
   </TABLE>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session,section,sDate,makeOrganizationTable(organizations))
cdrcgi.sendPage(header + form)
