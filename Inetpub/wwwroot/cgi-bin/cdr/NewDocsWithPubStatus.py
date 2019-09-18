#----------------------------------------------------------------------
# Reports on newly created documents and their publication statuses.
# BZIssue::754 - changes requested by Margaret
#----------------------------------------------------------------------
import cdr, cdrcgi, cgi, time
from cdrapi import db

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
script  = "NewDocsWithPubStatus.py"
title   = "CDR Administration"
section = "New Documents With Publication Status"
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
# Validate input
#----------------------------------------------------------------------
if request:  cdrcgi.valParmVal(request, valList=buttons)
if docType:  cdrcgi.valParmVal(docType, valList=cdr.getDoctypes(session))
if toDate:   cdrcgi.valParmDate(toDate)
if fromDate: cdrcgi.valParmDate(fromDate)

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
    if fromDate < cdrcgi.DAY_ONE: fromDate = cdrcgi.DAY_ONE
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
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>List of New Documents with Publication Status - %s</title>
 </head>
 <basefont face='Arial, Helvetica, sans-serif'>
 <body>
  <center>
   <b>
    <font size='4'>List of New Documents with Publication Status</font>
   </b>
   <br />
   <font size='4'>%s</font>
  </center>
  <br />
  <br />
  <font size = '4'>Documents Created Between:&nbsp;%s and %s</font>
  <br />
  <br />
""" % (time.strftime("%m/%d/%Y", now),
       time.strftime("%B %d, %Y", now),
       fromDate,
       toDate)

#----------------------------------------------------------------------
# Extract the information from the database.
#----------------------------------------------------------------------
if fromDate < cdrcgi.DAY_ONE: fromDate = cdrcgi.DAY_ONE
try:
    conn   = db.connect()
    cursor = conn.cursor()
    dtQual = docType and ("AND doc_type = '%s'" % docType) or ""
    cursor.execute("""\
         SELECT doc_id,
                cre_user,
                cre_date,
                ver_date,
                ver_user,
                doc_type,
                pv,
                epv,
                doc_title
           FROM docs_with_pub_status
          WHERE cre_date BETWEEN '%s' AND DATEADD(s, -1, DATEADD(d, 1, '%s'))
            %s
       ORDER BY doc_type,
                pv,
                cre_date,
                ver_date""" % (fromDate, toDate, dtQual))
    rows = cursor.fetchall()
except Exception as e:
    cdrcgi.bail('Database connection failure: %s' % e)

curDocType = None
for row in rows:
    (docId, creUser, creDate, verDate, verUser, docType, pvFlag,
     epvCount, docTitle) = row
    if curDocType != docType:
        if curDocType:
            html += """\
  </table>
  <br />
  <br />
"""
        curDocType = docType
        html += """\
  <b>
   <font size='3'>Document Type: &nbsp;%s</font>
  </b>
  <table border='1' cellspacing='0' cellpadding='2' width='100%%'>
   <tr>
    <td valign='top'>
     <b>
      <font size='3'>CDR ID</font>
     </b>
    </td>
    <td valign='top'>
     <b>
      <font size='3'>DocTitle</font>
     </b>
    </td>
    <td valign='top'>
     <b>
      <font size='3'>Created By</font>
     </b>
    </td>
    <td valign='top'>
     <b>
      <font size='3'>Creation Date</font>
     </b>
    </td>
    <td valign='top'>
     <b>
      <font size='3'>Latest Version Date</font>
     </b>
    </td>
    <td valign='top'>
     <b>
      <font size='3'>Latest Version By</font>
     </b>
    </td>
    <td valign='top'>
     <b>
      <font size='3'>Pub?</font>
     </b>
    </td>
    <td valign='top'>
     <b>
      <font size='3'>Earlier PubVer?</font>
     </b>
    </td>
   </tr>
""" % docType
    html += """\
   <tr>
    <td align='center'>
     <font size='3'>%d</font>
    </td>
    <td>
     <font size='3'>%s</font>
    </td>
    <td>
     <font size='3'>%s</font>
    </td>
    <td>
     <font size='3'>%s</font>
    </td>
    <td>
     <font size='3'>%s</font>
    </td>
    <td>
     <font size='3'>%s</font>
    </td>
    <td align='center'>
     <font size='3'>%s</font>
    </td>
    <td align='center'>
     <font size='3'>%s</font>
    </td>
   </tr>
""" % (docId,
       cgi.escape(docTitle),
       creUser.upper(),
       creDate[:10],
       verDate and verDate[:10] or "None",
       verUser and verUser.upper() or "None",
       pvFlag,
       epvCount and "Y" or "N")
if curDocType:
    html += """\
  </table>
"""
cdrcgi.sendPage(html + """\
 <br />
 <br />
 %s
 </body>
</html>
""" % cdrcgi.getFullUserName(session, conn))
