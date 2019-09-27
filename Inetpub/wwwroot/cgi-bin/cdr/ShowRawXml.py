#----------------------------------------------------------------------
# Show unformatted XML.
#----------------------------------------------------------------------
import cgi, cdrcgi
from cdrapi import db
from html import escape

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
id      = fields and fields.getvalue("id") or cdrcgi.bail("No ID")

conn = db.connect(user='CdrGuest')
cursor = conn.cursor()
cursor.execute("SELECT xml FROM document WHERE id = %s" % id)
row = cursor.fetchone()
if not row:
    cdrcgi.bail("Can't retrieve XML for document %s" % id)
cdrcgi.sendPage("""\
<html>
 <head>
  <title>CDR Document %s</title>
  <style type='text/css'>
   body { font-family: Arial; }
   pre  { color: blue; }
  </style>
 </head>
 <body>
  <h1>CDR Document %s</h1>
  <pre>%s</pre>
 </body>
</html>""" % (id, id, escape(row.xml)))
