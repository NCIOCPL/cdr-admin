#!/usr/bin/env python

# ---------------------------------------------------------------------
# Sends the raw XML for a document to a browser.  Useful with IE5.x,
# which by default shows a hierarchical tree display for the data.
# ---------------------------------------------------------------------
from cdrcgi import sendPage, bail, DOCID, FieldStorage
from cdrapi.docs import Doc
from cdrapi.users import Session

# ---------------------------------------------------------------------
# Get the parameters from the request.
# ---------------------------------------------------------------------
title = "CDR Document XML"
fields = FieldStorage()
error = "No Document"
id = fields.getvalue(DOCID) or fields.getvalue("id") or bail(error, title)

# ---------------------------------------------------------------------
# Filter the document's XML.
# ---------------------------------------------------------------------
session = Session("guest")
doc = Doc(session, id=id)
try:
    xml = doc.xml
except Exception as e:
    bail(f"Fetching XML for document {id}: {e}")

# ---------------------------------------------------------------------
# Send it.
# ---------------------------------------------------------------------
sendPage(xml, "xml")
