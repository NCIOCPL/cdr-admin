#----------------------------------------------------------------------
#
# $Id: AuditTrail.py,v 1.1 2003-02-24 21:17:38 bkline Exp $
#
# Audit Trail report.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
#!/usr/bin/python

import sys, cgi, time, cdrcgi, cdrdb, re

fields = cgi.FieldStorage()
docId  = fields and fields.getvalue("id") or ""
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
curs = conn.cursor()
try:
    curs.execute("""\
      SELECT title
        FROM document
       WHERE id = ?""", id)
    row = curs.fetchone()
    if not row:
        cdrcgi.bail("Can't find document %d" % id)
    title = cgi.escape(row[0])
except:
    cdrcgi.bail("Database failure retrieving title for document %d" % id)
try:
    curs.execute("""\
   SELECT TOP 50 audit_trail.dt, usr.fullname, action.name
            FROM audit_trail
            JOIN usr
              ON usr.id = audit_trail.usr
            JOIN action
              ON action.id = audit_trail.action
           WHERE audit_trail.document = ?
        ORDER BY audit_trail.dt DESC""", id)
    rows = curs.fetchall()
except:
    cdrcgi.bail("Failure retrieving rows from CDR Audit Trail")
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
for row in rows:
    when = cdrdb.strftime("%m/%d/%Y %I:%M:%S %p", row[0])
    who  = row[1]
    what = row[2]
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
""" % (when, who, what)
cdrcgi.sendPage(html +  """\
  </table>
 </body>
</html>""")
