#----------------------------------------------------------------------
#
# $Id: AdHocQuery.py,v 1.1 2002-07-10 19:33:33 bkline Exp $
#
# Displays result set for SQL query.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
query   = fields and fields.getvalue('Query') or None
title   = "CDR Administration"
section = "Reports"
SUBMENU = "Reports Menu"
buttons = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
header  = cdrcgi.header(title, title, section, "AdHocQuery.py", buttons)

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == SUBMENU:
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if action == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Request the query.
#----------------------------------------------------------------------
if not query:
    form = """\
    <INPUT TYPE='hidden' NAME='%s' VALUE='%s'>
    <b>Enter SQL query:</b><br>
    <textarea name='Query' rows='20' cols='80'>
   SELECT d.id,
          d.title
     FROM document d
     JOIN doc_type t
       ON t.id = d.doc_type
    WHERE t.name = 'Filter'
 ORDER BY d.title
     </textarea>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form + "</FORM></BODY></HTML>")

#----------------------------------------------------------------------
# Create the report.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
    cursor.execute(query)
    if not cursor.description:
        cdrcgi.bail('No result set returned')
    html = """\
<html>
 <head>
  <title>Ad Hoc Query</title>
 </head>
 <body>
  <pre>
%s
  </pre>
  <table border='1' cellspacing='0' cellpadding='1'>
   <tr>
""" % query.replace("\r", "").rstrip()
    for col in cursor.description:
        html += """\
    <th align='center'>%s</th>
""" % (col[0] or "-")
    html += """\
   </tr>
"""
    row = cursor.fetchone()
    while row:
        html += """\
   <tr>
"""
        for col in row:
            if col is None: col = "NULL"
            html += """\
    <td valign='top'>%s</td>
""" % col
        html += """\
   </tr>
"""
        row = cursor.fetchone()
    html += """\
  </table>
 </body>
</html>
"""

except cdrdb.Error, info:
    cdrcgi.bail('Database failure: %s' % info[1][0])
cdrcgi.sendPage(cdrcgi.unicodeToLatin1(html))
