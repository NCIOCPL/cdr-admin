#----------------------------------------------------------------------
#
# $Id: TestStatus.py,v 1.1 2002-08-01 18:45:33 bkline Exp $
#
# Report on status of testing of enhancements and bug fixes.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb

#----------------------------------------------------------------------
# Start the page.
#----------------------------------------------------------------------
title = "Report on Status of Testing of CDR Enhancements and Fixes"
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>%s</title>
  <style type 'text/css'>
   body    { font-family: Arial, Helvetica, sans-serif }
   span.t1 { font-size: 14pt; font-weight: bold }
   span.t2 { font-size: 12pt; font-weight: bold }
   th      { font-size: 12pt; font-weight: bold }
   td      { font-size: 12pt; font-weight: normal }
  </style>
 </head>
 <body>
  <center>
   <span class='t1'>%s</span>
   <br />
   <br />
  </center>
""" % (title, title)
   
#----------------------------------------------------------------------
# Get the rows from the database.
#----------------------------------------------------------------------
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
    cursor.execute("""\
         SELECT module,
                status, 
                tester, 
                issue,
                implemented,
                description
           FROM cdr_test
       -- WHERE status <> 'P'
       ORDER BY module, status, implemented""")
    rows = cursor.fetchall()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Make sure we have some information to report on.
#----------------------------------------------------------------------
if not rows:
    cdrcgi.sendPage(html + """\
  <span class='t2'>No testing activity found to report.</span>
 </body>
</html>
""")

#----------------------------------------------------------------------
# Show the table.
#----------------------------------------------------------------------
html += """\
  <table border='1' cellspacing='0' cellpadding='2'>
   <tr>
    <th align='center'>Module</th>
    <th align='center'>Status</th>
    <th align='center' nowrap='1'>Test Contact</th>
    <th align='center'>Issue</th>
    <th align='center'>Implemented</th>
    <th align='center'>Description</th>
   </tr>
"""
for row in rows:
    if row[3] is None: row[3] = 0
    if row[1] == 'I': row[1] = 'Implemented'
    elif row[1] == 'T': row[1] = 'Tested/Approved'
    elif row[1] == 'P': row[1] = 'Promoted'
    html += """\
   <tr>
    <td align='center' valign='top'>%s</td>
    <td valign='top'>%s</td>
    <td align='center' valign='top'>%s</td>
    <td valign='top' align='center'>%03d</td>
    <td valign='top' align='center'>%s</td>
    <td valign='top'>%s</td>
   </tr>
""" % (row[0], row[1], row[2], row[3], row[4][:10], row[5])

print """\
Content-type: text/html

%s
  </table>
 </body>
</html>
""" % html
