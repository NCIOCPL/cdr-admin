#----------------------------------------------------------------------
#
# $Id$
#
# Report of Citation documents created during a specified date range.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, re, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
fromDate = fields and fields.getvalue('FromDate') or None
toDate   = fields and fields.getvalue('ToDate')   or None
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "NewCitations.py"
title   = "CDR Administration"
section = "New Citations Report"
header  = cdrcgi.header(title, title, section, script, buttons)
now     = time.localtime(time.time())
host    = 'www.ncbi.nlm.nih.gov'
cgicmd  = '/entrez/query.fcgi'
params  = '?cmd=Retrieve&db=pubmed&dopt=Abstract&list_uids=%s'
url     = 'http://%s%s%s' % (host, cgicmd, params)

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
if not fromDate or not toDate:
    toDate   = time.strftime("%Y-%m-%d", now)
    then     = list(now)
    then[2] -= 6
    then     = time.localtime(time.mktime(then))
    fromDate = time.strftime("%Y-%m-%d", then)
    docTypes = cdr.getDoctypes(session)
    if type(docTypes) in [type(""), type(u"")]:
        cdrcgi.bail(docTypes)
    if fromDate < cdrcgi.DAY_ONE: fromDate = cdrcgi.DAY_ONE
    form = u"""\
   <input type='hidden' name='%s' value='%s'>
   <table border='0'>
    </tr>
    <tr>
     <td><b>Start Date:&nbsp;</b></td>
     <td><input name='FromDate' value='%s'>&nbsp;
         (use format YYYY-MM-DD for dates, e.g. %s)</td>
    </tr>
    <tr>
     <td><b>End Date:&nbsp;</b></td>
     <td><input name='ToDate' value='%s'>&nbsp;</td>
    </tr>
   </table>
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session, fromDate, cdrcgi.DAY_ONE, toDate)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Start the page.
#----------------------------------------------------------------------
html = u"""\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>List of New Citation Documents</title>
  <style type 'text/css'>
   body    { font-family: Arial, Helvetica, sans-serif }
   span.ti { font-size: 14pt; font-weight: bold }
   th      { text-align: center; vertical-align: top; 
             font-size: 12pt; font-weight: bold }
   td      { vertical-align: top; 
             font-size: 12pt; font-weight: normal }
  </style>
 </head>
 <basefont face='Arial, Helvetica, sans-serif'>
 <body>
  <center>
   <span class='ti'>List of New Citation Documents</span>
   <br />
   <span class='ti'>%s</span>
   <br />
   <br />
   <span class='ti'>Documents Created Between: %s and %s</span>
  </center>
  <br />
  <br />
  <table border='1' cellspacing='0' cellpadding='2'>
   <tr>
    <th>CDR ID</th>
    <th>DocTitle</th>
    <th>Created By</th>
    <th>Creation Date</th>
    <th>Last Version Pub?</th>
    <th>PMID?</th>
   </tr>
""" % (time.strftime("%B %d, %Y", now), fromDate, toDate)

#----------------------------------------------------------------------
# Extract the information from the database.
#----------------------------------------------------------------------
if fromDate < cdrcgi.DAY_ONE: fromDate = cdrcgi.DAY_ONE
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
    cursor.execute("""\
        CREATE TABLE #t
                 (id INTEGER  NOT NULL,
                  dt DATETIME NOT NULL,
                 usr INTEGER  NOT NULL,
                 ver INTEGER      NULL)""")
    conn.commit()
    cursor.execute("""\
    INSERT INTO #t
         SELECT d.id,
                c.dt,
                c.usr,
                MAX(v.num)
           FROM document d
           JOIN doc_type t
             ON t.id = d.doc_type
           JOIN audit_trail c
             ON c.document = d.id
           JOIN action a
             ON a.id = c.action
LEFT OUTER JOIN doc_version v
             ON v.id = d.id
          WHERE t.name = 'Citation'
            AND c.dt BETWEEN '%s' AND DATEADD(s, -1, DATEADD(d, 1, '%s'))
            AND a.name = 'ADD DOCUMENT'
       GROUP BY d.id, c.dt, c.usr""" % (fromDate, toDate), timeout = 300)
    conn.commit()
    cursor.execute("""\
         SELECT d.id,
                d.title,
                u.name,
                t.dt,
                v.publishable,
                p.value
           FROM document d
           JOIN #t t
             ON t.id = d.id
           JOIN usr u
             ON t.usr = u.id
LEFT OUTER JOIN doc_version v
             ON v.id = d.id
            AND v.num = t.ver
LEFT OUTER JOIN query_term p
             ON p.doc_id = d.id
            AND p.path IN ('/Citation/PubmedArticle/MedlineCitation/PMID',
                           '/Citation/PubmedArticle/NCBIArticle/PMID')
       ORDER BY d.id, t.dt""",
                   timeout = 300)
    row = cursor.fetchone()
    while row:
        pub = row[4] or "N/A"
        if row[5]:
            pmid = url % row[5]
            pmid = "<a href='%s'>%s</a>" % (pmid, row[5])
        else:
            pmid = "&nbsp;"
        html += u"""\
   <tr>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td align='center'>%s</td>
    <td>%s</td>
   </tr>
""" % (row[0], cgi.escape(row[1]), row[2], row[3][:10], pub, pmid)
        row = cursor.fetchone()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])
cdrcgi.sendPage(html + u"""\
  </table>
 </body>
</html>
""")
