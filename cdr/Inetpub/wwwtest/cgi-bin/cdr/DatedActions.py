#----------------------------------------------------------------------
#
# $Id: DatedActions.py,v 1.1 2002-03-13 16:58:07 bkline Exp $
#
# Reports on dated actions for a particular document type.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, cdrcgi, cgi, re, time, xml.dom.minidom

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
docType = fields and fields.getvalue('DocType') or None
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "DatedActions.py"
title   = "CDR Administration"
section = "Dated Actions Report"
header  = cdrcgi.header(title, title, section, script, buttons)

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
if not docType:
    docTypes = cdr.getDoctypes(session)
    if type(docTypes) in [type(""), type(u"")]:
        cdrcgi.bail(docTypes)
    form = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <B>Select Document Type:&nbsp;</B>
   <SELECT NAME='DocType'>
    <OPTION VALUE='' SELECTED>&nbsp;</OPTION>
""" % (cdrcgi.SESSION, session)
    for docType in docTypes:
        form += """\
    <OPTION VALUE='%s'>%s &nbsp;</OPTION>
""" % (docType, docType)
    form += """\
   </SELECT>
  </FORM>
 </BODY>
</HTML>
"""
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# We have a request; do it.
#----------------------------------------------------------------------
parms  = (('DocType', docType),)
name   = 'Dated Actions'
report = cdr.report(session, name, parms)
report = re.sub("<!\[CDATA\[", "", report)
report = re.sub("\]\]>", "", report)
report = xml.dom.minidom.parseString(report).documentElement
now    = time.localtime(time.time())

#----------------------------------------------------------------------
# Connect to the database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Get the full name for the requesting user.
#----------------------------------------------------------------------
try:
    cursor.execute("""\
            SELECT fullname
              FROM usr
              JOIN session
                ON session.usr = usr.id
             WHERE session.name = ?""", session)
    usr = cursor.fetchone()[0]
except:
    cdrcgi.bail("Unable to find current user name")

#----------------------------------------------------------------------
# Start the page.
#----------------------------------------------------------------------
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Date Action Report %s %s</title>
 </head>
 <basefont face='Arial, Helvetica, sans-serif'>
 <body>
  <center>
   <b>
    <font size='4'>Date Action Report</font>
   </b>
   <br />
   <b>
    <font size='4'>Document Type: %s</font>
   </b>
  </center>
  <br />
  <br />
  <table border='1' cellspacing='0' cellpadding='2' width='100%%'>
   <tr>
    <td>
     <b>
      <font size='3'>DocID</font>
     </b>
    </td>
    <td>
     <b>
      <font size='3'>DocTitle</font>
     </b>
    </td>
    <td nowrap='1'>
     <b>
      <font size='3'>Action Description</font>
     </b>
    </td>
    <td nowrap='1'>
     <b>
      <font size='3'>Action Date</font>
     </b>
    </td>
    <td>
     <b>
      <font size='3'>Comment</font>
     </b>
    </td>
   </tr>
""" % (docType, time.strftime("%m/%d/%Y", now), docType)
   
#----------------------------------------------------------------------
# Extract the information from the XML so we can sort it.
#----------------------------------------------------------------------
class ReportRow:
    def __init__(self, id, title, action): #date, desc, comment):
        dateElems = action.getElementsByTagName("ActionDate")
        descElems = action.getElementsByTagName("ActionDescription")
        commElems = action.getElementsByTagName("Comment")
        self.id      = id
        self.title   = title
        self.date    = dateElems and cdr.getTextContent(dateElems[0]) or ""
        self.desc    = descElems and cdrcgi.unicodeToLatin1(
                           cdr.getTextContent(descElems[0])) or ""
        self.comment = commElems and cdrcgi.unicodeToLatin1(
                           cdr.getTextContent(commElems[0])) or ""
reportRows = []
docs = report.getElementsByTagName("ReportRow")
if docs:
    for doc in docs:
        idElems = doc.getElementsByTagName("DocId")
        titleElems = doc.getElementsByTagName("DocTitle")
        if not idElems: cdrcgi.bail("Missing DocId in report XML")
        if not titleElems: cdrcgi.bail("Missing DocTitle in report XML")
        id = cdr.getTextContent(idElems[0])
        title = cdrcgi.unicodeToLatin1(cdr.getTextContent(titleElems[0]))
        actions = doc.getElementsByTagName("DatedAction")
        if actions:
            for action in actions:
                reportRows.append(ReportRow(id, title, action))
    reportRows.sort(lambda a, b: cmp(a.date, b.date) or cmp(a.id, b.id))
    for row in reportRows:
        html += """\
   <tr>
    <td valign='top'>
     <font size='3'>%s</font>
    </td>
    <td valign='top'>
     <font size='3'>%s</font>
    </td>
    <td valign='top'>
     <font size='3'>%s</font>
    </td>
    <td valign='top'>
     <font size='3'>%s</font>
    </td>
    <td valign='top'>
     <font size='3'>%s</font>
    </td>
   </tr>
""" % (row.id      or "&nbsp;",
       row.title   or "&nbsp;",
       row.desc    or "&nbsp;",
       row.date    or "&nbsp;",
       row.comment or "&nbsp;")
cdrcgi.sendPage(html + """\
  </table>
  <br />
  <br />
  <br />
  <font size='3'>
   <i>%s</i>
  </font>
 </body>
</html>
""" % usr)
