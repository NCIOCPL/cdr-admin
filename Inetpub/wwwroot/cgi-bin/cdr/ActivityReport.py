#----------------------------------------------------------------------
# Reports on audit trail content.
# BZIssue::1283 - add support for searching by user
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
user     = fields and fields.getvalue('User')     or None
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "ActivityReport.py"
title   = "CDR Administration"
section = "Document Activity Report"
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
# Validate some user input
#----------------------------------------------------------------------
# cgi.escape of dates will not be required after this validation
if fromDate:
    if not cdr.strptime(fromDate, '%Y-%m-%d'):
        cdrcgi.bail('Start Date must be valid date in YYYY-MM-DD format')
if toDate:
    if not cdr.strptime(toDate, '%Y-%m-%d'):
        cdrcgi.bail('End Date must be valid date in YYYY-MM-DD format')
if docType:
    if docType not in cdr.getDoctypes(session):
        cdrcgi.bail('Unknown doc type requested: "%s"' % cgi.escape(docType))

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
    form = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <TABLE BORDER='0'>
    <TR>
     <TD><B>User:&nbsp;</B></TD>
     <TD><INPUT NAME='User' VALUE=''>&nbsp;</TD>
    </TR>
    <TR>
     <TD><B>Document Type:&nbsp;</B></TD>
     <TD>
      <SELECT NAME='DocType'>
      <OPTION VALUE='' SELECTED>All Types</OPTION>
""" % (cdrcgi.SESSION, session)
    for docType in docTypes:
        form += """\
      <OPTION VALUE='%s'>%s &nbsp;</OPTION>
""" % (docType, docType)
    form += """\
    </TR>
    <TR>
     <TD><B>Start Date:&nbsp;</B></TD>
     <TD><INPUT NAME='FromDate' VALUE='%s'>&nbsp;
         (use format YYYY-MM-DD for dates, e.g. %s)</TD>
    </TR>
    <TR>
     <TD><B>End Date:&nbsp;</B></TD>
     <TD><INPUT NAME='ToDate' VALUE='%s'>&nbsp;</TD>
    </TR>
   </TABLE>
  </FORM>
 </BODY>
</HTML>
""" % (fromDate, cdrcgi.DAY_ONE, toDate)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Start the page.
#----------------------------------------------------------------------
headerDocType = docType and ("%s Documents" % docType) or "All Document Types"
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Document Activity Report %s -- %s</title>
  <style type 'text/css'>
   body    { font-family: Arial, Helvetica, sans-serif }
   span.ti { font-size: 14pt; font-weight: bold }
   th      { text-align: center; vertical-align: top;
             font-size: 12pt; font-weight: bold }
   td      { text-align: left; vertical-align: top;
             font-size: 12pt; font-weight: normal }
  </style>
 </head>
 <basefont face='Arial, Helvetica, sans-serif'>
 <body>
  <center>
   <span class='ti'>CDR Document Activity</span>
   <br />
   <span class='ti'>From %s to %s</span>
  </center>
  <br />
  <br />
  <table border='1' cellspacing='0' cellpadding='2'>
   <tr>
    <th>Who</th>
    <th>When</th>
    <th>Action</th>
    <th>DocType</th>
    <th>DocID</th>
    <th>DocTitle</th>
    <th>Comment</th>
   </tr>
""" % (headerDocType, time.strftime("%m/%d/%Y", now), fromDate, toDate)

#----------------------------------------------------------------------
# Extract the information from the database.
#----------------------------------------------------------------------
if fromDate < cdrcgi.DAY_ONE: fromDate = cdrcgi.DAY_ONE
try:
    # Create array of question mark parameter value substitutions
    # Avoids SQL injection vulnerability found by AppScan on previous version
    qmarkVals = [fromDate, toDate]
    userQual  = ""
    if user:
        userQual = "AND u.name = ?"
        qmarkVals.append(user)
    dtQual = ""
    if docType:
        dtQual = "AND t.name = ?"
        qmarkVals.append(docType)

    # Execute dynamically built query
    conn     = cdrdb.connect()
    cursor   = conn.cursor()
    cursor.execute("""\
         SELECT a.document,
                u.name,
                u.fullname,
                a.dt,
                t.name,
                act.name,
                d.title,
                a.comment
           FROM audit_trail a
           JOIN usr u
             ON u.id = a.usr
           JOIN all_docs d
             ON d.id = a.document
           JOIN doc_type t
             ON t.id = d.doc_type
           JOIN action act
             ON act.id = a.action
          WHERE a.dt BETWEEN ? AND DATEADD(s, -1, DATEADD(d, 1, ?))
            %s
            %s
        ORDER BY a.dt DESC""" % (userQual, dtQual), qmarkVals, timeout = 120)

    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdr.logwrite('DB Failure: info=%s' % info)
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

for row in rows:
    html += """\
   <tr>
    <td nowrap='1'>%s (%s)</td>
    <td nowrap='1'>%s</td>
    <td nowrap='1'>%s</td>
    <td nowrap='1'>%s</td>
    <td nowrap='1'>
     <a href='%s/QcReport.py?DocId=CDR%010d&%s=%s'>CDR%010d</a>
    </td>
    <td nowrap='1'>%s ...</td>
    <td>%s</td>
   </tr>
""" % (row[2], row[1], row[3], row[5], row[4],
       cdrcgi.BASE, row[0], cdrcgi.SESSION, session, row[0],
       cdrcgi.unicodeToLatin1(row[6][:20]),
       row[7] and cdrcgi.unicodeToLatin1(row[7]) or "&nbsp;")

# Converting html since sendPage() expects a unicode string.
# ----------------------------------------------------------
html = html.decode('utf-8')
cdrcgi.sendPage(html + u"""\
  </table>
 </body>
</html>
""")
