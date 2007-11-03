#----------------------------------------------------------------------
#
# $Id: PersonOrgLocLinks.py,v 1.2 2007-11-03 14:15:07 bkline Exp $
#
# Reports on Person documents which link to Organization address 
# fragments.
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

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
fragLink = fields and fields.getvalue("FragLink") or None

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
          WHERE query_term.path   = '/Person/PersonLocations' +
                                    '/OtherPracticeLocation' +
                                    '/OrganizationLocation/@cdr:ref'
            AND query_term.value  = ?
       ORDER BY document.title
"""
try:
    cursor.execute(query, fragLink)
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database query failure: %s' % info[1][0])

title   = "Person Documents Linking to Fragment %s" % fragLink
instr   = "Number of linking documents: %d" % len(rows)
buttons = ()
header  = cdrcgi.header(title, title, instr, None, buttons)
html    = """\
<TABLE BORDER='0' WIDTH='100%' CELLSPACING='1' CELLPADDING='1'>
 <TR BGCOLOR='silver' VALIGN='top'>
  <TD ALIGN='center' WIDTH='15%'><FONT SIZE='-1'><B>Doc ID</B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Title</B></FONT></TD>
 </TR>
"""
for row in rows:
    docId = "CDR%010d" % row[0]
    title = row[1]
    shortTitle = title[:100] 
    if len(title) > 100: shortTitle += " ..."
    html += u"""\
<TR>
  <TD BGCOLOR='white' VALIGN='top' WIDTH='15%%' ALIGN='center'>
   <A HREF='%s?DocId=%s&Filter=%s'>
    <FONT SIZE='-1'>%s</FONT>
   </A>
  </TD>
  <TD BGCOLOR='white' ALIGN='left'><FONT SIZE='-1'>%s</FONT></TD>
 </TR>
""" % (SCRIPT, 
       docId,
       'CDR266296',
       docId,
       shortTitle)
cdrcgi.sendPage(header + html + "</TABLE></BODY></HTML>")
