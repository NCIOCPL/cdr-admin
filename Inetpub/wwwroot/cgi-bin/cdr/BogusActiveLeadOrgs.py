#----------------------------------------------------------------------
#
# $Id$
#
# Report of lead orgs claiming to be active, without any active
# participating sites.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2003/03/04 22:37:23  bkline
# New report for Lakshmi on lead orgs marked active without any active
# participating sites.
#
#----------------------------------------------------------------------

import cdrdb, cdrcgi, cgi, time

debugging = 0
def logTime(start, finish, what):
    if debugging:
        file = open("d:/cdr/log/debug.log", "a")
        if file:
            file.write("BogusActiveLeadOrgs: %s took %f seconds.\n" %
                       (what, finish - start))
            file.close();
    
try:
    # Connect to the database.
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

try:
    start = time.time()
    # Create some temporary tables.
    cursor.execute("""\
        CREATE TABLE #activeppsites(id INTEGER, node_loc CHAR(8))""")
    conn.commit()
    cursor.execute("""\
        CREATE TABLE #activeorgsites(id INTEGER, node_loc CHAR(8))""")
    conn.commit()
    cursor.execute("""\
        CREATE TABLE #activeleadorgs(id INTEGER, node_loc CHAR(8))""")
    conn.commit()
    cursor.execute("""\
        CREATE TABLE #activeleadorgs_not(id INTEGER, node_loc CHAR(8))""")
    conn.commit()
    logTime(start, time.time(), "Creating temporary tables")
except cdrdb.Error, info:
    cdrcgi.bail('Failure creating temporary tables: %s' % info[1][0])


# Populate the tables.
ppStatus = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg' \
           '/ProtocolSites/PrivatePracticeSite/PrivatePracticeSiteStatus'
orgStat  = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg' \
           '/ProtocolSites/OrgSite/OrgSiteStatus'
loStat   = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg' \
           '/LeadOrgProtocolStatuses/CurrentOrgStatus/StatusName'

try:
    start = time.time()
    cursor.execute("""\
        INSERT INTO #activeppsites (id, node_loc)
    SELECT DISTINCT doc_id, LEFT(node_loc, 8)
               FROM query_term
              WHERE path = '%s'
                AND value = 'Active'""" % ppStatus)
    conn.commit()
    logTime(start, time.time(), "Populating #activeppsites")
except cdrdb.Error, info:
    cdrcgi.bail('Failure populating #activeppsites: %s' % info[1][0])

try:
    start = time.time()
    cursor.execute("""\
        INSERT INTO #activeorgsites (id, node_loc)
    SELECT DISTINCT doc_id, LEFT(node_loc, 8)
               FROM query_term
              WHERE path = '%s'
                AND value = 'Active'""" % orgStat)
    conn.commit()
    logTime(start, time.time(), "Populating #activeorgsites")
except cdrdb.Error, info:
    cdrcgi.bail('Failure populating #activeorgsites: %s' % info[1][0])

try:
    start = time.time()
    cursor.execute("""\
        INSERT INTO #activeleadorgs (id, node_loc)
    SELECT DISTINCT s.doc_id, LEFT(s.node_loc, 8)
               FROM query_term s
               JOIN doc_version v
                 ON v.id = s.doc_id
              WHERE s.path = '%s'
                AND s.value = 'Active'
                AND v.publishable = 'Y'""" % loStat)
    conn.commit()
    logTime(start, time.time(), "Populating #activeleadorgs")
except cdrdb.Error, info:
    cdrcgi.bail('Failure populating #activeleadorgs: %s' % info[1][0])


try:
    # This step finds the bogus active lead orgs.
    start = time.time()
    cursor.execute("""
        INSERT INTO #activeleadorgs_not(id, node_loc)
    SELECT DISTINCT a.id, a.node_loc
               FROM #activeleadorgs a
              WHERE NOT EXISTS (SELECT *
                                  FROM #activeppsites p
                                 WHERE p.id = a.id
                                   AND p.node_loc = a.node_loc)
                AND NOT EXISTS (SELECT *
                                  FROM #activeorgsites o
                                 WHERE o.id = a.id
                                   AND o.node_loc = a.node_loc)""")
    conn.commit()
    logTime(start, time.time(), "Populating #activeleadorgs_not")
except cdrdb.Error, info:
    cdrcgi.bail('Failure populating #activeleadorgs_not: %s' % info[1][0])

#cursor.execute("SELECT count(*) from #activeleadorgs")
#cdrcgi.bail("count of #activeleadorgs: %d" % cursor.fetchone()[0])

# Collect the information to display in the report.
orgIdPath   = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg' \
              '/LeadOrganizationID/@cdr:ref'
orgNamePath = '/Organization/OrganizationNameInformation/OfficialName/Name'

try:
    start = time.time()
    cursor.execute("""\
        SELECT DISTINCT n.id, org.int_val, name.value
                   FROM #activeleadorgs_not n
                   JOIN query_term org
                     ON n.id = org.doc_id
                   JOIN query_term name
                     ON name.doc_id = org.int_val
                  WHERE org.path = '%s'
                    AND LEFT(org.node_loc, 8) = n.node_loc
                    AND name.path = '%s'
               ORDER BY n.id, org.int_val""" % (orgIdPath, orgNamePath))
    logTime(start, time.time(), "Selecting report rows")
except cdrdb.Error, info:
    cdrcgi.bail('Failure selecting report rows: %s' % info[1][0])

# Display the report.
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Protocols with Active Lead Orgs But No Active Sites</title>
  <style type='text/css'>
   h1         { font-family: serif; font-size: 16pt; color: black; }
   th         { font-family: Arial; font-size: 12pt; }
   td         { font-family: Arial; font-size: 11pt; }
  </style>
 </head>
 <body>
  <h1>Protocols with Active Lead Orgs But No Active Sites</h1>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th nowrap='1'>Protocol ID</th>
    <th nowrap='1'>Lead Org ID</th>
    <th nowrap='1'>Lead Org Name</th>
   </tr>
"""

try:
    row = cursor.fetchone()
    while row:
        html += """\
   <tr>
    <td valign='top'>CDR%010d</td>
    <td valign='top'>CDR%010d</td>
    <td>%s</td>
   </tr>
""" % (row[0], row[1], cgi.escape(row[2]))
        row = cursor.fetchone()
except cdrdb.Error, info:
    cdrcgi.bail('Failure fetching report rows: %s' % info[1][0])

cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>""")
