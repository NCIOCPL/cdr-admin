#----------------------------------------------------------------------
# Reports documents last modified during a specified time period.
# JIRA::OCECDR-3731
#----------------------------------------------------------------------
import cgi
import datetime
import os
import sys
import msvcrt
import cdr
import cdrdb
import cdrcgi

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
fromDate = fields.getvalue('FromDate') or None
toDate   = fields.getvalue('ToDate')   or None
docType  = fields.getvalue('DocType')  or None
format_  = fields.getvalue('format')   or "html"
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "DateLastModified.py"
title   = "CDR Administration"
section = "Date Last Modified"
header  = cdrcgi.header(title, title, section, script, buttons)
today   = datetime.date.today()

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
    toDate = datetime.date.today()
    fromDate = toDate - datetime.timedelta(7)
    docTypes = cdr.getDoctypes(session)
    if type(docTypes) in [type(""), type(u"")]:
        cdrcgi.bail(docTypes)
    form = u"""\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <STYLE>
    .fixed-width { width: 200px; }
   </STYLE>
   <TABLE BORDER='0'>
    <TR>
     <TD><B>Document Type:&nbsp;</B></TD>
     <TD>
      <SELECT class='fixed-width' NAME='DocType'>
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
     <TD><INPUT class='fixed-width' NAME='FromDate' VALUE='%s'>&nbsp;
         (use format YYYY-MM-DD for dates, e.g. 2002-01-01)</TD>
    </TR>
    <TR>
     <TD><B>End Date:&nbsp;</B></TD>
     <TD><INPUT class='fixed-width' NAME='ToDate' VALUE='%s'>&nbsp;</TD>
    </TR>
    <TR>
     <TD><B>Format:&nbsp;</B></TD>
     <TD>
      <SELECT class='fixed-width' NAME='format'>
       <OPTION value='html' selected='selected'>HTML</OPTION>
       <OPTION value='excel'>Excel Workbook</OPTION>
      </SELECT>&nbsp;
     </TD>
    </TR>
   </TABLE>
  </FORM>
 </BODY>
</HTML>
""" % (fromDate, toDate)
    cdrcgi.sendPage(header + form)

# Validate dates and docType from the input form
if not cdr.valFromToDates('%Y-%m-%d', fromDate, toDate):
    cdrcgi.bail(
      "Invalid Start or End date.  Use YYYY-MM-DD, Start no later than End.")

if docType and docType not in cdr.getDoctypes(session):
    cdrcgi.bail('Unknown document type requested: "%s"' % cgi.escape(docType))

#----------------------------------------------------------------------
# We have a request; do it.
#----------------------------------------------------------------------
headerDocType = docType and ("%s Documents" % docType) or "All Document Types"
if format_ == "html":
    html = u"""\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Date Last Modified Report %s %s</title>
  <basefont face='Arial, Helvetica, sans-serif'>
 </head>
 <body>
  <center>
   <b>
    <font size='4'>Date Last Modified Report</font>
   </b>
   <br />
   <b>
    <font size='4'>From %s to %s</font>
   </b>
  </center>
  <br />
  <br />
""" % (headerDocType, today.strftime("%m/%d/%Y"), fromDate, toDate)
else:
    styles = cdrcgi.ExcelStyles()

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
        if format_ == "html":
            cdrcgi.sendPage(html + u"""\
  <b>
   <font size='3'>No documents found.</font>
  </b>
 </body>
</html>
""")
        else:
            cdrcgi.bail("No documents found")

    while row:
        docType, lastMod, docId, title = row
        if docType != lastDocType:
            if format_ == "html":
                if lastDocType:
                    html += u"""\
  </table>
  <br />
"""
                html += u"""\
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
            else:
                sheet = styles.add_sheet(docType)
                widths = 20, 15, 100
                labels = "Date Last Modified", "CDR ID", "Document Title"
                assert(len(widths) == len(labels))
                for i, chars in enumerate(widths):
                    sheet.col(i).width = styles.chars_to_width(chars)
                vals = docType, fromDate, toDate
                title = "%s Documents Last Modified Between %s and %s" % vals
                sheet.write_merge(0, 0, 0, 2, title, styles.header)
                for i, label in enumerate(labels):
                    sheet.write(2, i, label, styles.header)
                rowNumber = 3
            lastDocType = docType
        if format_ == "html":
            html += u"""\
   <tr>
    <td valign='top'>%s</td>
    <td valign='top'>CDR%010d</td>
    <td>%s</td>
   </tr>
""" % (lastMod, docId, title)
        else:
            sheet.write(rowNumber, 0, lastMod, styles.center)
            sheet.write(rowNumber, 1, "CDR%010d" % docId, styles.center)
            sheet.write(rowNumber, 2, title, styles.left)
            rowNumber += 1
        row = cursor.fetchone()
    if format_ == "html" and lastDocType:
        html += u"""\
  </table>
"""

except cdrdb.Error, info:
    cdrcgi.bail('Database failure: %s' % info[1][0])

if format_ == "html":
    cdrcgi.sendPage(html + u"""\
 </body>
</html>
""")
else:
    now = datetime.datetime.now()
    name = "DateLastModified-%s.xls" % now.strftime("%Y%m%d%H%M%S")
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    print "Content-type: application/vnd.ms-excel"
    print "Content-disposition: attachment; filename=%s" % name
    print
    styles.book.save(sys.stdout)
