#----------------------------------------------------------------------
#
# $Id: DevTasks.py,v 1.3 2001-08-22 14:42:13 bkline Exp $
#
# Lists CDR development tasks.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2001/08/21 20:48:52  shines
# Added ability to sort by column headings
#
# Revision 1.1  2001/08/21 17:18:02  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, dbi, cdrdb

#----------------------------------------------------------------------
# Retrieve and display the user information.
#----------------------------------------------------------------------
title   = "CDR Development"
section = "Task List"
buttons = ["Refresh"]
#script  = "DumpParams.pl"
script  = "DevTasks.py"
header  = cdrcgi.header(title, title, section, script, buttons, numBreaks = 1)


#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
sortby    = fields and fields.getvalue("sortby") or ""

#----------------------------------------------------------------------
# Retrieve the information directly from the database.
#----------------------------------------------------------------------
orderby = sortby
orderlist = ['category', 'assigned_to', 'status DESC', 'id']
for item in orderlist:
    if item != sortby:
        orderby += orderby and ", "
        orderby += item

try:
    conn = cdrdb.connect()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])
cursor = conn.cursor()
query1  = """\
   SELECT id, description, assigned_to, status, category,est_complete,notes
     FROM dev_task
 ORDER BY %s
""" % orderby

query2 = """\
   SELECT status, COUNT(*)
     FROM dev_task
 GROUP BY status
 ORDER BY status DESC
"""
try:
    cursor.execute(query1)
    tasks = cursor.fetchall()
    cursor.execute(query2)
    summary = cursor.fetchall()

except cdrdb.Error, info:
    cdrcgi.bail('Database query failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Display the information in two tables.
#----------------------------------------------------------------------
body = """\
<TABLE BORDER='0' WIDTH='100%%' CELLSPACING='1' CELLPADDING='1'>
 <TR BGCOLOR='silver' VALIGN='top'>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Status</B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Count</B></FONT></TD>
 </TR>
"""
for line in summary:
    body += """\
 <TR>
  <TD BGCOLOR='white' ALIGN='center'><FONT SIZE='-1'><B>%s</B></FONT></TD>
  <TD BGCOLOR='white' ALIGN='center'><FONT SIZE='-1'><B>%d</B></FONT></TD>
 </TR>
""" % (line[0], line[1])

body += """\
</TABLE>
<BR>
<TABLE BORDER='0' WIDTH='100%%' CELLSPACING='1' CELLPADDING='1'>
 <TR BGCOLOR='silver' VALIGN='center'>
  <TD ALIGN='center'><FONT SIZE='-1'><B>&nbsp;#&nbsp;</B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Description</B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B><a
  href='DevTasks.py?sortby=assigned_to' >Assigned To</a></B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B><a
  href="DevTasks.py?sortby=status%20DESC">Status</a></B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B><a
  href="DevTasks.py?sortby=category" >Category</A></B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Done By</B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Notes</B></FONT></TD>
  </TR>
"""
for rec in tasks:
    body += """
 <TR>
  <TD BGCOLOR='white' VALIGN='top' ALIGN='right'><FONT SIZE='-1'>%d</FONT></TD>
  <TD BGCOLOR='white' VALIGN='top'><FONT SIZE='-1'>%s</FONT></TD>
  <TD BGCOLOR='white' VALIGN='top' NOWRAP><FONT SIZE='-1'>%s</FONT></TD>
  <TD BGCOLOR='white' VALIGN='top' NOWRAP><FONT SIZE='-1'>%s</FONT></TD>
  <TD BGCOLOR='white' VALIGN='top' ALIGN='center' NOWRAP><FONT SIZE='-1'>%s</FONT></TD>
   <TD BGCOLOR='white' VALIGN='top' ALIGN='center' NOWRAP><FONT 
   SIZE='-1'>%s</FONT></TD> 
   <TD BGCOLOR='white' VALIGN='top'><FONT SIZE='-1'>%s</FONT></TD>
   </TR>
""" % (rec[0],
       rec[1],
       rec[2],
       rec[3],
       rec[4],
       rec[5],
       rec[6])

body += "</TABLE>\n"

#----------------------------------------------------------------------
# Send back the table.
#----------------------------------------------------------------------
cdrcgi.sendPage(header + body + "</BODY></HTML>")
