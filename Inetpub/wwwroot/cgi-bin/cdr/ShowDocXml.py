#----------------------------------------------------------------------
# Sends the raw XML for a document to a browser.  Useful with IE5.x,
# which by default shows a hierarchical tree display for the data.
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
title   = "CDR Document XML"
fields  = cgi.FieldStorage() or cdrcgi.bail("No Request Found", title)
docId   = fields.getvalue(cdrcgi.DOCID) or cdrcgi.bail("No Document", title)

#----------------------------------------------------------------------
# Filter the document.
#----------------------------------------------------------------------
doc = cdrcgi.decode(cdr.getDoc('guest', docId))

#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
expr = re.compile("<!\[CDATA\[(.*)\]\]>", re.DOTALL)
doc  = expr.findall(doc)[0]
print "Content-type: text/xml\n\n" + doc
