#----------------------------------------------------------------------
#
# $Id$
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi

fields   = cgi.FieldStorage() or cdrcgi.bail("No Request Found", repTitle)
session  = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")

# -------------------------------------------------------------
# Function to select all persons linked to a given organization
# -------------------------------------------------------------
def getPersons(id, session):
    try:
        query = """\
            SELECT * 
              FROM #t2
             WHERE orgid = %d
             ORDER BY persname""" % id
        cursor.execute(query, timeout = 300)
    except cdrdb.Error, info:
        cdrcgi.bail('Database failure selecting from table #t2: %s' % info[1][0])

    rows = cursor.fetchall()

    names = ''
    for row in rows:
        names += """\
                 %s (<a href="/cgi-bin/cdr/QcReport.py?%s=%s&amp;DocId=%d">%d</a>)
                 <br/>""" % (row[1], cdrcgi.SESSION, session, row[0], row[0])

    return(names)


# *******************************************************************
# Main
# *******************************************************************
conn = cdrdb.connect('CdrGuest')
conn.setAutoCommit()  
cursor = conn.cursor()
 
# Create and populate table of all organizations linked to a AdHoc group
# ----------------------------------------------------------------------
try:
    cursor.execute("""\
        CREATE TABLE #t1 (orgid   INTEGER       NOT NULL,
                          orgname VARCHAR(800)  NOT NULL,
                          ahid    INTEGER       NOT NULL,
                          ahname  VARCHAR(800)  NOT NULL)
""", timeout = 300)
except cdrdb.Error, info:
    cdrcgi.bail('Database failure creating table #t1: %s' % info[1][0])

try:
    cursor.execute("""\
        insert into #t1    
        SELECT q.doc_id, n.value, q.int_val, a.value
          FROM query_term q
          JOIN query_term n
            ON n.doc_id = q.doc_id
           AND n.path   = '/Organization/OrganizationNameInformation/'
                        + 'OfficialName/Name'
          JOIN query_term a
            ON a.doc_id = q.int_val
           AND a.path   = '/Organization/OrganizationNameInformation/'
                        + 'OfficialName/Name'
          JOIN document d
            ON d.id = q.doc_id
          JOIN query_term s
            ON s.doc_id = q.doc_id
           AND s.path   = '/Organization/Status/CurrentStatus'
           AND s.value  = 'Active'
         WHERE q.path   = '/Organization/OrganizationAffiliations/'
                        + 'MemberOfAdHocGroup/@cdr:ref'
           AND d.active_status = 'A'
         ORDER BY a.value, n.value
""", timeout = 300)
except cdrdb.Error, info:
    cdrcgi.bail('Database failure populating table #t1: %s' % info[1][0])

# Create and populate table of all persons linked to the organizations 
# ----------------------------------------------------------------------
try:
    cursor.execute("""\
        CREATE TABLE #t2 (persid   INTEGER       NOT NULL,
                          persname VARCHAR(800)  NOT NULL,
                          role     VARCHAR(80)   NOT NULL,
                          orgid    INTEGER       NOT NULL)
""", timeout = 300)
except cdrdb.Error, info:
    cdrcgi.bail('Database failure creating table #t2: %s' % info[1][0])

try:
    cursor.execute("""\
        INSERT into #t2    
        SELECT DISTINCT s.doc_id, s.value + ', ' + g.value + ' ' + m.value,
               r.value, o.int_val
          FROM query_term s
          JOIN query_term g
            ON g.doc_id  = s.doc_id
           AND g.path    = '/Person/PersonNameInformation/GivenName'
          JOIN query_term m
            ON m.doc_id  = s.doc_id
           AND m.path    = '/Person/PersonNameInformation/MiddleInitial'
          JOIN query_term r
            ON r.doc_id  = s.doc_id
           AND r.path    = '/Person/PersonLocations/OtherPracticeLocation/'
                         + 'ComplexAffiliation/RoleAtAffiliatedOrganization'
          JOIN query_term o
            ON o.doc_id  = s.doc_id
           AND o.path    = '/Person/PersonLocations/OtherPracticeLocation/'
                         + 'OrganizationLocation/@cdr:ref'
           AND left(o.node_loc, 8) = left(r.node_loc, 8)
          JOIN #t1 t1
            ON o.int_val = t1.orgid
          JOIN document d
            ON d.id      = s.doc_id
          JOIN query_term z
            ON z.doc_id  = s.doc_id
           AND z.path    = '/Person/Status/CurrentStatus'
           AND z.value   = 'Active'
         WHERE s.path    = '/Person/PersonNameInformation/SurName'
           AND d.active_status = 'A'
""", timeout = 300)
except cdrdb.Error, info:
    cdrcgi.bail('Database failure populating table #t2: %s' % info[1][0])

orgs = {}
preferredOrgs = {}

# Select the organizations
# ---------------------------
try:
    cursor.execute("""\
        SELECT *
          FROM #t1""")
except cdrdb.Error, info:
    cdrcgi.bail('Database failure during select from table #t1: %s' % info[1][0])

rows = cursor.fetchall()
    
table = """\
"""
lastorg = ''
for row in rows:
    # Begin a new table with each new AdHoc Group
    # -------------------------------------------
    if lastorg != row[3]:
        table += """\
  </table>
  <p/>
  <table width='100%%' border='1' cellspacing='0' cellpadding='2'>
   <tr class="header">
    <th width='35%%'>AdHoc Organization</th>
    <th width='35%%'>Organization</th>
    <th>Person</th> 
   </tr>
  """

    # Suppress printing the AdHoc Group multiple times within a table
    # ---------------------------------------------------------------
    if lastorg != row[3]:
        table += """\
   <tr>
    <td valign="top">%s 
     (<a href="/cgi-bin/cdr/QcReport.py?%s=%s&amp;DocId=%d">%d</a>)
    </td>
    <td valign="top">%s 
     (<a href="/cgi-bin/cdr/QcReport.py?%s=%s&amp;DocId=%d">%d</a>)
    </td>
    <td valign="top">%s</td>
   </tr>
""" % (row[3], cdrcgi.SESSION, session, row[2], row[2], 
       row[1], cdrcgi.SESSION, session, row[0], row[0], 
       getPersons(row[0], session))
    else:
        table += """\
   <tr>
    <td valign="top">%s </td>
    <td valign="top">%s 
     (<a href="/cgi-bin/cdr/QcReport.py?%s=%s&amp;DocId=%d">%d</a>)
    </td>
    <td valign="top">%s</td>
   </tr>
""" % ('&nbsp;' , 
       row[1], cdrcgi.SESSION, session, row[0], row[0], 
       getPersons(row[0], session))
    lastorg = row[3]

table += """\
  </table>
"""
html = """\
<html>
 <head>
  <title>Member of AdHoc Group Organization Report</title>
  <style type='text/css'>
   body      { font-family: Arial; }
   tr.header { background-color: #CCFFFF; }
  </style>
 </head>
 <body>
  <h3>Member of AdHoc Group Organization Report</h3>
  %s
 </body>
</html>""" % table
cdrcgi.sendPage(html)
