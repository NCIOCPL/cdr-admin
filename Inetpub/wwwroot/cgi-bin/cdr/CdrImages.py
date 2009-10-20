#----------------------------------------------------------------------
#
# $Id$
#
# Page to show the users the list of image documents in the CDR.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, cdrcgi, xml.sax.saxutils

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
    SELECT d.id, d.title
      FROM document d
      JOIN doc_type t
        ON t.id = d.doc_type
     WHERE t.name = 'Media'
  ORDER BY d.id""")
html = u"""\
<html>
 <head>
  <title>CDR Images</title>
  <style type='text/css'>
   body { font-family: Arial }
   h1   { font-size: 15pt }
  </style>
 </head>
 <body>
  <h1>CDR Image Documents</h1>
"""
for row in cursor.fetchall():
    html += """\
  <a href='ShowRawImageXml.py?id=%d'>[CDR%d] %s</a><br />
""" % (row[0], row[0], xml.sax.saxutils.escape(row[1]))
html += """\
 </body>
</html>
"""
cdrcgi.sendPage(html)
