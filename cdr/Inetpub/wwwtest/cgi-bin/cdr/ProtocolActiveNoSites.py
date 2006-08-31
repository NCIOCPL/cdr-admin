#----------------------------------------------------------------------
#
# $Id: ProtocolActiveNoSites.py,v 1.1 2006-08-31 21:59:56 venglisc Exp $
#
# Report of active Protocols without any active participating sites
# or external sites. (Bug 2379)
#
# $Log: not supported by cvs2svn $
#
#----------------------------------------------------------------------
import cdrdb, cdrcgi, cgi, time

debugging = 0
def logTime(start, finish, what):
    if debugging:
        file = open("d:/cdr/log/debug.log", "a")
        if file:
            file.write("ProtocolActiveNoSites: %s took %f seconds.\n" %
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
        CREATE TABLE #activeprotocol(id INTEGER)""")
    conn.commit()
    cursor.execute("""\
        CREATE TABLE #apwithsite(id INTEGER)""")
    conn.commit()
    cursor.execute("""\
        CREATE TABLE #apwithpriv(id INTEGER)""")
    conn.commit()
    cursor.execute("""\
        CREATE TABLE #apexternal(id INTEGER)""")
    conn.commit()
    cursor.execute("""\
        CREATE TABLE #activeprotocol_not(id INTEGER)""")
    conn.commit()
    logTime(start, time.time(), "Creating temporary tables")
except cdrdb.Error, info:
    cdrcgi.bail('Failure creating temporary tables: %s' % info[1][0])


# Populate the tables.
# ---------------------
curStatus = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
orgStatus = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg' \
            '/ProtocolSites/OrgSite/OrgSiteStatus'
ppStatus  = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg' \
            '/ProtocolSites/PrivatePracticeSite/PrivatePracticeSiteStatus'
extSite   = '/InScopeProtocol/ProtocolAdminInfo/ExternalSites/ExternalSite/%%'
protId    = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'

try:
    start = time.time()
    # Populate temp table listing all active protocols
    # ------------------------------------------------
    cursor.execute("""\
        INSERT INTO #activeprotocol
        SELECT DISTINCT doc_id
          FROM query_term q
          JOIN document d
            ON d.id = q.doc_id
         WHERE q.path  = '%s'
           AND q.value = 'Active'
           AND d.active_status = 'A'
           AND d.val_status    = 'V'""" % curStatus)
    conn.commit()
    logTime(start, time.time(), "Populating #activeprotocol")
except cdrdb.Error, info:
    cdrcgi.bail('Failure populating #activeprotocol: %s' % info[1][0])

try:
    start = time.time()
    # Populate temp table listing all active protocols with
    # active organizations
    # ----------------------------------------------------
    cursor.execute("""\
        INSERT INTO #apwithsite
        SELECT DISTINCT p.doc_id
          FROM query_term p
          JOIN #activeprotocol a
            ON a.id = p.doc_id
         WHERE p.path  = '%s'
           AND p.value = 'Active'""" % orgStatus)
    conn.commit()
    logTime(start, time.time(), "Populating #apwithsite")
except cdrdb.Error, info:
    cdrcgi.bail('Failure populating #apwithsite: %s' % info[1][0])

try:
    start = time.time()
    # Populate temp table listing all active protocols with 
    # private practice locations
    # ------------------------------------------------------
    cursor.execute("""\
        INSERT INTO #apwithpriv
        SELECT DISTINCT q.doc_id
          FROM query_term q
          JOIN #activeprotocol a
            ON a.id = q.doc_id
         WHERE q.path  = '%s'
           AND q.value = 'Active'""" % ppStatus)
    conn.commit()
    logTime(start, time.time(), "Populating #apwithpriv")
except cdrdb.Error, info:
    cdrcgi.bail('Failure populating #apwithpriv: %s' % info[1][0])


try:
    start = time.time()
    # Populate temp table listing all active protocols with 
    # external sites
    # ------------------------------------------------------
    cursor.execute("""\
        INSERT INTO #apexternal
        SELECT DISTINCT q.doc_id
          FROM query_term q
          JOIN #activeprotocol a
            ON a.id = q.doc_id
         WHERE q.path  like '%s'""" % extSite)
    conn.commit()
    logTime(start, time.time(), "Populating #apexternal")
except cdrdb.Error, info:
    cdrcgi.bail('Failure populating #apexternal: %s' % info[1][0])


try:
    # This step finds the bogus active protocols.
    # (active protocols w/o site, external site, or priv. practice location)
    # ----------------------------------------------------------------------
    start = time.time()
    cursor.execute("""
        INSERT INTO #activeprotocol_not(id)
        SELECT id 
          FROM #activeprotocol p
         WHERE NOT EXISTS (SELECT * 
                           FROM #apwithsite o
                           WHERE o.id = p.id)
           AND NOT EXISTS (SELECT * 
                           FROM #apexternal e
                           WHERE e.id = p.id)
           AND NOT EXISTS (SELECT * 
                           FROM #apwithpriv g
                           WHERE g.id = p.id)""")
    conn.commit()
    logTime(start, time.time(), "Populating #activeprotocol_not")
except cdrdb.Error, info:
    cdrcgi.bail('Failure populating #activeprotocol_not: %s' % info[1][0])

# Collect the information to display in the report.
# -------------------------------------------------
try:
    start = time.time()
    cursor.execute("""\
        SELECT DISTINCT n.id, q.value
                   FROM #activeprotocol_not n
                   JOIN query_term q
                     ON q.doc_id = n.id
                  WHERE q.path = '%s'
               ORDER BY n.id""" % protId)
    logTime(start, time.time(), "Selecting report rows")
except cdrdb.Error, info:
    cdrcgi.bail('Failure selecting report rows: %s' % info[1][0])

# Display the report.
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Protocols (Active) But No Active Sites</title>
  <style type='text/css'>
   h1         { font-family: serif; font-size: 16pt; color: black; }
   th         { font-family: Arial; font-size: 12pt; }
   td         { font-family: Arial; font-size: 11pt; }
  </style>
 </head>
 <body>
  <h1>Protocols (Active) But No Active Sites</h1>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th nowrap='1'>DocID</th>
    <th nowrap='1'>Primary Protocol ID</th>
   </tr>
"""

try:
    row = cursor.fetchone()
    while row:
        html += """\
   <tr>
    <td valign='top'>CDR%010d</td>
    <td valign='top'>%s</td>
   </tr>
""" % (row[0], row[1])
        row = cursor.fetchone()
except cdrdb.Error, info:
    cdrcgi.bail('Failure fetching report rows: %s' % info[1][0])

cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>""")
