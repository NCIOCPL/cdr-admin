#----------------------------------------------------------------------
#
# $Id: ProtocolHpQcReport.py,v 1.6 2002-05-30 17:06:41 bkline Exp $
#
# Protocol Health Professional QC Report.
#
# $Log: not supported by cvs2svn $
# Revision 1.5  2002/05/30 17:01:06  bkline
# New protocol filters from Cheryl.
#
# Revision 1.4  2002/05/17 21:15:40  bkline
# Plugged in new filters from Cheryl.
#
# Revision 1.3  2002/05/08 17:41:52  bkline
# Updated to reflect Volker's new filter names.
#
# Revision 1.2  2002/05/03 20:27:32  bkline
# Changed filter name to match name change made by Cheryl.
#
# Revision 1.1  2002/04/22 13:54:06  bkline
# New QC reports.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
title   = "CDR Protocol Health Professional QC Report"
fields  = cgi.FieldStorage() or cdrcgi.bail("No Request Found", title)
session = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
docId   = fields.getvalue(cdrcgi.DOCID) or cdrcgi.bail("No Document", title)

#----------------------------------------------------------------------
# Map for finding the filters for this document type.
#----------------------------------------------------------------------
filters = [
    "name:Denormalization Filter (1/1): InScope Protocol",
    "name:XML for Professional Protocol QC Report",
    "name:Health Professional Protocol QC Content Report"
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
