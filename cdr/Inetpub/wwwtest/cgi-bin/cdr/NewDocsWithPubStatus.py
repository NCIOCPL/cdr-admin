#----------------------------------------------------------------------
#
# $Id: NewDocsWithPubStatus.py,v 1.1 2002-07-02 13:47:56 bkline Exp $
#
# Reports on newly created documents and their publication statuses.
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
    conn   = cdrdb.connect()
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
                epv
           FROM docs_with_pub_status
          WHERE cre_date BETWEEN ? AND ?
            %s
       ORDER BY doc_type, 
                pv, 
                cre_date, 
                ver_date""" % dtQual, (fromDate, toDate))
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

curDocType = None
for row in rows:
    docId, creUser, creDate, verDate, verUser, docType, pvFlag, epvCount = row
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
      <font size='3'>DocID</font>
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
      <font size='3'>Publishable?</font>
     </b>
    </td>
    <td valign='top'>
     <b>
      <font size='3'>Any Earlier Publishable Versions?</font>
     </b>
    </td>
   </tr>
""" % docType
    html += """\
   <tr>
    <td>
     <font size='3'>CDR%010d</font>
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
