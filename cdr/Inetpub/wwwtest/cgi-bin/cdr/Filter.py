#----------------------------------------------------------------------
#
# $Id: Filter.py,v 1.2 2001-04-08 22:56:03 bkline Exp $
#
# Transform a CDR document using an XSL/T filter and send it back to 
# the browser.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2001/03/27 21:19:09  bkline
# Initial revision
#
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
title   = "CDR Formatting"
fields  = cgi.FieldStorage() or cdrcgi.bail("No Request Found", title)
session = cdr.login('rmk', '***REDACTED***') or cdrcgi.bail("Not Authorized", title)
docId   = fields.getvalue(cdrcgi.DOCID) or cdrcgi.bail("No Document", title)
filtId  = fields.getvalue(cdrcgi.FILTER) or cdrcgi.bail("No Filter", title)

#----------------------------------------------------------------------
# Filter the document.
#----------------------------------------------------------------------
doc = cdrcgi.decode(cdr.filterDoc(session, filtId, docId = docId))
doc = re.sub("@@DOCID@@", docId, doc)

#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
cdrcgi.sendPage(doc)
