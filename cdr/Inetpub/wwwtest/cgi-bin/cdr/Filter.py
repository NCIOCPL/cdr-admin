#----------------------------------------------------------------------
#
# $Id: Filter.py,v 1.4 2002-07-15 20:18:03 bkline Exp $
#
# Transform a CDR document using an XSL/T filter and send it back to 
# the browser.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2002/01/23 18:50:22  mruben
# allow up to 8 filters
#
# Revision 1.2  2001/04/08 22:56:03  bkline
# Added Unicode mapping; switched around arguments to filterDoc call.
#
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
filtId0 = fields.getvalue(cdrcgi.FILTER) or cdrcgi.bail("No Filter", title)
filtId  = [filtId0,
           fields.getvalue(cdrcgi.FILTER + "1", ""),
           fields.getvalue(cdrcgi.FILTER + "2", ""),
           fields.getvalue(cdrcgi.FILTER + "3", ""),
           fields.getvalue(cdrcgi.FILTER + "4", ""),
           fields.getvalue(cdrcgi.FILTER + "5", ""),
           fields.getvalue(cdrcgi.FILTER + "6", ""),
           fields.getvalue(cdrcgi.FILTER + "7", "")]

#----------------------------------------------------------------------
# Filter the document.
#----------------------------------------------------------------------
doc = cdr.filterDoc(session, filtId, docId = docId)
if type(doc) == type(()):
  doc = doc[0]

doc = cdrcgi.decode(doc)
doc = re.sub("@@DOCID@@", docId, doc)

#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
textType = 'html'
if doc.find("<?xml") != -1:
    textType = 'xml'
open('foo.txt', 'wb').write(doc)
cdrcgi.sendPage(doc, textType)
