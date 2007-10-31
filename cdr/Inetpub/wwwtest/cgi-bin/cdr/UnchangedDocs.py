#----------------------------------------------------------------------
#
# $Id: UnchangedDocs.py,v 1.6 2007-10-31 21:13:48 bkline Exp $
#
# Reports on documents unchanged for a specified number of days.
#
# $Log: not supported by cvs2svn $
# Revision 1.5  2007/10/31 21:11:42  bkline
# Fixed handling of Unicode.
#
# Revision 1.4  2004/02/17 19:55:02  venglisc
# Modified the header title.
#
# Revision 1.3  2002/04/24 20:37:10  bkline
# Changed "Title" label to "DocTitle" at Eileen's request (issue #161).
#
# Revision 1.2  2002/02/21 15:22:03  bkline
# Added navigation buttons.
#
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
days    = fields and fields.getvalue("Days")    or None
type    = fields and fields.getvalue("DocType") or None
maxRows = fields and fields.getvalue("MaxRows") or None
SUBMENU = 'Report Menu'

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Create a picklist for document types.
#----------------------------------------------------------------------
def makePicklist(docTypes):
    picklist = "<SELECT NAME='DocType'><OPTION>All</OPTION>"
    selected = " SELECTED"
    for docType in docTypes:
        picklist += "<OPTION%s>%s</OPTION>" % (selected, docType[0])
        selected = ""
    return picklist + "</SELECT>"

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Do the report if we have a request.
#----------------------------------------------------------------------
if request:
    maxRows = maxRows and int(maxRows) or 1000
    days = days and int(days) or 365
    if type and type != 'All':
        query   = """\
   SELECT TOP %d d.id AS DocId, 
          d.title AS DocTitle, 
          MAX(a.dt) AS LastChange
     FROM document d, 
          audit_trail a, 
          doc_type t
    WHERE d.id = a.document
      AND d.doc_type = t.id
      AND t.name = '%s'
 GROUP BY d.id, d.title
   HAVING DATEDIFF(day, MAX(a.dt), GETDATE()) > %d
 ORDER BY MAX(a.dt), d.id
""" % (maxRows, type, days)
    else:
        query   = """\
   SELECT TOP %d d.id AS DocId, 
          d.title AS DocTitle, 
          MAX(a.dt) AS LastChange
     FROM document d, 
          audit_trail a
    WHERE d.id = a.document
 GROUP BY d.id, d.title
   HAVING DATEDIFF(day, MAX(a.dt), GETDATE()) > %d
 ORDER BY MAX(a.dt), d.id
""" % (maxRows, days)
    try:
        cursor.execute(query, timeout = 600)
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])

    title   = "Documents Unchanged for %d Days" % days
    instr   = "Document type: %s" % type
    buttons = (SUBMENU, cdrcgi.MAINMENU)
    header  = cdrcgi.header(title, title, instr, "UnchangedDocs.py", buttons)
    html    = [u"""\
<INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
<TABLE BORDER='0' WIDTH='100%%' CELLSPACING='1' CELLPADDING='1'>
 <TR BGCOLOR='silver' VALIGN='top'>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Doc ID</B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>DocTitle</B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Last Change</B></FONT></TD>
 </TR>
""" % (cdrcgi.SESSION, session)]
    for row in rows:
        title = row[1]
        shortTitle = title[:100]
        if len(title) > 100: shortTitle += u" ..."
        html.append(u"""\
 <TR>
  <TD BGCOLOR='white' VALIGN='top' ALIGN='center'><FONT SIZE='-1'>CDR%010d</FONT></TD>
  <TD BGCOLOR='white' ALIGN='left'><FONT SIZE='-1'>%s</FONT></TD>
  <TD BGCOLOR='white' VALIGN='top' ALIGN='center'><FONT SIZE='-1'>%s</FONT></TD>
 </TR>
""" % (row[0],
       shortTitle,
       row[2][:10]))
    html.append(u"</TABLE></FORM></BODY></HTML>")
    cdrcgi.sendPage(header + u"".join(html))

#----------------------------------------------------------------------
# Put out the form if we don't have a request.
#----------------------------------------------------------------------
else:
    try:
        cursor.execute("""\
SELECT DISTINCT name 
           FROM doc_type 
          WHERE name IS NOT NULL and name <> ''
       ORDER BY name
""")
        docTypes = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail('Database query failure: %s' % info[1][0])
    title   = "CDR Administration"
    instr   = "Unchanged Documents"
    buttons = ("Submit Request", SUBMENU, cdrcgi.MAINMENU)
    header  = cdrcgi.header(title, title, instr, "UnchangedDocs.py", buttons)
    form    = """\
        <TABLE CELLSPACING='0' CELLPADDING='0' BORDER='0'>
        <TR>
          <TD ALIGN='right'><B>Days Since Last Change&nbsp;</B></TD>
          <TD><INPUT NAME='Days' VALUE='365'></TD>
        </TR>
        <TR>
          <TD ALIGN='right'><B>Document Type&nbsp;</B></TD>
          <TD>%s</TD>
        </TR>
        <TR>
          <TD ALIGN='right'><B>Max Rows&nbsp;</B></TD>
          <TD><INPUT NAME='MaxRows' VALUE='1000'></TD>
        </TR>
       </TABLE>
       <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
      </FORM>
     </BODY>
    </HTML>
    """ % (makePicklist(docTypes), cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)
