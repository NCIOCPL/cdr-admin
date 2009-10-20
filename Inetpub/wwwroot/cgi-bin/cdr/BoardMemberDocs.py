#----------------------------------------------------------------------
#
# $Id$
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, cdrcgi

conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
cursor.execute("""\
    SELECT d.id, d.title
      FROM document d
      JOIN doc_type t
        ON t.id = d.doc_type
     WHERE t.name = 'PDQBoardMemberInfo'
  ORDER BY d.title""")
html = """\
<html>
 <head>
  <title>PDQ Board Member Documents</title>
 </head>
 <body>
  <h1>Board Member Docs</h1>
"""
for row in cursor.fetchall():
    html += """\
  <a href='ShowDocXml.py?DocId=CDR%010d'>%s</a><br>
""" % (row[0], row[1])
cdrcgi.sendPage(html + """\
 </body>
</html>
""")
