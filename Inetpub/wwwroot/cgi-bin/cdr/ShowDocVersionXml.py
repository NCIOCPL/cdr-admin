#----------------------------------------------------------------------
# Display the XML for a CDR document version.
#----------------------------------------------------------------------
import cgi, cdrdb, cdrcgi

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
docId   = fields.getvalue('id')
ver     = fields.getvalue('ver')

#----------------------------------------------------------------------
# Get the document version.
#----------------------------------------------------------------------
cursor = cdrdb.connect('CdrGuest').cursor()
cursor.execute("""\
SELECT xml
  FROM doc_version
 WHERE id = ?
   AND num = ?""", (docId, ver))
rows = cursor.fetchall()
if not rows:
    cdrcgi.bail("Version %s of document %s not found" % (ver, docId))

#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
docXml = rows[0][0]
print("Content-type: text/xml; charset=utf-8\n\n" + docXml.encode('utf-8'))
