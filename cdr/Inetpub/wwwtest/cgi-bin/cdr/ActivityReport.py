#----------------------------------------------------------------------
#
# $Id: ActivityReport.py,v 1.2 2002-06-26 20:04:14 bkline Exp $
#
# Reports on audit trail content.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2002/06/26 16:35:16  bkline
# Implmented report of audit_trail activity.
#
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
docType  = fields and fields.getvalue('DocType')  or None
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
    if fromDate < '2002-06-24': fromDate = '2002-06-24'
    form = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <TABLE BORDER='0'>
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
# Start the page.
#----------------------------------------------------------------------
headerDocType = docType and ("%s Documents" % docType) or "All Document Types"
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Document Activity Report %s %s</title>
 </head>
 <basefont face='Arial, Helvetica, sans-serif'>
 <body>
  <center>
   <b>
    <font size='4'>CDR Document Activity</font>
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
      <font size='3'>Who</font>
     </b>
    </td>
    <td nowrap='1' align='center'>
     <b>
      <font size='3'>When</font>
     </b>
    </td>
    <td nowrap='1' align='center'>
     <b>
      <font size='3'>Action</font>
     </b>
    </td>
    <td nowrap='1' align='center'>
     <b>
      <font size='3'>DocType</font>
     </b>
    </td>
    <td nowrap='1' align='center'>
     <b>
      <font size='3'>DocID</font>
     </b>
    </td>
    <td nowrap='1' align='center'>
     <b>
      <font size='3'>DocTitle</font>
     </b>
    </td>
   </tr>
""" % (headerDocType, time.strftime("%m/%d/%Y", now), fromDate, toDate)
   
#----------------------------------------------------------------------
# Extract the information from the database.
#----------------------------------------------------------------------
if fromDate < '2002-06-24': fromDate = '2002-06-24'
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
    dtQual = docType and ("AND t.name = '%s'" % docType) or ""
    cursor.execute("""\
         SELECT a.document,
                u.name,
                u.fullname,
                a.dt,
                t.name,
                act.name,
                d.title
           FROM audit_trail a
           JOIN usr u
             ON u.id = a.usr
           JOIN document d
             ON d.id = a.document
           JOIN doc_type t
             ON t.id = d.doc_type
           JOIN action act
             ON act.id = a.action
          WHERE a.dt BETWEEN '%s' AND DATEADD(s, -1, DATEADD(d, 1, '%s'))
            %s
        ORDER BY a.dt DESC""" % (fromDate, toDate, dtQual), timeout = 120)

    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

for row in rows:
    html += """\
   <tr>
    <td nowrap='1'>
     <font size='3'>%s (%s)</font>
    </td>
    <td nowrap='1'>
     <font size='3'>%s</font>
    </td>
    <td nowrap='1'>
     <font size='3'>%s</font>
    </td>
    <td nowrap='1'>
     <font size='3'>%s</font>
    </td>
    <td nowrap='1'>
     <font size='3'>
      <a href='%s/QcReport.py?DocId=CDR%010d&%s=%s'>CDR%010d</a>
     </font>
    </td>
    <td nowrap='1'>
     <font size='3'>%s ...</font>
    </td>
   </tr>
""" % (row[2], row[1], row[3], row[5], row[4], 
       cdrcgi.BASE, row[0], cdrcgi.SESSION, session, row[0],
       cdrcgi.unicodeToLatin1(row[6][:20]))

cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>
""")
