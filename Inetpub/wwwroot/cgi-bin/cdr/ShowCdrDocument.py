#----------------------------------------------------------------------
#
# $Id$
#
# CDR Document Viewer
#
#----------------------------------------------------------------------
import cdr, cgi, cdrcgi, cdrdb

fields  = cgi.FieldStorage()
docId   = fields.getvalue('id')
title   = fields.getvalue('title')
raw     = fields.getvalue('raw')
docType = fields.getvalue('doctype')
error   = u""
conn    = cdrdb.connect('CdrGuest')
cursor  = conn.cursor()

if title:
    if docType:
        cursor.execute("""\
            SELECT d.id, d.title, t.name
              FROM document d
              JOIN doc_type t
                ON t.id = d.doc_type
             WHERE d.title LIKE ?
               AND t.name = ?""", (title, docType))
    else:
        cursor.execute("""\
            SELECT d.id, d.title, t.name
              FROM document d
              JOIN doc_type t
                ON t.id = d.doc_type
             WHERE d.title LIKE ?""", title)
    rows = cursor.fetchall()
    if len(rows) < 1:
        error = u"No documents found"
    elif len(rows) == 1:
        docId = rows[0][0]
    else:
        html = [u"""\
<html>
 <head>
  <title>CDR Document Search Results</title>
  <style type='text/css'>
   ol { margin-left: 25px; }
  </style>
 </head>
 <body>
  <h1>CDR Document Search Results (%d Documents)</h1>
  <ol>
""" % len(rows)]
        for docId, docTitle, docType in rows:
            url = u"ShowCdrDocument.py?id=%s" % docId
            raw = url + "&raw=1"
            html.append(u"""\
   <li><a href='%s' target='_'>%s [%s] %s</a> (<a href='%s' target='_'>Raw</a>)
""" % (url, docId, docType, docTitle, raw))
        html.append(u"""\
  </ol>
 </body>
</html>
""")
        cdrcgi.sendPage(u"".join(html))
        
if docId:
    doc = cdr.getDoc('guest', docId, getObject = True)
    if raw:
        html = u"""\
<html>
 <head>
  <title>CDR%s</title>
 </head>
 <body>
  <pre>%s</pre>
 </body>
</head>
""" % (docId, cgi.escape(unicode(doc.xml, 'utf-8')))
        cdrcgi.sendPage(html)
    else:
        cdrcgi.sendPage(unicode(doc.xml, 'utf-8'), 'xml')

page = [u"""\
<html>
 <head>
  <title>CDR Document Viewer</title>
 </head>
 <body>
  <h1>CDR Document Viewer</h1>
  <p id='error'>%s</p>
  <form action='ShowCdrDocument.py' method='POST'>
   <table>
    <tr><th>CDR ID:&nbsp;</th><td><input name='id' /></td></th>
    <tr><th>Title:&nbsp;</th><td><input name='title' /></td></th>
    <tr>
     <th>Doc Type:&nbsp;</th>
     <td>
      <select name='doctype'>
       <option value='' selected='selected'>Any</option>
""" % error]
cursor.execute("""\
    SELECT name
      FROM doc_type
     WHERE xml_schema IS NOT NULL
       AND active = 'Y'
  ORDER BY name""")
for row in cursor.fetchall():
    page.append(u"""\
       <option>%s</option>
""" % row[0])
page.append(u"""\
      </select>
     </td>
    </th>
    <tr>
     <th>Show Raw XML?&nbsp;</th>
     <td><input type='checkbox' name='raw'%s /></td>
    </tr>
   </table>
   <br />
   <input type='submit' />
  </form>
 </body>
</html>
""" % (raw and u" checked='checked'" or u""))
cdrcgi.sendPage(u"".join(page))
