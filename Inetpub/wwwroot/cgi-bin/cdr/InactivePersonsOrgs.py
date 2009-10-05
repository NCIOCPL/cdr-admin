#----------------------------------------------------------------------
#
# $Id: InactivePersonsOrgs.py,v 1.2 2007-11-03 14:15:07 bkline Exp $
#
# Report on inactive persons and organizations linked to protocols.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2002/07/16 15:39:36  bkline
# New report on inactive persons and orgs.
#
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, re, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "InactivePersonsOrgs.py"
title   = "CDR Administration"
section = "Inactive Persons and Organizations linked to Protocols"
header  = cdrcgi.header(title, title, section, script, buttons)
now     = time.localtime(time.time())

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
# Start the page.
#----------------------------------------------------------------------
html = u"""\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Inactive Persons/Organizations Linked to Protocols -- %s</title>
  <style type 'text/css'>
   body    { font-family: Arial, Helvetica, sans-serif }
   span.t1 { font-size: 14pt; font-weight: bold }
   span.t2 { font-size: 12pt; font-weight: bold }
   th      { text-align: center; vertical-align: top; 
             font-size: 12pt; font-weight: bold }
   td      { text-align: left; vertical-align: top; 
             font-size: 12pt; font-weight: normal }
  </style>
 </head>
 <body>
  <center>
   <span class='t1'>Inactive Persons/Organizations Linked to Protocols</span>
   <br />
   <span class='t2'>(For Active, Approved, Temporarily Closed Only)</span>
   <br />
   <span class='t2'>%s</span>
   <br />
   <br />
  </center>
""" % (time.strftime("%m/%d/%Y"), time.strftime("%B %d, %Y", now))
   
#----------------------------------------------------------------------
# Extract the inactive persons and organizations from the database.
#----------------------------------------------------------------------
perLinkPaths = ('/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                '/LeadOrgPersonnel/Person/@cdr:ref',
                '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                '/ProtocolSites/PrivatePracticeSite'
                '/PrivatePracticeSiteID/@cdr:ref',
                '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'
                '/ProtocolSites/OrgSite/OrgSiteContact/SpecificPerson'
                '/Person/@cdr:ref')
orgLinkPath  = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg' \
               '/ProtocolSites/OrgSite/OrgSiteID/@cdr:ref'
protStatPath = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
    cursor.execute("""\
SELECT DISTINCT person.id,
                person.title,
                protocol.id,
                protocol.title
           FROM document person
           JOIN query_term person_stat
             ON person_stat.doc_id = person.id
            AND person_stat.path = '/Person/Status/CurrentStatus'
            AND person_stat.value = 'Inactive'
           JOIN query_term person_link
             ON person_link.int_val = person.id
            AND person_link.path IN ('%s', '%s', '%s')
           JOIN document protocol
             ON protocol.id = person_link.doc_id
           JOIN query_term prot_stat
             ON prot_stat.doc_id = protocol.id
            AND prot_stat.path = '%s'
            AND prot_stat.value IN ('Active',
                                    'Approved-not yet active',
                                    'Temporarily Closed')
       ORDER BY person.id, protocol.title""" % (perLinkPaths[0],
                                                perLinkPaths[1],
                                                perLinkPaths[2],
                                                protStatPath), timeout = 120)

    personRows = cursor.fetchall()
    cursor.execute("""\
SELECT DISTINCT organization.id,
                organization.title,
                protocol.id,
                protocol.title
           FROM document organization
           JOIN query_term org_stat
             ON org_stat.doc_id = organization.id
            AND org_stat.path = '/Organization/Status/CurrentStatus'
            AND org_stat.value = 'Inactive'
           JOIN query_term org_link
             ON org_link.int_val = organization.id
            AND org_link.path = '%s'
           JOIN document protocol
             ON protocol.id = org_link.doc_id
           JOIN query_term prot_stat
             ON prot_stat.doc_id = protocol.id
            AND prot_stat.path = '%s'
            AND prot_stat.value IN ('Active',
                                 'Approved-not yet active',
                                 'Temporarily Closed')
       ORDER BY organization.id, protocol.title""" % (orgLinkPath, 
                                                      protStatPath), 
                                                      timeout = 120)
    orgRows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Make sure we have some documents to report on.
#----------------------------------------------------------------------
if not orgRows and not personRows:
    cdrcgi.sendPage(html + u"""\
  <span class='t2'>No documents found to report.</span>
 </body>
</html>
""")

#----------------------------------------------------------------------
# Common code for generating a table for inactive persons or organizations.
#----------------------------------------------------------------------
def showTable(title, rows):
    html = u"""\
  <span class='t2'>%s</span>
  <br />
  <br />
  <table border='1' cellspacing='0' cellpadding='2' width='100%%'>
   <tr>
    <th>CDR DOCID</th>
    <th>DOCTITLE</th>
    <th>PROTOCOL DOCID</th>
    <th>LEAD ORG PROTOCOL ID</th>
   </tr>
""" % title
    for row in rows:
        semicolon = row[3].find(';')
        if semicolon == -1: protId = row[3]
        else:               protId = row[3][:semicolon]
        html += u"""\
   <tr>
    <td>CDR%010d</td>
    <td>%s</td>
    <td>CDR%010d</td>
    <td>%s</td>
   </tr>
""" % (row[0], row[1], row[2], protId)
    return html + u"""\
  </table>
  <br />
  <br />
"""

if personRows:
    html += showTable("PERSONS", personRows)
if orgRows:
    html += showTable("ORGANIZATIONS", orgRows)

cdrcgi.sendPage(html + u"""\
 </body>
</html>
""")
