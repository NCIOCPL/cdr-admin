#----------------------------------------------------------------------
#
# $Id: DateLastModified.py,v 1.1 2002-04-22 22:15:45 bkline Exp $
#
# Reports documents last modified during a specified time period.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, re, time, xml.dom.minidom

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
script  = "DateLastModified.py"
title   = "CDR Administration"
section = "Date Last Modified"
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
# We have a request; do it.
#----------------------------------------------------------------------
headerDocType = docType and ("%s Documents" % docType) or "All Document Types"
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Date Last Modified Report %s %s</title>
  <basefont face='Arial, Helvetica, sans-serif'>
 </head>
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
""" % (headerDocType, time.strftime("%m/%d/%Y", now), fromDate, toDate)
   
#----------------------------------------------------------------------
# Extract the information from the database.
#----------------------------------------------------------------------
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
    dtQual = docType and ("AND t.name = '%s'" % docType) or ""
    cursor.execute("""\
            SELECT t.name,
                   q.value,
                   d.id,
                   d.title
              FROM doc_type t
              JOIN document d
                ON d.doc_type = t.id
              JOIN query_term q
                ON q.doc_id = d.id
             WHERE q.path LIKE '%%/DateLastModified'
               AND q.value BETWEEN ? AND ?
               %s
          ORDER BY t.name,
                   q.value,
                   d.id""" % dtQual, (fromDate, toDate))
    lastDocType = None
    row = cursor.fetchone()
    if not row:
        cdrcgi.sendPage(html + """\
  <b>
   <font size='3'>No documents found.</font>
  </b>
 </body>
</html>
""")
    while row:
        docType, lastMod, docId, title = row
        if docType != lastDocType:
            if lastDocType:
                html += """\
  </table>
  <br />
"""
            lastDocType = docType
            html += """\
  <b>
   <font size='3'>Document Type:&nbsp;&nbsp;&nbsp;&nbsp;%s</font>
  </b>
  <table border='1' cellspacing='0' cellpadding='2' width='100%%'>
   <tr>
    <td align='center'>
     <b>
      <font size='3'>Date Last Modified</font>
     </b>
    </td>
    <td align='center'>
     <b>
      <font size='3'>DocID</font>
     </b>
    </td>
    <td align='center'>
     <b>
      <font size='3'>DocTitle</font>
     </b>
    </td>
   </tr>
""" % docType
        html += """\
   <tr>
    <td valign='top'>%s</td>
    <td valign='top'>CDR%010d</td>
    <td>%s</td>
   </tr>
""" % (lastMod, docId, title)
        row = cursor.fetchone()
    if lastDocType:
        html += """\
  </table>
"""

except cdrdb.Error, info:
    cdrcgi.bail('Database failure: %s' % info[1][0])

cdrcgi.sendPage(html + """\
 </body>
</html>
""")
