#----------------------------------------------------------------------
#
# $Id: QcReport.py,v 1.3 2002-05-08 17:41:53 bkline Exp $
#
# Transform a CDR document using a QC XSL/T filter and send it back to 
# the browser.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2002/05/03 20:30:22  bkline
# New filters and filter names.
#
# Revision 1.1  2002/04/22 13:54:07  bkline
# New QC reports.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
title   = "CDR QC Report"
fields  = cgi.FieldStorage() or cdrcgi.bail("No Request Found", title)
session = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
docId   = fields.getvalue(cdrcgi.DOCID) or cdrcgi.bail("No Document", title)

#----------------------------------------------------------------------
# Map for finding the filters for a given document type.
#----------------------------------------------------------------------
filters = {
    'Summary':
        ["name:Denormalization Filter (1/5): Summary",
         "name:Denormalization Filter (2/5): Summary",
         "name:Denormalization Filter (3/5): Summary",
         "name:Denormalization Filter (4/5): Summary",
         "name:Denormalization Filter (5/5): Summary",
         "name:Health Professional Summary Report"],
    'GlossaryTerm':         
        ["name:Glossary Term QC Report Filter"],
    'Citation':         
        ["name:Citation QC Report"],
    'Organization':     
        ["name:Denormalization Filter (1/1): Organization",
         "name:Organization QC Report Filter"],
    'Person':           
        ["name:Denormalization Filter (1/1): Person",
         "name:Person QC Report Filter"],
    'InScopeProtocol':  
        ["name:Denormalization Filter (1/1): InScope Protocol",
         "name:Create InScope Protocol XML for Full Protocol QC Report",
         "name:InScope Protocol Full QC Report"],
    'Term':             
        ["name:Denormalization Filter (1/1): Terminology",
         "name:Terminology QC Report Filter"],
    'MiscellaneousDocument':
        ["name:Miscellaneous Document Report Filter"]
}

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Determine the document type.
#----------------------------------------------------------------------
try:
    digits = re.sub('[^\d]+', '', docId)
    intId  = int(digits)
    cursor.execute("""\
        SELECT name
          FROM doc_type
          JOIN document
            ON document.doc_type = doc_type.id
         WHERE document.id = ?""", (intId,))
    row = cursor.fetchone()
    if not row:
        cdrcgi.bail("Unable to find document type for %s" % docId)
    docType = row[0]
except cdrdb.Error, info:    
        cdrcgi.bail('Unable to find document type for %s: %s' % (docId, 
                                                                 info[1][0]))

#----------------------------------------------------------------------
# Filter the document.
#----------------------------------------------------------------------
if not filters.has_key(docType):
    cdrcgi.bail("Don't have filters set up for %s documents yet" % docType)
doc = cdr.filterDoc(session, filters[docType], docId = docId)
if type(doc) == type(()):
    doc = doc[0]

doc = cdrcgi.decode(doc)
doc = re.sub("@@DOCID@@", docId, doc)

#----------------------------------------------------------------------
# Send it.
#----------------------------------------------------------------------
cdrcgi.sendPage(doc)
