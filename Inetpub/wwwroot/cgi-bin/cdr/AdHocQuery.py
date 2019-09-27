#----------------------------------------------------------------------
# Displays result set for SQL query.
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string
from cdrapi import db
from html import escape as html_escape

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
action  = cdrcgi.getRequest(fields)
query   = fields and fields.getvalue('Query') or None
timeout = fields and fields.getvalue('TimeOut') or '20'
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
    <input type='hidden' name='%s' value='%s'>
    <b>Enter SQL query:</b><br>
    <textarea name='Query' rows='20' cols='80'>
/*
   Modify t.name (Term) to match your document type and
   change "%%<MenuInformation%%" to match your string such
   as "%%<Phone%%Public%%" for Person, in the documents of
   the given type. Remember to use %% as the wildcard.
*/
SELECT TOP 10 d.id
  FROM document d
  JOIN doc_type t
    ON d.doc_type = t.id
 WHERE d.xml like '%%<MenuInformation%%'
   AND t.name = 'Term'

     </textarea>
     <br><b>Enter timeout in seconds:</b><br>
    <input type='text' name='TimeOut' value='20'>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form + "</form></body></html>")

#----------------------------------------------------------------------
# Create the report.
#----------------------------------------------------------------------
try:
    conn = db.connect(user='CdrGuest', timeout=int(timeout))
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
  <table border='1' cellspacing='0' cellpadding='3'>
   <tr>
""" % (query.replace("\r", "").rstrip()).replace("<", "&lt;")
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
            elif col == 0: col = "0"
            elif not col: col = "&nbsp;"
            elif isinstance(col, str): col = html_escape(col)
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

except Exception as e:
    cdrcgi.bail('Database failure: %s' % e)
cdrcgi.sendPage("".join(html))
