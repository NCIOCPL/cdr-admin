#----------------------------------------------------------------------
#
# $Id: ProtocolAdminQcReport.py,v 1.2 2002-05-08 17:41:52 bkline Exp $
#
# Protocol Admin QC Report.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2002/04/22 13:54:06  bkline
# New QC reports.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
title   = "CDR Protocol Admin QC Report"
fields  = cgi.FieldStorage() or cdrcgi.bail("No Request Found", title)
session = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
docId   = fields.getvalue(cdrcgi.DOCID) or cdrcgi.bail("No Document", title)

#----------------------------------------------------------------------
# Map for finding the filters for this document type.
#----------------------------------------------------------------------
filters = [
    "name:Denormalization Filter (1/1): InScope Protocol",
    "name:InScope Protocol Administrative Report Filter"
]

#----------------------------------------------------------------------
# Filter the document.
#----------------------------------------------------------------------
doc = cdr.filterDoc(session, filters, docId = docId)
if type(doc) == type(()):
    doc = doc[0]

doc = cdrcgi.decode(doc)
doc = re.sub("@@DOCID@@", docId, doc)

#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
cdrcgi.sendPage(doc)
