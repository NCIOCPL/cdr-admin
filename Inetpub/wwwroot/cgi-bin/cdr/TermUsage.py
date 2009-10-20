#----------------------------------------------------------------------
#
# $Id$
#
# Reports on documents which link to specified terms.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2002/02/21 22:34:01  bkline
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
docIds  = fields and fields.getvalue("DocId")   or None
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
SUBMENU = "Report Menu"

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Put out the form if we don't have a request.
#----------------------------------------------------------------------
if not docIds:
    title   = "Term Usage"
    instr   = "Report on documents indexed by specified terms"
    script  = "TermUsage.py"
    buttons = ("Submit Request", SUBMENU, cdrcgi.MAINMENU)
    header  = cdrcgi.header(title, title, instr, script, buttons)
    form    = """\
    <TABLE CELLSPACING='0' CELLPADDING='0' BORDER='0'>
    <TR>
      <TD ALIGN='right'><B>Term ID:&nbsp;</B></TD>
      <TD><INPUT NAME='DocId'></TD>
    </TR>
    <TR>
      <TD ALIGN='right'><B>Term ID:&nbsp;</B></TD>
      <TD><INPUT NAME='DocId'></TD>
    </TR>
    <TR>
      <TD ALIGN='right'><B>Term ID:&nbsp;</B></TD>
      <TD><INPUT NAME='DocId'></TD>
    </TR>
   </TABLE>
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Normalize the field values.
#----------------------------------------------------------------------
if type(docIds) != type([]):
    docIds = [docIds]
pattern = re.compile("(\d+)")
for i in range(len(docIds)):
    value = docIds[i]
    match = pattern.search(value)
    if not match:
        cdrcgi.bail("Invalid document ID: %s" % value)
    intVal = string.atoi(match.group(1))
    if not intVal:
        cdrcgi.bail("Invalid document ID: %s" % value)
    docIds[i] = intVal

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Find the documents using the specified terms.
#----------------------------------------------------------------------
query   = """\
SELECT DISTINCT ut.name, ud.id, ud.title, td.id, td.title
           FROM doc_type ut
           JOIN document ud
             ON ud.doc_type = ut.id
           JOIN query_term q
             ON q.doc_id = ud.id
           JOIN document td
             ON td.id = q.int_val
          WHERE q.path LIKE '%/@cdr:ref'
            AND ut.name <> 'Term'
            AND td.id IN ("""
sep = ""
for id in docIds:
    query += sep + '?'
    sep = ', '
query += """)
       ORDER BY ut.name, ud.title
"""

try:
    cursor.execute(query, docIds)
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database query failure: %s' % info[1][0])

title   = "CDR Term Usage Report"
instr   = "Number of documents using specified terms: %d" % len(rows)
buttons = (SUBMENU, cdrcgi.MAINMENU)
header  = cdrcgi.header(title, title, instr, "TermUsage.py", buttons)
html    = """\
<TABLE BORDER='0' WIDTH='100%%' CELLSPACING='1' CELLPADDING='3'>
 <TR BGCOLOR='silver' VALIGN='top'>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Doc Type</B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Doc ID</B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Doc Title</B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Term ID</B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Term</B></FONT></TD>
 </TR>
"""
for row in rows:
    title = row[2]
    termName = row[4]
    #shortTitle = title[:50] 
    #shortTermName = termName[:30]
    #if len(title) > 50: shortTitle += " ..."
    #if len(termName) > 30: shortTermName += " ..."
    html += u"""\
 <TR>
  <TD BGCOLOR='white' VALIGN='top' ALIGN='left'><FONT SIZE='-1'>%s</FONT></TD>
  <TD BGCOLOR='white' VALIGN='top' ALIGN='center'><FONT SIZE='-1'>CDR%010d</FONT></TD>
  <TD BGCOLOR='white' VALIGN='top' ALIGN='left'><FONT SIZE='-1'>%s</FONT></TD>
  <TD BGCOLOR='white' VALIGN='top' ALIGN='center'><FONT SIZE='-1'>CDR%010d</FONT></TD>
  <TD BGCOLOR='white' VALIGN='top' ALIGN='left'><FONT SIZE='-1'>%s</FONT></TD>
 </TR>
""" % (row[0],
       row[1],
       title, #shortTitle,
       row[3],
       termName) #shortTermName)
cdrcgi.sendPage(header + html + """\
   </TABLE>
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>""" % (cdrcgi.SESSION, session))
