#----------------------------------------------------------------------
#
# $Id: ShowRawXml.py,v 1.1 2004-07-13 18:05:11 bkline Exp $
#
# Show unformatted XML; mostly useful for filters.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdrdb, cdrcgi

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
id      = fields and fields.getvalue("id") or cdrcgi.bail("No ID")

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("SELECT xml FROM document WHERE id = %s" % id)
rows = cursor.fetchall()
if not rows:
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
</html>""" % (id, id, cgi.escape(rows[0][0])))
