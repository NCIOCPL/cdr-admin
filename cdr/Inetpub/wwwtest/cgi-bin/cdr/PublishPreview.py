#----------------------------------------------------------------------
#
# $Id: PublishPreview.py,v 1.12 2002-08-29 12:32:08 bkline Exp $
#
# Transform a CDR document using an XSL/T filter and send it back to 
# the browser.
#
# $Log: not supported by cvs2svn $
# Revision 1.11  2002/05/30 17:06:41  bkline
# Corrected CVS log comment for previous version.
#
# Revision 1.10  2002/05/30 17:01:06  bkline
# New protocol filters from Cheryl.
#
# Revision 1.9  2002/05/08 17:41:53  bkline
# Updated to reflect Volker's new filter names.
#
# Revision 1.8  2002/04/18 21:46:59  bkline
# Plugged in some additional filters from Cheryl.
#
# Revision 1.7  2002/04/12 19:57:20  bkline
# Installed new filters.
#
# Revision 1.6  2002/04/11 19:41:48  bkline
# Plugged in some new filters.
#
# Revision 1.5  2002/04/11 14:07:49  bkline
# Added denormalization filter for Organization documents.
#
# Revision 1.4  2002/04/10 20:08:45  bkline
# Added denormalizing filter for Person display.
#
# Revision 1.3  2002/01/22 21:31:41  bkline
# Added filter for Protocols.
#
# Revision 1.2  2001/12/24 23:18:15  bkline
# Replaced document IDs with filter names.
#
# Revision 1.1  2001/12/01 18:11:44  bkline
# Initial revision
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re, cdr2cg

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
title   = "CDR Publish Preview"
fields  = cgi.FieldStorage() or cdrcgi.bail("No Request Found", title)
session = cdrcgi.getSession(fields) or cdrcgi.bail("Not logged in")
docId   = fields.getvalue(cdrcgi.DOCID) or cdrcgi.bail("No Document", title)
flavor  = fields.getvalue("Flavor") or None

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
         "name:Vendor Filter: Summary"],
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
         "name:Vendor Filter: InScopeProtocol"],
    'Term':             
        ["name:Denormalization Filter (1/1): Terminology",
         "name:Terminology QC Report Filter"]
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
if not flavor:
    if docType == "Summary": flavor = "summary"
    elif docType == "InScopeProtocol": flavor = "protocol_hp"
    else: cdrcgi.bail(
        "Publish preview only available for Summary and Protocol documents")

#----------------------------------------------------------------------
# Filter the document.
#----------------------------------------------------------------------
if not filters.has_key(docType):
    cdrcgi.bail("Don't have filters set up for %s documents yet" % docType)
doc = cdr.filterDoc(session, filters[docType], docId = docId)
if type(doc) == type(()):
    doc = doc[0]
pattern1 = re.compile("<\?xml[^?]+\?>", re.DOTALL)
pattern2 = re.compile("<!DOCTYPE[^>]+>", re.DOTALL)
doc = pattern1.sub("", doc)
doc = pattern2.sub("", doc)
#cdrcgi.bail("flavor=%s doc=%s" % (flavor, doc))
try:
    resp = cdr2cg.pubPreview(doc, flavor)
except:
    cdrcgi.bail("Preview formatting failure")

#doc = cdrcgi.decode(doc)
#doc = re.sub("@@DOCID@@", docId, doc)

#----------------------------------------------------------------------
# Show it.
#----------------------------------------------------------------------
cdrcgi.sendPage("""\
<html>
 <head>
  <title>Publish Preview for CDR%010d</title>
 </head>
 <body>
  %s
 </body>
</html>""" % (intId, resp.xmlResult))
