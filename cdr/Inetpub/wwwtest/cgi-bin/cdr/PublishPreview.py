#----------------------------------------------------------------------
#
# $Id: PublishPreview.py,v 1.35 2008-03-31 20:59:20 venglisc Exp $
#
# Transform a CDR document using an XSL/T filter and send it back to 
# the browser.
#
# $Log: not supported by cvs2svn $
# Revision 1.34  2008/03/26 20:43:57  venglisc
# Added some regular expression replacement strings to allow some links to
# properly work within the PP document and to change the target of the
# images to come from our CDR servers. (Bug 3973)
#
# Revision 1.33  2008/02/19 22:53:44  venglisc
# Reverting the work around allowing protocol patient publish preview
# documents to be displayed properly.  These are now correctly handled
# as part of the publish preview code. (Bug 2002)
#
# Revision 1.32  2008/01/23 20:59:53  venglisc
# Removing previous changes in order to move to production the IE6 fix
# for publish preview to shrink a page when printed so that its right
# border isn't cut off. (Bug 2002)
#
# Revision 1.31  2008/01/09 17:53:20  venglisc
# Made modifications to temporarily allow protocol patient publish preview
# to work by accessing the old gatekeeper (using cdr2cg.py). (Bug 2002)
#
# Revision 1.30  2007/12/11 19:10:16  venglisc
# Changes for new PublishPreview using the new gatekeeper code (Bug 2002)
#
# Revision 1.29  2006/11/02 00:16:01  venglisc
# Adjusted the doctype passed to Cancer.gov to what they had implemented.
# (Bug 2310)
#
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
import cgi, cdr, cdrcgi, cdrdb, re, cdr2gk, sys, time
# Interim fix to allow Protocol Patient publish preview
##import cdr2cg

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
    cdr2gk.host = cgHost
    # Temporary fix for Protocol_Patient PP
    ##if flavor == 'Protocol_Patient':
    ##    cdr2cg.host = cgHost

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

# Note: The values for flavor listed here are not the only values possible.
#       These values are the default values but XMetaL macros may pass
#       additional values for the flavor attribute. 
#       Currently, the additional values are implemented:
#         Protocol_Patient
#         Summary_Patient       (unused)
#         CTGovProtocol_Patient (unused)
# -------------------------------------------------------------------------
if not flavor:
    if docType == "Summary":                  flavor = "Summary"
    elif docType == "DrugInformationSummary": flavor = "DrugInfoSummary"
    elif docType == "InScopeProtocol":        flavor = "Protocol_HP"
    elif docType == "CTGovProtocol":          flavor = "CTGovProtocol"
    elif docType == "GlossaryTerm":           flavor = "GlossaryTerm"
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
        cdr2gk.debuglevel = 1
        showProgress("Debug logging turned on...")
    showProgress("Submitting request to Cancer.gov...")
    # Temp fix to make Protocol_Patient PP work
    ##if flavor == 'Protocol_Patient':
    ##    resp = cdr2cg.pubPreview(doc, flavor)
    ##else:
    ##    resp = cdr2gk.pubPreview(doc, flavor)
    resp = cdr2gk.pubPreview(doc, flavor)
    showProgress("Response received from Cancer.gov...")
except:
    cdrcgi.bail("Preview formatting failure")

#doc = cdrcgi.decode(doc)
#doc = re.sub("@@DOCID@@", docId, doc)

#----------------------------------------------------------------------
# Show it.
#----------------------------------------------------------------------
showProgress("Done...")

# The output from Cancer.gov is modified to add the CDR-ID to the title
# We are also adding a style to work around a IE6 bug that causes the 
# document printed to be cut of on the right by shifting the entire
# document to the left
# We also need to modify the image links so that they are pulled from 
# the CDR server.
# ---------------------------------------------------------------------

# Include the CDR-ID of the document to the HTML title
# ----------------------------------------------------
pattern3 = re.compile('<title>CDR Preview', re.DOTALL)
html = pattern3.sub('<title>Publish Preview: CDR%s' % intId, resp.xmlResult)
#cdrcgi.sendPage("%s" % html)

# Fix the print out so that it's not cut off in IE6
# -------------------------------------------------
pattern4 = re.compile('</head>', re.DOTALL)
html = pattern4.sub('\n<!--[if IE 6]>\n<link rel="stylesheet" type="text/css" media="print" href="/stylesheets/ppprint.css">\n<![endif]-->\n</head>\n', html)

# Make the SummaryRef elements clickable within the document
# ----------------------------------------------------------
pattern5 = re.compile('<a class="SummaryRef" href=".*?#Section_(.*?)"')
html = pattern5.sub('<a class="SummaryRef" href="#Section_\g<1>"', html)

# Replace the image links for the popup boxes to point to our CDR repository
# --------------------------------------------------------------------------
if html.find('gatekeeper2.cancer.gov/CDRPreviewWS') == -1:
    pp_host = cdr.DEV_HOST
else:
    pp_host = cdr.PROD_HOST

pattern6 = re.compile(
       'imageName=http://(.*?)/images/cdr/live/CDR(.*?)-(.*?)\.jpg')
html = pattern6.sub(
       'imageName=http://%s/cgi-bin/cdr/GetCdrImage.py?id=CDR\g<2>-\g<3>.jpg' % 
       pp_host, html)

#cdrcgi.sendPage("%s" % html)
# Replace the image for the popup boxes to point to our CDR repository
# 
# Cancer.gov is not consistent with the HTML that's returned.
# We need different patterns depending if we're receiving a summary or
# a glossary document
# ---------------------------------------------------------------------
if html.find('class="document-title">Dictionary of Cancer Terms') == -1:
    pattern7 = re.compile(
               'src="http://(.*?)/images/cdr/live/CDR(.*?)-(.*?)\.jpg"')
else:  # for Glossary PP
    pattern7 = re.compile(
               '  src="http://(.*?)/images/cdr/live/CDR(.*?)-(.*?)\.jpg"')
html = pattern7.sub(
       '  src="http://%s/cgi-bin/cdr/GetCdrImage.py?id=CDR\g<2>-\g<3>.jpg"' % 
       pp_host, html)

cdrcgi.sendPage("%s" % html)
