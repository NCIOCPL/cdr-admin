#----------------------------------------------------------------------
#
# $Id: ListIssues.py,v 1.3 2002-05-10 21:15:25 bkline Exp $
#
# Lists CDR development issues.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2002/05/10 19:27:16  bkline
# Added option to filter out future enhancements.
#
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, dbi, cdrdb

#----------------------------------------------------------------------
# Retrieve and display the user information.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
title   = "CDR Development"
section = "Issue List"
request = cdrcgi.getRequest(fields) or "Hide Resolved Issues"
sort_by = fields and fields.getvalue("sort_by") or "logged"
script  = "ListIssues.py"
buttons = ["Hide Resolved Issues", "Show Resolved Issues"]
filter  = request == "Hide Resolved Issues" and " AND resolved IS NULL" or ""
nextVer = fields and fields.getvalue("NextVer") and 1 or 0
#script  = "DumpParams.pl"
header  = cdrcgi.header(title, title, section, script, buttons, numBreaks = 1)

#----------------------------------------------------------------------
# Retrieve the information directly from the database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])
cursor = conn.cursor()
if sort_by == "priority": sort_by = "priority DESC"
if not nextVer:
    filter += " AND priority <> '1 - Later Version' "
query  = """\
   SELECT id, logged, logged_by, substring(priority, 1, 1),
          description, assigned, assigned_to, resolved, resolved_by
     FROM issue
    WHERE priority <> 'X - Deleted'%s
 ORDER BY %s, id
""" % (filter, sort_by)
try:
    cursor.execute(query)
except cdrdb.Error, info:
    cdrcgi.bail('Database query failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Display the information in a table.
#----------------------------------------------------------------------
flag = nextVer and "CHECKED" or ""
body = """\
<TABLE BORDER='0' WIDTH='100%%' CELLSPACING='1' CELLPADDING='1'>
 <TR BGCOLOR='silver' VALIGN='top'>
  <TD ALIGN='center'><FONT SIZE='-1'><B>&nbsp;#&nbsp;</B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>
   <A HREF='/cgi-bin/cdr/ListIssues.py?sort_by=logged&%s=%s'>Logged</A>
  </B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>By</B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>
   <A HREF='/cgi-bin/cdr/ListIssues.py?sort_by=priority&%s=%s'>Pty</A>
  </B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Description</B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>
   <A HREF='/cgi-bin/cdr/ListIssues.py?sort_by=assigned&%s=%s'>Assigned</A>
  </B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>
   <A HREF='/cgi-bin/cdr/ListIssues.py?sort_by=assigned_to&%s=%s'>To</A>
  </B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Resolved</B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>By</B></FONT></TD>
 </TR>
""" % (cdrcgi.REQUEST, request,
       cdrcgi.REQUEST, request,
       cdrcgi.REQUEST, request,
       cdrcgi.REQUEST, request)
try:
    for rec in cursor.fetchall():
        desc = cgi.escape(rec[4])
        descSubstring = desc[:40]
        if len(desc) > 40: descSubstring += '...'
        body += """
 <TR>
  <TD BGCOLOR='white' ALIGN='right' NOWRAP>
   <FONT SIZE='-1'>
    <A HREF='/cgi-bin/cdr/EditIssue.py?id=%d' TARGET='issue-form'>%d</A>
   </FONT>
  </TD>
  <TD BGCOLOR='white' ALIGN='center' NOWRAP><FONT SIZE='-1'>%s</FONT></TD>
  <TD BGCOLOR='white' NOWRAP><FONT SIZE='-1'>%s</FONT></TD>
  <TD BGCOLOR='white' ALIGN='center' NOWRAP><FONT SIZE='-1'>%s</FONT></TD>
  <TD BGCOLOR='white' NOWRAP><FONT SIZE='-1'>%s</FONT></TD>
  <TD BGCOLOR='white' ALIGN='center' NOWRAP><FONT SIZE='-1'>%s</FONT></TD>
  <TD BGCOLOR='white' NOWRAP><FONT SIZE='-1'>%s</FONT></TD>
  <TD BGCOLOR='white' ALIGN='center' NOWRAP><FONT SIZE='-1'>%s</FONT></TD>
  <TD BGCOLOR='white' NOWRAP><FONT SIZE='-1'>%s</FONT></TD>
 </TR>
""" % (rec[0],
       rec[0],
       rec[1][:10],
       rec[2],
       rec[3],
       descSubstring,
       rec[5] and rec[5][:10] or "[Unassigned]",
       rec[6] and rec[6] or "----",
       rec[7] and rec[7][:10] or "[Unresolved]",
       rec[8] and rec[8] or "----")
except cdrdb.Error, info:
    cdrcgi.bail('Failure fetching query results: %s' % info[1][0])

body += """\
</TABLE>
<INPUT TYPE='checkbox' NAME='NextVer' %s>
Show enhancements for future releases
""" % flag

#----------------------------------------------------------------------
# Add the session key and send back the form.
#----------------------------------------------------------------------
cdrcgi.sendPage(header + body + "</BODY></HTML>")
