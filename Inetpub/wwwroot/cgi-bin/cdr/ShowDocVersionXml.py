#!/usr/bin/env python

# ---------------------------------------------------------------------
# Display the XML for a CDR document version.
# ---------------------------------------------------------------------

from sys import stdout
from cdrapi import db
from cdrcgi import bail, FieldStorage

# ---------------------------------------------------------------------
# Get the parameters from the request.
# ---------------------------------------------------------------------
fields = FieldStorage()
docId = fields.getvalue('id')
ver = fields.getvalue('ver')

# ---------------------------------------------------------------------
# Get the document version.
# ---------------------------------------------------------------------
cursor = db.connect(user='CdrGuest').cursor()
cursor.execute("""\
SELECT xml
  FROM doc_version
 WHERE id = ?
   AND num = ?""", (docId, ver))
row = cursor.fetchone()
if not row:
    bail("Version %s of document %s not found" % (ver, docId))

# ---------------------------------------------------------------------
# Send it.
# ---------------------------------------------------------------------
stdout.buffer.write(f"""\
Content-type: text/xml; charset=utf-8

{row.xml}""".encode('utf-8'))
