#----------------------------------------------------------------------
#
# $Id: PublishPreview.py,v 1.28 2006-07-11 20:50:58 venglisc Exp $
#
# Transform a CDR document using an XSL/T filter and send it back to 
# the browser.
#
# $Log: not supported by cvs2svn $
# Revision 1.27  2005/12/08 16:01:32  venglisc
# Modified the program to handle an additional parameter.  With this new
# version parameter we are able to display a specific version of a document
# including the cwd (current working document).
#
# Revision 1.26  2005/04/21 21:30:06  venglisc
# Modified to allow running GlossaryTerm Publish Preview reports. (Bug 1531)
#
# Revision 1.25  2005/02/15 13:07:13  bkline
# Added ability to override default for host from which to pull the
# stylesheet.
#
# Revision 1.24  2004/12/28 16:20:55  bkline
# Added cgHost parameter.
#
# Revision 1.23  2004/05/27 20:50:23  bkline
# Replaced stylesheets as requested by Jay (email message).
#
# Revision 1.22  2003/12/16 15:47:14  bkline
# Added debugging support and CTGovProtocol support.
#
# Revision 1.21  2003/11/25 12:47:41  bkline
# Added support for testing from command line.
#
# Revision 1.20  2003/08/25 20:31:44  bkline
# Eliminated obsolete lists of filters (replaced by named filter sets).
#
# Revision 1.19  2002/11/15 18:36:23  bkline
# Fixed typo (InScopePrototocol).
#
# Revision 1.18  2002/11/13 20:33:37  bkline
# Plugged in filter sets.
#
# Revision 1.17  2002/11/05 14:00:29  bkline
# Updated filter lists from publication control document.
#
# Revision 1.16  2002/10/31 02:06:06  bkline
# Changed www.cancer.gov to stage.cancer.gov for css url.
#
# Revision 1.15  2002/10/28 13:59:11  bkline
# Added hook to debuglevel.  Added link to Cancer.gov stylesheet.
#
# Revision 1.14  2002/10/24 15:38:08  bkline
# Implemented change request from issue #478 to use last publishable
# version instead of current working version.
#
# Revision 1.13  2002/10/22 17:47:05  bkline
# Added, then commented out, the debugging flag for cdr2cg.
#
# Revision 1.12  2002/08/29 12:32:08  bkline
# Hooked up with Cancer.gov.
#
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
import cgi, cdr, cdrcgi, cdrdb, re, cdr2cg, sys, time

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
title   = "CDR Publish Preview"
fields  = cgi.FieldStorage() or None

if not fields:
    session    = 'guest'
    docId      = sys.argv[1]
    docVersion = len(sys.argv) > 2 and sys.argv[2] or None
    dbgLog     = len(sys.argv) > 3 and sys.argv[3] or None
    flavor     = len(sys.argv) > 4 and sys.argv[4] or None
    cgHost     = len(sys.argv) > 5 and sys.argv[5] or None
    ssHost     = len(sys.argv) > 6 and sys.argv[6] or 'www.cancer.gov'
    monitor    = 1
else:
    session    = cdrcgi.getSession(fields)   or cdrcgi.bail("Not logged in")
    docId      = fields.getvalue(cdrcgi.DOCID) or cdrcgi.bail("No Document",
                                                           title)
    docVersion = fields.getvalue("Version")  or None
    flavor     = fields.getvalue("Flavor")   or None
    dbgLog     = fields.getvalue("DebugLog") or None
    cgHost     = fields.getvalue("cgHost")   or None
    ssHost     = fields.getvalue("ssHost")   or 'www.cancer.gov'
    monitor    = 0

#----------------------------------------------------------------------
# Point to a different host if requested.
#----------------------------------------------------------------------
if cgHost:
    cdr2cg.host = cgHost

#----------------------------------------------------------------------
# Debugging output.
#----------------------------------------------------------------------
def showProgress(progress):
    if monitor:
        sys.stderr.write("[%s] %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"),
                                        progress))
showProgress("Started...")

#----------------------------------------------------------------------
# Map for finding the filters for a given document type.
# Need to enter (Document type : [filter set])
#----------------------------------------------------------------------
filterSets = {
    'CTGovProtocol'         : ['set:Vendor CTGovProtocol Set'],
    'DrugInformationSummary': ['set:Vendor DrugInfoSummary Set'], 
    'GlossaryTerm'          : ['set:Vendor GlossaryTerm Set'], 
    'InScopeProtocol'       : ['set:Vendor InScopeProtocol Set'],
    'Summary'               : ['set:Vendor Summary Set']
}

#----------------------------------------------------------------------
# Set up a database connection and cursor.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
    showProgress("Connected to CDR database...")
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Determine the document type and version.
#----------------------------------------------------------------------
# We are covering three situations here.
# a) No Version parameter is given
#    The original behavior will be performed, namely to display the 
#    latest publishable version of the document if it exists.
# b) The Version parameter is set to 'cwd'
#    The current working document will be displayed
# c) The Version parameter is set and it is not 'cwd'
#    This means that the specified version is to be displayed in the
#    publish preview display.
# -------------------------------------------------------------------
try:
    digits = re.sub('[^\d]+', '', docId)
    intId  = int(digits)

    # We need to select the document type
    # -----------------------------------
    cursor.execute("""\
        SELECT doc_type.name
          FROM doc_type
          JOIN document
            ON document.doc_type = doc_type.id
         WHERE document.id = ?""", (intId,))
    
    row = cursor.fetchone()
    if not row:
        cdrcgi.bail("Unable to find specified document %s" % docId)

    docType = row[0]

    # Next we need to identify the version to be displayed
    # ----------------------------------------------------
    if not docVersion:
        cursor.execute("""\
        SELECT max(doc_version.num)
          FROM doc_version
         WHERE doc_version.id = ?
           AND doc_version.publishable = 'Y' """, (intId,))

        row = cursor.fetchone()
        if not row:
            cdrcgi.bail("Unable to find publishable version for %s" % docId)
        docVer = row[0]
    elif docVersion != 'cwd':
        cursor.execute("""\
        SELECT doc_version.num
          FROM doc_version
         WHERE doc_version.id = ?
           AND doc_version.num = ? """, (intId, docVersion,))

        row = cursor.fetchone()
        if not row:
            cdrcgi.bail("Unable to find specified version %s for %s" % (
                                                            docVersion, docId))
        docVer = row[0]
    else:
        docVer = None

except cdrdb.Error, info:    
        cdrcgi.bail('Failure finding specified version for %s: %s' % (docId, 
                                                                 info[1][0]))
showProgress("Fetched document type: %s..." % row[0])

if not flavor:
    if docType == "Summary":                  flavor = "summary"
    elif docType == "DrugInformationSummary": flavor = "druginfosummary"
    elif docType == "InScopeProtocol":        flavor = "protocol_hp"
    elif docType == "CTGovProtocol":          flavor = "CTGovProtocol_HP"
    elif docType == "GlossaryTerm":           flavor = "glossary"
    else: cdrcgi.bail("Publish preview only available for Summary, "
                      "DrugInfoSummary, GlossaryTerm and Protocol documents")
showProgress("Using flavor: %s..." % flavor)

#----------------------------------------------------------------------
# Filter the document.
#----------------------------------------------------------------------
if not filterSets.has_key(docType):
    cdrcgi.bail("Don't have filters set up for %s documents yet" % docType)
doc = cdr.filterDoc(session, filterSets[docType], docId = docId, 
                    docVer = docVer)
if type(doc) == type(()):
    doc = doc[0]
showProgress("Document filtering complete...")
pattern1 = re.compile("<\?xml[^?]+\?>", re.DOTALL)
pattern2 = re.compile("<!DOCTYPE[^>]+>", re.DOTALL)
doc = pattern1.sub("", doc)
doc = pattern2.sub("", doc)
showProgress("Doctype declaration stripped...")
#cdrcgi.bail("flavor=%s doc=%s" % (flavor, doc))
try:
    if dbgLog:
        cdr2cg.debuglevel = 1
        showProgress("Debug logging turned on...")
    showProgress("Submitting request to Cancer.gov...")
    resp = cdr2cg.pubPreview(doc, flavor)
    showProgress("Response received from Cancer.gov...")
except:
    cdrcgi.bail("Preview formatting failure")

#doc = cdrcgi.decode(doc)
#doc = re.sub("@@DOCID@@", docId, doc)

#----------------------------------------------------------------------
# Show it.
#----------------------------------------------------------------------
showProgress("Done...")
cdrcgi.sendPage("""\
<html>
 <head>
  <title>Publish Preview for CDR%d</title>
  <link rel='stylesheet'
        href='http://%s/stylesheets/nci.css'
        type='text/css'>
  <link rel='stylesheet'
        href='http://%s/stylesheets/nci_general_browsers.css'
        type='text/css'>
 </head>
 <body>
  %s
 </body>
</html>""" % (intId, ssHost, ssHost, resp.xmlResult))
