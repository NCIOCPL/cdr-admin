#----------------------------------------------------------------------
#
# $Id: ModifiedPubMedDocs.py,v 1.2 2002-02-21 22:34:00 bkline Exp $
#
# Reports on documents unchanged for a specified number of days.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb

#----------------------------------------------------------------------
# Named constants.
#----------------------------------------------------------------------
SCRIPT  = '/cgi-bin/cdr/Filter.py'
SUBMENU = 'Report Menu'

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)

#----------------------------------------------------------------------
# Make sure we have an active session.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect()
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Submit the query to the database.
#----------------------------------------------------------------------
query = """\
SELECT DISTINCT document.id,
                document.title
           FROM document
           JOIN query_term
             ON query_term.doc_id = document.id
          WHERE query_term.path   = '/Citation/PubmedArticle/ModifiedRecord'
            AND query_term.value  = 'Yes'
       ORDER BY document.title
"""
try:
    cursor.execute(query)
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database query failure: %s' % info[1][0])

title   = "Modified PubMed Documents"
instr   = "Number of modified documents: %d" % len(rows)
buttons = (SUBMENU, cdrcgi.MAINMENU)
header  = cdrcgi.header(title, title, instr, "ModifiedPubMedDocs.py", buttons)
html    = """\
<TABLE BORDER='0' WIDTH='100%%' CELLSPACING='1' CELLPADDING='1'>
 <TR BGCOLOR='silver' VALIGN='top'>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Doc ID</B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Title</B></FONT></TD>
 </TR>
"""
for row in rows:
    docId = "CDR%010d" % row[0]
    title = row[1].encode('latin-1')
    shortTitle = title[:100] 
    if len(title) > 100: shortTitle += " ..."
    html += """\
<TR>
  <TD BGCOLOR='white' VALIGN='top' ALIGN='center'>
   <A HREF=%s?DocId=%s&Filter=%s">
    <FONT SIZE='-1'>%s</FONT>
   </A>
  </TD>
  <TD BGCOLOR='white' ALIGN='left'><FONT SIZE='-1'>%s</FONT></TD>
 </TR>
""" % (SCRIPT, 
       docId,
       'name:Citation QC Report',
       docId,
       shortTitle)
cdrcgi.sendPage(header + html + """\
   </TABLE>
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>""" % (cdrcgi.SESSION, session))
