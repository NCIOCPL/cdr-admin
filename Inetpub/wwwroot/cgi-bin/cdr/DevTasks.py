#----------------------------------------------------------------------
#
# $Id$
#
# Lists CDR development tasks.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb

#----------------------------------------------------------------------
# Retrieve and display the user information.
#----------------------------------------------------------------------
title   = "CDR Development"
section = "Task List"
buttons = ["Show Pending Tasks", "Show All Tasks"]
#script  = "DumpParams.pl"
script  = "DevTasks.py"
header  = cdrcgi.header(title, title, section, script, buttons, numBreaks = 1)


#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
sortby  = fields and fields.getvalue("sortby") or ""
action  = cdrcgi.getRequest(fields)
showAll = fields and fields.getvalue("showall") or None

#----------------------------------------------------------------------
# Retrieve the information directly from the database.
#----------------------------------------------------------------------
orderby = sortby
where   = "WHERE status NOT IN ('Complete', 'Abandoned')"
if showAll == 'Y' or action == "Show All Tasks":
    where = ""
    showAll = "showall=Y"
else:
    showAll = "showall=N"
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
    %s
 ORDER BY %s
""" % (where, orderby)

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
  <TD ALIGN='center'><FONT SIZE='-1'><B><a
  href="DevTasks.py?sortby=id&%s">&nbsp;#&nbsp;</a></B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Description</B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B><a
  href='DevTasks.py?sortby=assigned_to&%s'>Assigned To</a></B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B><a
  href="DevTasks.py?sortby=status%%20DESC&%s">Status</a></B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B><a
  href="DevTasks.py?sortby=category&%s" >Category</A></B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Done By</B></FONT></TD>
  <TD ALIGN='center'><FONT SIZE='-1'><B>Notes</B></FONT></TD>
  </TR>
""" % (showAll, showAll, showAll, showAll)
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
       rec[5] and rec[5][:10] or "&nbsp;No estimate&nbsp;",
       rec[6])

body += "</TABLE>\n"

#----------------------------------------------------------------------
# Send back the table.
#----------------------------------------------------------------------
cdrcgi.sendPage(header + body + "</BODY></HTML>")
