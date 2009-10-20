#----------------------------------------------------------------------
#
# $Id$
#
# Report on documents checked out to a user.
#
# $Log: not supported by cvs2svn $
# Revision 1.4  2002/04/24 20:36:03  bkline
# Changed "Title" label to "DocTitle" as requested by Eileen (issue #161).
#
# Revision 1.3  2002/03/02 13:51:32  bkline
# Rearranged columns.  Added call to unicodeToLatin1().
#
# Revision 1.2  2002/03/02 13:04:42  bkline
# Fixed header comment.
#
# Revision 1.1  2002/03/02 13:04:03  bkline
# Report on documents checked out to a user.
#
#----------------------------------------------------------------------
import cgi, httplib, urlparse, socket, cdrdb, cdrcgi

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
user    = fields and fields.getvalue('User') or None
SUBMENU = 'Report Menu'

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("reports.py", session)

#----------------------------------------------------------------------
# Put up form if we have no user.
#----------------------------------------------------------------------
if not user:
    header = cdrcgi.header('CDR Report on Checked Out Documents',
                           'CDR Reports',
                           'Checked Out Documents',
                           'CheckedOutDocs.py',
                           ("Submit", SUBMENU, cdrcgi.MAINMENU))
    form = """\
      <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
      <B>User:&nbsp;</B>
      <INPUT NAME='User'>
     </FORM>
    </BODY>
   </HTML>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Display the report.
#----------------------------------------------------------------------
header = cdrcgi.header('CDR Report on Checked Out Documents',
                       'CDR Reports',
                       'Checked Out Documents',
                       'CheckUrls.py',
                       (SUBMENU, cdrcgi.MAINMENU))
table  = """\
<TABLE BORDER='0' WIDTH='100%' CELLSPACING='1' CELLPADDING='2'>
 <TR BGCOLOR='silver'>
  <TD NOWRAP='1'><B>Checked Out</B></TD>
  <TD><B>Type</B></TD>
  <TD><B>ID</B></TD>
  <TD><B>DocTitle</B></TD>
 </TR>
"""

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect()
    cursor = conn.cursor()
    query  = """\
        SELECT t.name,
               d.title,
               d.id,
               c.dt_out
          FROM usr u
          JOIN checkout c
            ON c.usr = u.id
          JOIN document d
            ON d.id = c.id
          JOIN doc_type t
            ON t.id = d.doc_type
         WHERE u.name = ?
           AND dt_in IS NULL
      ORDER BY c.dt_out, t.name, d.id"""
    cursor.execute(query, user)
    rows = cursor.fetchall()
    if not rows:
        cdrcgi.sendPage(header + """\
  <H3>No Documents Checked Out To %s</H3>
  <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>
""" % (user, cdrcgi.SESSION, session))
    for row in rows:
        table += """\
   <TR BGCOLOR='white'>
    <TD NOWRAP='1' VALIGN='top'>%s</TD>
    <TD VALIGN='top'>%s</TD>
    <TD VALIGN='top'>CDR%010d</TD>
    <TD VALIGN='top'>%s</TD>
   </TR>
""" % (row[3], row[0], row[2], cdrcgi.unicodeToLatin1(row[1]))
except cdrdb.Error, info:
    cdrcgi.bail('Database failure: %s' % info[1][0])

cdrcgi.sendPage(header + table + """\
   </TABLE>
   <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
  </FORM>
 </BODY>
</HTML>""" % (cdrcgi.SESSION, session))
