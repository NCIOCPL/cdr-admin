#!/usr/bin/env python

# ---------------------------------------------------------------------
# Sends the raw XML for a document to a browser.  Useful with IE5.x,
# which by default shows a hierarchical tree display for the data.
# ---------------------------------------------------------------------
from cdrcgi import Controller, FieldStorage
from cdrapi.docs import Doc
from cdrapi.users import Session

# ---------------------------------------------------------------------
# Get the parameters from the request.
# ---------------------------------------------------------------------
title = "CDR Document XML"
fields = FieldStorage()
error = "No document specified for XML viewer."
id = fields.getvalue(Controller.DOCID) or fields.getvalue("id")
if not id:
    Controller.bail(error)

# ---------------------------------------------------------------------
# Filter the document's XML.
# ---------------------------------------------------------------------
session = Session("guest")
doc = Doc(session, id=id)
try:
    xml = doc.xml
except Exception as e:
    Controller.bail(f"Fetching XML for document {id}: {e}")

# ---------------------------------------------------------------------
# Send it.
# ---------------------------------------------------------------------
Controller.send_page(xml, text_type="xml")
