#----------------------------------------------------------------------
#
# $Id: GetSchema.py,v 1.2 2007-02-27 18:16:14 bkline Exp $
#
# Gets a schema document from the repository and returns it as a plain
# text file.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2006/05/04 14:57:04  bkline
# Show schema as text.
#
#----------------------------------------------------------------------
import cgi, cdrdb, cdrcgi, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
id      = fields and fields.getvalue("id")

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()

if id:
    cursor.execute("SELECT title, xml FROM document WHERE id = %s" % id)
    rows = cursor.fetchall()
    if not rows:
        cdrcgi.bail("Can't retrieve XML for document %s" % id)
    sys.stdout.write("""\
Content-type: text/plain
Content-disposition: attachment;filename=%s

%s""" % (rows[0][0],
         rows[0][1].encode('utf-8').replace('\r', '')))
    sys.exit(0)

cursor.execute("""\
    SELECT d.id, d.title
      FROM document d
      JOIN doc_type t
        ON t.id = d.doc_type
     WHERE t.name = 'Schema'
  ORDER BY d.title""")
html = [u"""\
<html>
 <head>
  <title>CDR Schemas</title>
  <style type='text/css'>
   body { font-family: Arial }
  </style>
 </head>
 <body>
  <h1>CDR Schemas</h1>"""]
for row in cursor.fetchall():
    line = (u"  <a href='GetSchema.py?id=%d'>%s</a><br />" %
            (row[0], cgi.escape(row[1])))
    html.append(line)
html.append(u"""\
 </body>
</html>
""")
cdrcgi.sendPage(u"\n".join(html))
