#!/usr/bin/env python

#----------------------------------------------------------------------
# Sends the raw XML for a document to a browser.  Useful with IE5.x,
# which by default shows a hierarchical tree display for the data.
#----------------------------------------------------------------------
from cgi import FieldStorage
from cdrcgi import sendPage, bail, DOCID
from cdrapi.docs import Doc
from cdrapi.users import Session

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
title   = "CDR Document XML"
fields  = FieldStorage()
docId   = fields.getvalue(DOCID) or bail("No Document", title)

#----------------------------------------------------------------------
# Filter the document's XML.
#----------------------------------------------------------------------
session = Session("guest")
doc = Doc(session, id=docId)
xml = doc.xml

#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
sendPage(xml, "xml")
