#----------------------------------------------------------------------
#
# $Id: ProtocolHpQcReport.py,v 1.9 2009-05-06 17:25:34 venglisc Exp $
#
# Protocol Health Professional QC Report.
#
# $Log: not supported by cvs2svn $
# Revision 1.8  2003/04/11 18:20:16  pzhang
# Added Insertion/Deletion and Filter Set features.
#
# Revision 1.7  2002/06/13 13:19:53  bkline
# Plugged in Cheryl's new filter names.
#
# Revision 1.6  2002/05/30 17:06:41  bkline
# Corrected CVS log comment for previous version.
#
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
revLvls = fields.getvalue("revLevels")  or None

#----------------------------------------------------------------------
# Map for finding the filters for this document type.
#----------------------------------------------------------------------
filters = ["set:QC InScopeProtocol HP Set"]

#----------------------------------------------------------------------
# Filter the document.
#----------------------------------------------------------------------
filterParm = [['vendorOrQC', 'QC']]
if revLvls:
    filterParm.append(['revLevels', revLvls])  
doc = cdr.filterDoc(session, filters, docId = docId, parm = filterParm)

if type(doc) == type(()):
    doc = doc[0]

doc = cdrcgi.decode(doc)
doc = re.sub("@@DOCID@@", docId, doc)

# sendPage wants unicode
doc = doc.decode('utf-8')

#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
cdrcgi.sendPage(doc)
