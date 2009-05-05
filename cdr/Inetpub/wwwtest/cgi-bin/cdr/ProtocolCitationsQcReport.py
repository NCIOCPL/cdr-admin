#----------------------------------------------------------------------
#
# $Id: ProtocolCitationsQcReport.py,v 1.5 2009-05-05 21:58:41 ameyer Exp $
#
# Protocol Citations QC Report.
#
# $Log: not supported by cvs2svn $
# Revision 1.4  2003/04/11 18:30:56  pzhang
# Added Insertion/Deletion and Filter Set features.
#
# Revision 1.3  2002/05/08 17:41:52  bkline
# Updated to reflect Volker's new filter names.
#
# Revision 1.2  2002/05/03 20:27:33  bkline
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
title   = "CDR Protocol Citations QC Report"
fields  = cgi.FieldStorage() or cdrcgi.bail("No Request Found", title)
session = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
docId   = fields.getvalue(cdrcgi.DOCID) or cdrcgi.bail("No Document", title)
revLvls = fields.getvalue("revLevels")  or None

#----------------------------------------------------------------------
# Map for finding the filters for this document type.
#----------------------------------------------------------------------
filters = ["set:QC InScopeProtocol Citation Set"]

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
