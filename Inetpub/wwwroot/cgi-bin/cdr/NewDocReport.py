#----------------------------------------------------------------------
# Reports on newly created documents and their statuses.
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
fromDate = fields and fields.getvalue('FromDate') or None
toDate   = fields and fields.getvalue('ToDate')   or None
docType  = fields and fields.getvalue('DocType')  or None
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "NewDocReport.py"
title   = "CDR Administration"
section = "New Documents Report"
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
# If we don't have a request, put up the request form.
#----------------------------------------------------------------------
if not fromDate or not toDate:
    toDate   = time.strftime("%Y-%m-%d", now)
    then     = list(now)
    then[1] -= 1
    then[2] += 1
    then     = time.localtime(time.mktime(then))
    fromDate = time.strftime("%Y-%m-%d", then)
    docTypes = cdr.getDoctypes(session)
    if type(docTypes) in [type(""), type(u"")]:
        cdrcgi.bail(docTypes)
    form = u"""\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <TABLE BORDER='0'>
    <TR>
     <TD><B>Document Type:&nbsp;</B></TD>
     <TD>
      <SELECT NAME='DocType'>
      <OPTION VALUE='' SELECTED>All Types</OPTION>
""" % (cdrcgi.SESSION, session)
    for docType in docTypes:
        form += u"""\
      <OPTION VALUE='%s'>%s &nbsp;</OPTION>
""" % (docType, docType)
    form += u"""\
    </TR>
    <TR>
     <TD><B>Start Date:&nbsp;</B></TD>
     <TD><INPUT NAME='FromDate' VALUE='%s'>&nbsp;
         (use format YYYY-MM-DD for dates, e.g. 2002-01-01)</TD>
    </TR>
    <TR>
     <TD><B>End Date:&nbsp;</B></TD>
     <TD><INPUT NAME='ToDate' VALUE='%s'>&nbsp;</TD>
    </TR>
   </TABLE>
  </FORM>
 </BODY>
</HTML>
""" % (fromDate, toDate)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Validate inputs
#----------------------------------------------------------------------
fromDate = fromDate.strip()
toDate   = toDate.strip()
if not cdr.valFromToDates('%Y-%m-%d', fromDate, toDate):
    cdrcgi.bail(
      "Invalid Start or End date.  Use YYYY-MM-DD, Start no later than End.")

if docType and docType not in cdr.getDoctypes(session):
    cdrcgi.bail('Unknown doc type requested: "%s"' % cgi.escape(docType))

#----------------------------------------------------------------------
# We have a request; do it.
#----------------------------------------------------------------------
headerDocType = docType and ("%s Documents" % docType) or "All Document Types"
statuses      = ["Published",
                 "Ready for Publication",
                 "Ready for Review",
                 "Valid",
                 "Unvalidated",
                 "Invalid",
                 "Malformed"]

#----------------------------------------------------------------------
# Start the page.
#----------------------------------------------------------------------
html = u"""\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>New Document Report %s %s</title>
 </head>
 <basefont face='Arial, Helvetica, sans-serif'>
 <body>
  <center>
   <b>
    <font size='4'>New Documents Created In CDR</font>
   </b>
   <br />
   <b>
    <font size='4'>From %s to %s</font>
   </b>
  </center>
  <br />
  <br />
  <table border='1' cellspacing='0' cellpadding='2' width='100%%'>
   <tr>
    <td nowrap='1' align='center'>
     <b>
      <font size='3'>Document Type</font>
     </b>
    </td>
    <td align='center'>
     <b>
      <font size='3'>Status</font>
     </b>
    </td>
    <td align='center'>
     <b>
      <font size='3'>Count</font>
     </b>
    </td>
   </tr>
""" % (headerDocType, time.strftime("%m/%d/%Y", now), fromDate, toDate)

#----------------------------------------------------------------------
# Extract the information from the database.
#----------------------------------------------------------------------
docCounts = {}
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
    # Security note: docType already checked for whitelist, data i safe
    dtQual = docType and ("AND t.name = '%s'" % docType) or ""
    cursor.execute("""\
    SELECT t.name,
           dstat = CASE
                        WHEN EXISTS (SELECT *
                                       FROM pub_proc_doc ppd
                                       JOIN pub_proc pp
                                         ON pp.id = ppd.pub_proc
                                      WHERE ppd.doc_id    = d.id
                                        AND pp.pub_subset = 'Cancer.gov'
                                        AND pp.status     = 'success')
                             THEN 0
                        WHEN d.active_status = 'A'
                         AND EXISTS (SELECT *
                                       FROM doc_version v
                                      WHERE v.id = d.id
                                        AND v.publishable = 'Y'
                                        AND v.val_status  = 'V')
                             THEN 1
                        WHEN EXISTS (SELECT *
                                       FROM ready_for_review rr
                                      WHERE rr.doc_id = d.id)
                             THEN 2
                        ELSE
                             CASE d.val_status
                                  WHEN 'V' THEN 3
                                  WHEN 'U' THEN 4
                                  WHEN 'I' THEN 5
                                  WHEN 'M' THEN 6
                                  ELSE          4
                             END
                    END
      INTO #doc_statuses
      FROM document d
      JOIN doc_type t
        ON t.id = d.doc_type
     WHERE (SELECT MIN(a.dt)
              FROM audit_trail a
             WHERE a.document = d.id) BETWEEN '%s'
                                          AND DATEADD(s, -1,
                                                      DATEADD(d, 1, '%s'))
      %s
""" % (fromDate, toDate, dtQual), timeout = 120)
    cursor.execute("""\
    SELECT name, dstat, COUNT(*)
      FROM #doc_statuses
  GROUP BY name, dstat
  ORDER BY name, dstat""")
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

for row in rows:
    if not docCounts.has_key(row[0]):
        docCounts[row[0]] = [0, 0, 0, 0, 0, 0, 0]
    if row[1] not in range(len(statuses)):
        cdrcgi.bail('Invalid status for %s documents' % row[0])
    docCounts[row[0]][row[1]] = row[2]

keys = docCounts.keys()
keys.sort()
for key in keys:
    col1   = key
    total  = 0
    counts = docCounts[key]
    if key != keys[0]:
        html += u"""\
   <tr>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
    <td>&nbsp;</td>
   </tr>
"""
    for i in range(len(statuses)):
        html += u"""\
   <tr>
    <td nowrap='1'>
     <b>
      <font size='3'>%s</font>
     </b>
    </td>
    <td nowrap='1'>
     <font size='3'>%s</font>
    </td>
    <td align='right'>
     <font size='3'>%d</font>
    </td>
   </tr>
""" % (col1, statuses[i], counts[i])
        col1 = "&nbsp;"
        total += counts[i]

    html += u"""\
   <tr>
    <td nowrap='1'>
     <b>
      <i>
       <font size='3'>Total</font>
      </i>
     </b>
    </td>
    <td>&nbsp;</td>
    <td align='right'>
     <b>
      <font size='3'>%d</font>
     </b>
    </td>
   </tr>
""" % total
cdrcgi.sendPage(html + u"""\
  </table>
 </body>
</html>
""")
