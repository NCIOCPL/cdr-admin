#----------------------------------------------------------------------
#
# $Id$
#
# Report of documents linking to a specified glossary term.
#
# $Log: not supported by cvs2svn $
# Revision 1.4  2009/02/24 16:39:33  bkline
# Updated Term Links report to match new glossary document structures.
#
# Revision 1.3  2003/06/02 14:18:42  bkline
# Fixed problem with encoding of Unicode characters.
#
# Revision 1.2  2002/03/20 20:08:14  bkline
# Added description to header comment.
#
# Revision 1.1  2002/03/20 18:39:02  bkline
# Report of documents linking to a specified glossary term.
#
#----------------------------------------------------------------------

import cdr, cdrdb, cdrcgi, cgi, re, string, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
name    = fields and fields.getvalue('Name') or None
id      = fields and fields.getvalue('Id')   or None
SUBMENU = "Report Menu"
buttons = ["Submit Request", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script  = "GlossaryTermLinks.py"
title   = "CDR Administration"
section = "Glossary Term Links QC Report"
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
if not name and not id:
    form = """\
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
   <TABLE BORDER='0'>
    <TR>
     <TD ALIGN='right'><B>Document ID:&nbsp;</B></TD>
     <TD><INPUT NAME='Id'></TD>
    </TR>
    <TR>
     <TD ALIGN='right'><B>Glossary Term Name:&nbsp;</B></TD>
     <TD><INPUT NAME='Name'></TD>
    </TR>
   </TABLE>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Get the document ID.
#----------------------------------------------------------------------
if id:
    digits = re.sub('[^\d]', '', id)
    id     = string.atoi(digits)
else:
    try:
        cursor.execute("""\
                SELECT DISTINCT doc_id
                           FROM query_term
                          WHERE path  = '/GlossaryTermName/TermName'
                                      + '/TermNameString'
                            AND value = ?""", name)
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure looking up glossary term '%s': %s" % (name,
                                                                   info[1][0]))
    if len(rows) > 1: cdrcgi.bail("Ambiguous term name: '%s'" % name)
    if len(rows) < 1: cdrcgi.bail("Unknown term '%s'" % name)
    id = rows[0][0]

#----------------------------------------------------------------------
# Get the name and source for the term.  Even if we got the name from
# the user, we are certain this way that the capitalization is correct.
#----------------------------------------------------------------------
try:
    cursor.execute("""\
            SELECT DISTINCT name.value,
                            source.value
                       FROM query_term name
            LEFT OUTER JOIN query_term source
                         ON source.doc_id = name.doc_id
                        AND source.path = '/GlossaryTermName/TermName'
                                        + '/TermNameSource'
                      WHERE name.doc_id = ?
                        AND name.path   = '/GlossaryTermName/TermName'
                                        + '/TermNameString'""", id)
    rows = cursor.fetchall()
    if not rows:
        cdrcgi.bail("Can't find GlossaryTermName document for CDR%s" % id)
    (name, source) = rows[0]
except cdrdb.Error, info:
    cdrcgi.bail('Failure fetching term name and source for CDR%s: %s' %
                (id, info[1][0]))

#----------------------------------------------------------------------
# Get the list of documents which link to this glossary term.
#----------------------------------------------------------------------
try:
    cursor.execute("""\
            SELECT DISTINCT query_term.doc_id,
                            document.title,
                            doc_type.name
                       FROM query_term
                       JOIN document
                         ON document.id = query_term.doc_id
                       JOIN doc_type
                         ON doc_type.id = document.doc_type
                      WHERE query_term.value = 'CDR%010d'
                   ORDER BY doc_type.name,
                            query_term.doc_id""" % id)
except cdrdb.Error, info:
    cdrcgi.bail('Failure fetching list of linking documents: %s' % info[1][0])

#----------------------------------------------------------------------
# Start the page.
#----------------------------------------------------------------------
ellipsis = '.' * 70
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>%s - %s - CDR%010d</title>
 </head>
 <basefont face='Arial, Helvetica, sans-serif'>
 <body>
  <center>
   <b>
    <font size='4'>Documents Linked to Glossary Term Names Report</font>
   </b>
   <br />
   <br />
  </center>
  <table border='0'>
   <tr>
    <td align='top'>
     <b>
      <font size='3'>Name</font>
     </b>
    </td>
    <td align='top' nowrap='1'>
     <font size='3'>%s</font>
    </td>
    <td>
     <font size='3'>%s</font>
    </td>
   </tr>
   <tr>
    <td align='top'>
     <b>
      <font size='3'>Source</font>
     </b>
    </td>
    <td align='top' nowrap='1'>
     <font size='3'>%s</font>
    </td>
    <td>
     <font size='3'>%s</font>
    </td>
   </tr>
  </table>
  <br />
  <br />
  <b>
   <i>
    <font size='3'>Documents Linked to Term Name</font>
   </i>
  </b>
""" % (name, time.strftime("%B %d, %Y", now), id, ellipsis, name, ellipsis, 
       source)
   
#----------------------------------------------------------------------
# Display the report rows.
#----------------------------------------------------------------------
filterParms = [['linkTarget', 'CDR%010d' % id]]
try:
    row = cursor.fetchone()
    currentDoctype = None
    while row:
        (docId, docTitle, docType) = row
        if docType != currentDoctype:
            if currentDoctype:
                html += """\
  </table>
"""
            currentDoctype = docType
            html += """\
  <br />
  <br />
  <b>
   <font size='3'>%s</font>
  </b>
  <br />
  <table border='1' cellspacing='0' cellpadding='1' width='100%%'>
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
    <td>
     <b>
      <font size='3'>ElementName</font>
     </b>
    </td>
    <td>
     <b>
      <font size='3'>FragmentID</font>
     </b>
    </td>
   </tr>
""" % currentDoctype

        resp = cdr.filterDoc(session, ['name:Glossary Link Report Filter'],
                             docId, parm = filterParms)
        #cdrcgi.bail(resp[0])
        if type(resp) in (type(''), type(u'')):
            cdrcgi.bail(resp)
        html += cdrcgi.decode(resp[0])
        row = cursor.fetchone()

except cdrdb.Error, info:
    cdrcgi.bail('Failure fetching linking document: %s' % info[1][0])

if currentDoctype:
    html += """\
  </table>
"""
cdrcgi.sendPage(html + """\
 </body>
</html>
""")
