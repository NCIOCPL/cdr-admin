#----------------------------------------------------------------------
#
# $Id: pptest.py,v 1.1 2001-12-01 18:11:44 bkline Exp $
#
# Transform a CDR document using an XSL/T filter and send it back to 
# the browser.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, cdrdb, re

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
title   = "CDR Publish Preview"
session = cdr.login('rmk','***REDACTED***')
docId   = 'cdr190853'

#----------------------------------------------------------------------
# Map for finding the filters for a given document type.
#----------------------------------------------------------------------
filters = {
    'Summary':
        ["name:Summary Filter1",
         "name:Summary Filter2",
         "name:Summary Filter3",
         "name:Summary Filter4",
         "name:Summary Filter5",
         "name:Summary Filter6"],
    'Citation':     ["CDR0000272600"],
    'Organization': ["CDR0000266805"],
    'Person':       ["CDR0000266326"],
    'Term':         ["CDR0000272593"]
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
