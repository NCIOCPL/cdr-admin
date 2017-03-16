#!/usr/bin/python
#----------------------------------------------------------------------
# Audit Trail report (new report requested by Lakshmi).
#----------------------------------------------------------------------

import sys, cgi, time, cdrcgi, cdrdb, re

fields = cgi.FieldStorage()
docId  = fields.getvalue("id") or ""
nRows  = fields.getvalue("rows") or "150"
if not docId:
    cdrcgi.bail("Missing required id parameter")
try:
    digits = re.sub(r"[^\d]", "", docId)
    id = int(digits)
except:
    cdrcgi.bail("Invalid id value: %s" % docId)
try:
    conn = cdrdb.connect('CdrGuest')
except:
    cdrcgi.bail("Unable to connect to CDR database")
cursor = conn.cursor()
try:
    cursor.execute("""\
      SELECT title
        FROM document
       WHERE id = ?""", id)
    row = cursor.fetchone()
    if not row:
        cdrcgi.bail("Can't find document %d" % id)
    title = cgi.escape(row[0])
except:
    cdrcgi.bail("Database failure retrieving title for document %d" % id)
try:
    cursor.execute("""\
        CREATE TABLE #audit
                 (dt DATETIME,
                 usr VARCHAR(80),
              action VARCHAR(255))""")
    cursor.execute("""\
        INSERT INTO #audit
             SELECT audit_trail.dt, usr.fullname, action.name
               FROM audit_trail
               JOIN usr
                 ON usr.id = audit_trail.usr
               JOIN action
                 ON action.id = audit_trail.action
              WHERE audit_trail.document = ?""", id, timeout = 300)
    cursor.execute("""\
        INSERT INTO #audit
             SELECT c.dt_out, u.fullname, 'LOCK'
               FROM checkout c
               JOIN usr u
                 ON u.id = c.usr
              WHERE c.id = ?""", id, timeout = 300)
    cursor.execute("""\
    SELECT TOP %s CONVERT(VARCHAR(23), dt, 121), usr, action
             FROM #audit
         ORDER BY dt DESC""" % nRows)
    rows = cursor.fetchall()
except:
    cdrcgi.bail("Failure retrieving rows for Audit Trail")
html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Audit Trail for %d</title>
  <basefont face='Arial, Helvetica, sans-serif'>
 </head>
 <body>
  <b>
   <font size='4'>Audit Trail for %d</font>
  </b>
  <p>%s</p>
  <table border='1' width='100%%' cellspacing='0' cellpadding='2'>
   <tr>
    <td align='center'>
     <font size='3'>
      <b>DATE TIME</b>
     </font>
    </td>
    <td align='center'>
     <font size='3'>
      <b>USER NAME</b>
     </font>
    </td>
    <td align='center'>
     <font size='3'>
      <b>ACTION</b>
     </font>
    </td>
   </tr>
""" % (id, id, title)
for when, who, what in rows:
    html += """\
   <tr>
    <td>
     <font size='3'>%s</font>
    </td>
    <td>
     <font size='3'>%s</font>
    </td>
    <td>
     <font size='3'>%s</font>
    </td>
   </tr>
""" % (when, who, cgi.escape(what))
cdrcgi.sendPage(html +  """\
  </table>
 </body>
</html>""")
