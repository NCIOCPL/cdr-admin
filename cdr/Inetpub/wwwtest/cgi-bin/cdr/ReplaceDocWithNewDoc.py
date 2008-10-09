#----------------------------------------------------------------------
# Replace an existing version of a document with a completely new
# document that was separately created and edited under its own
# CDR document ID.
#
# This is primarily intended for use when a new Summary document has
# been independently developed over a long period of time to replace
# an existing Summary.
#
# Requirements and design are described in Bugzilla issue #3561.
#
# $Id: ReplaceDocWithNewDoc.py,v 1.3 2008-10-09 13:57:37 ameyer Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2008/09/24 03:20:13  ameyer
# Bug fixes.  Slight user interface improvements.  Slight code cleanup.
#
# Revision 1.1  2008/09/19 02:37:37  ameyer
# Initial version.
#
#----------------------------------------------------------------------

import cgi, cgitb, cdr, cdrcgi, cdrdb
cgitb.enable()

# Prepare a log file for what we're about to do
# Not using a banner since the program comes through here more than once
G_log = cdr.Log("ReplaceDocWithNewDoc.log", banner=None)

# These will contain the full documents, in cdr.getDoc CdrDoc format.
# If they exist, the docs have been checked out and must be checked in
#   before exiting
oldDoc  = None
newDoc  = None

session = None

def fatal(msgs):
    """
    Cleanup and display a fatal error to the user.

    Pass:
        msgs - Single message or sequence of messages.

    Return:
        Does not return.
    """
    # Cleanup locked documents
    unlockDocs("Fatal error aborted ReplaceDocWithNewDoc")

    # Convert messages from string to sequence, if needed and prepend
    #   fatal error string
    msgList = ["Fatal error - aborting",]
    if type(msgs) in (type(()), type([])):
        msgList += msgs
    else:
        msgList.append(msgs)

    # Log what we're doing
    log(msgList)

    # Bail out
    bailMsg = ''
    for msg in msgList:
        bailMsg += "%s<br />\n" % msg
    cdrcgi.bail(bailMsg)

def log(msgs):
    """
    Wrapper for Log.write()

    Pass:
        msgs - Single message string or sequence of message strings.
    """
    global G_log

    G_log.write(msgs)

def checkDoc(docId):
    """
    Check that a document exists and find it's document type.

    Pass:
        CDR doc ID.

    Return:
        Document type, or None if doc not found.
    """
    # Normalize doc ID to simple integer
    docNum = cdr.exNormalize(docId)[1]

    try:
        conn   = cdrdb.connect()
        cursor = conn.cursor()
        cursor.execute("""
SELECT t.name
  FROM doc_type t
  JOIN document d
    ON d.doc_type = t.id
 WHERE d.id = ?""", docNum)
        row = cursor.fetchone()
    except Exception, info:
        fatal("Error retrieving doctype for %s: %s" % \
                    (docId, str(info)))

    if row:
        return row[0]
    return None

def getLockedDoc(docId):
    """
    Retrieve the document, locked for update.

    Pass:
        docId - CDR ID of the document.

    Return:
        cdr.doc object for the document.

    If errors, do not return.  Bail out with error message.
    """
    global session

    docObj = cdr.getDoc(session, docId, checkout='Y', getObject=True)

    # Bail out if error
    if type(docObj) in (type(""), type(u"")):
        errList = ["Unable to lock document %s" % docId] + \
                  cdr.getErrors(docObj, errorsExpected=True, asSequence=True)
        fatal(errList)

    # Success
    return docObj

def unlockDocs(reason):
    """
    Unlock document that need unlocking.
    Called before exit.

    Pass:
        Reason for unlock to log on server.

    Return:
        Error messages or empty string
    """
    # If there is no session, nothing was locked
    oldDocErrs = ""
    newDocErrs = ""
    if session:
        # Error could occur after locking one but not the other
        # So check each individually
        if oldDoc:
            log("Unlocking old document: %s" % oldDocIdStr)
            oldDocErrs += cdr.unlock(session, oldDocIdStr, reason=reason)
            if oldDocErrs:
                log("Error unlocking old doc:\n%s" % oldDocErrs)
        if newDoc:
            log("Unlocking new document: %s" % newDocIdStr)
            newDocErrs += cdr.unlock(session, newDocIdStr, reason=reason)
            if newDocErrs:
                log("Error unlocking new doc:\n%s" % newDocErrs)

    return(oldDocErrs + newDocErrs)


def getFragmentLinks(targetDocId):
    """
    Search for any documents that link to fragments in the old document.
    These must be resolved by the user sometime after the replacement.

    Pass:
        targetDocId - ID of the document to be replaced.

    Return:
        HTML table with the report.
        None if there are no fragment links
    """
    try:
        conn   = cdrdb.connect()
        cursor = conn.cursor()
        cursor.execute("""
SELECT DISTINCT t.name, d.id, d.title, n.source_elem, n.target_frag
           FROM document d
           JOIN doc_type t
             ON t.id = d.doc_type
           JOIN link_net n
             ON n.source_doc = d.id
          WHERE n.target_doc = ?
            AND n.target_frag is not null
       ORDER BY t.name, d.id, n.source_elem, n.target_frag
""", cdr.exNormalize(targetDocId)[1])
    except Exception, info:
        fatal("Error retrieving links to fragments in old doc: %s" % \
                    info)

    # Get them, there won't be more than a few, if any
    rows = cursor.fetchall()

    # If there aren't any, we're done
    if len(rows) == 0:
        return None

    html = """
<table border='1'>
 <tr>
  <th>Doctype</th>
  <th>Doc ID</th>
  <th>Doc title</th>
  <th>Element</th>
  <th>Frag ID</th>
 </tr>
"""
    for row in rows:
        html += """
 <tr>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
  <td>%s</td>
 </tr>
""" % (row[0], row[1], row[2], row[3], row[4])

    html += "</table>\n"

    return html

def versionDocIfNeeded(session, docId, doc):
    """
    If docId identifies a document for which the current working document
    is different from the last version, version it.

    Pass:
        session - Credentials
        docId   - ID of doc to process, CDR0000000000 format.
        doc     - Full CWD of doc, in CdrDoc format from cdr.getDoc().
    """
    try:
        # Is last version same as CWD?
        isChanged = cdr.lastVersions(session, docId)[2]

        if isChanged == 'Y':
            log("Creating non-publishable version of doc %s" % docId)
            reason='Versioning last CWD of replaced document'
            resp = cdr.repDoc(session, doc=doc, checkIn='N', ver='Y',
                       verPublishable='N', comment=reason)
            errList = cdr.getErrors(resp, errorsExpected=False,
                                    asSequence=True)
            if errList:
                raise Exception(errList)

    except Exception, info:
        fatal("Error versioning CWD of %s: %s" % (docId, str(info)))

def removeWillReplace(session, docXml):
    """
    Remove the "WillReplace" element from a document.

    Pass:
        session - credentials
        docXml  - Document xml (unicode or utf-8 okay)

    Return:
        Transformed doc without WillReplace.
    """
    xsl = """\
<?xml version='1.0' encoding='UTF-8'?>

<xsl:transform                version = '1.0'
                            xmlns:xsl = 'http://www.w3.org/1999/XSL/Transform'
                            xmlns:cdr = 'cips.nci.nih.gov/cdr'>

 <xsl:output                   method = 'xml'/>

 <!--
 =======================================================================
 Copy almost everything straight through.
 ======================================================================= -->
 <xsl:template                  match = '@*|node()|comment()|
                                         processing-instruction()'>
  <xsl:copy>
   <xsl:apply-templates        select = '@*|node()|comment()|
                                         processing-instruction()'/>
  </xsl:copy>
 </xsl:template>

 <!-- Except this -->
 <xsl:template                  match = 'WillReplace' />

</xsl:transform>
"""
    log("Filtering new doc to remove WillReplace element")
    response = cdr.filterDoc(session, xsl, doc=docXml, inline=True)
    if type(response) in (type(""), type(u"")):
        # Docs will be unlocked later
        fatal("Error removing WillReplace element from doc: %s" %\
                    response)

    # Return transformed doc
    return response[0]


# Constants
LF      = "ReplaceDocWithNewDoc.log"
TITLE   = "Replace Old Document with New One"
SCRIPT  = "ReplaceDocWithNewDoc.py"

# Action button constants
MENUBAR_BUTTONS = (cdrcgi.MAINMENU, "Log Out")
START_SUBMIT    = "Submit"                          # Start screen submit
START_CANCEL    = "Cancel"                          # Start screen cancel
CONFIRM_SUBMIT  = "Proceed to Replace Document"     # Submission confirmed
CONFIRM_CANCEL  = "Cancel Document Replacement"     # Submission cancelled

# HTML containing a description of what will be done
DESCRIPTIVE_HTML = """
<h3>Purpose</h3>
<p>This program replaces an existing document with a new one.  The new
document will become the current working version of the document identified
by the old document ID.  It can be used when a
new version of a document has been prepared as a completely separate
document that will, when it is ready, replace the original version.</p>

<h3>Pre-conditions</h3>
<p>All of the following conditions must be met before replacment will
proceed:</p>
<ol>
 <li>The user must be authorized to perform this operation.</li>
 <li>The old and new documents must both be Summaries.</li>
 <li>The new replacement document must have a WillReplace element with
     a cdr:ref referencing the old document.</li>
 <li>After receiving feedback, the user must confirm that the replacement
     should proceed.</li>
</ol>

<h3>Operation</h3>
<p>A user first enters the CDR document ID for the old (replaced) and
new (replacement) documents in the form below and clicks "Submit".
The program then checks to see if the first three conditions above are met.
If they are, the program will report to the user:</p>
<ul>
 <li>The titles of the respective old and new documents.</li>
 <li>The validation status of the new document.</li>
 <li>A list of any documents that have links to specific fragments in the
     old document.  Those links will need to be resolved after the new
     document replaces the old.</li>
</ul>

<p>The user must then confirm that this replacement should proceed.</p>

<p>If replacement is confirmed, the program will do the following:</p>
<ol>
 <li>Check out both documents.  If either document is locked by someone
     else, the program will stop.</li>
 <li>Version the current working document for the old document, if it is
     different from the last saved version.</li>
 <li>Remove the WillReplace element from the new document.</li>
 <li>Save the current working document for the new document as a
     non-publishable version under the old ID.</li>
 <li>Mark the now unused ID of the new document as deleted.  That ID will
     no longer be used in the CDR.</li>
</ol>
"""
DOCUMENT_ID_FORM = """
<h3>Document Identifiers</h3>
 <table border='0'>
  <tr>
   <td align='right'><strong>Old CDR ID </strong></td>
   <td><input type='text' size='12' name='oldDocId' /></td>
   <td>(keep this ID but replace the doc with the new one)</td>
  </tr><tr>
   <td align='right'><strong>New CDR ID </strong></td>
   <td><input type='text' size='12' name='newDocId' /></td>
   <td>(keep this doc but store it with the old ID)</td>
  </tr>
 </table>
 <p />
 <table border='0'>
  <tr>
   <td><input type='submit' name='%s' value='%s' /></td>
   <td><input type='submit' name='%s' value='%s' /></td>
  <tr>
 </table>
""" % (cdrcgi.REQUEST, START_SUBMIT, cdrcgi.REQUEST, START_CANCEL)

fields = cgi.FieldStorage()
if not fields:
    fatal ("Unable to load form fields - should not happen!")

# Collect form data
session   = cdrcgi.getSession(fields)
request   = cdrcgi.getRequest(fields)
oldDocId  = fields.getvalue("oldDocId") or None
newDocId  = fields.getvalue("newDocId") or None

# Normalize doc IDs to standard CDR0000000000 format
if oldDocId:
    oldDocIdStr = cdr.exNormalize(oldDocId)[0]
if newDocId:
    newDocIdStr = cdr.exNormalize(newDocId)[0]

# Navigation away from form?
if request in (cdrcgi.MAINMENU, START_CANCEL):
    cdrcgi.navigateTo("Admin.py", session)
if request == "Log Out":
    cdrcgi.logout(session)

# Authorization
# if not session:
#    fatal ("Unknown or expired CDR session.")
# if not cdr.canDo (session, ):
#   fatal ("Sorry, user not authorized to make global changes")

# Anything we send concludes with the session value and page termination tags
endPage = """
 <input type='hidden' name='%s' value='%s' />
 </FORM>
 </BODY>
</HTML>
""" % (cdrcgi.SESSION, session)

log("Before check, request=%s" % request)
# If first time through, or if insufficient data, put up initial form
if not oldDocId or not newDocId or request == CONFIRM_CANCEL:

    # Send the initial explanation and input form
    log("Putting up initial input form")
    html = cdrcgi.header(TITLE, TITLE, 'Initial screen',
                         script=SCRIPT, buttons=MENUBAR_BUTTONS) + \
           DESCRIPTIVE_HTML + DOCUMENT_ID_FORM + endPage
    cdrcgi.sendPage(html)

####################################################################
# Check that documents are okay for this action
####################################################################
oldDocType = checkDoc(oldDocId)
newDocType = checkDoc(newDocId)

# Both documents must exist and, for this version, must be Summaries
allowedTypes = ('Summary',)
msgs = ""
if not oldDocType:
    msgs += "Old document %s not found in database<br>" % oldDocIdStr
elif oldDocType not in allowedTypes:
    msgs += "Old document %s is of wrong doctype=%s<br>" % (oldDocIdStr,
                                                            oldDocType)
if not newDocType:
    msgs += "New document %s not found in database<br>" % newDocIdStr
elif newDocType not in allowedTypes:
    msgs += "New document %s is of wrong doctype=%s<br>" % (newDocIdStr,
                                                            newDocType)

# They must have the same doc type
if not msgs and oldDocType != newDocType:
    msgs += """
Old document %s is of type %s, but new doc %s is of type %s<br>
The two document types must be the same in order to replace one doc with the
other.
""" % (oldDocIdStr, oldDocType, newDocIdStr, newDocType)

# Any errors?
if msgs:
    fatal(msgs)

# The new document must have a WillReplace@cdr:ref referencing the old one
try:
    conn   = cdrdb.connect()
    cursor = conn.cursor()
    cursor.execute("""
SELECT value
  FROM query_term
 WHERE path = '/Summary/WillReplace/@cdr:ref'
   AND doc_id = ?""", newDocId)
    row = cursor.fetchone()
except Exception, info:
    fatal("Error retrieving WillReplace@cdr:ref for new doc=%s: %s" % \
          (newDocIdStr, info))

if not row:
    fatal("WillReplace / @cdr:ref not found in new document")
refDocId = row[0]
if refDocId != cdr.exNormalize(oldDocIdStr)[0]:
    fatal("WillReplace / @cdr:ref=%s does not match user entered old id=%s" \
                % (refDocId, oldDocIdStr))

####################################################################
# Request user confirmation if needed
####################################################################
# If we've passed all validation, but user hasn't confirmed yet,
#   give him what he needs to confirm
if request != CONFIRM_SUBMIT:

    # Prepare to send another screen
    html = cdrcgi.header(TITLE, "Confirmation required", '', script=SCRIPT,
           buttons=MENUBAR_BUTTONS) + "\n"

    # Validate new doc
    result  = cdr.valDoc(session, newDocType, docId=newDocId)
    errList = cdr.getErrors(result, errorsExpected=False, asSequence=True)

    # Get info for display
    try:
        conn   = cdrdb.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM document WHERE id = %d" %
                        cdr.exNormalize(oldDocId)[1])
        oldDocTitle = cursor.fetchone()[0]
        cursor.execute("SELECT title FROM document WHERE id = %d" %
                        cdr.exNormalize(newDocId)[1])
        newDocTitle = cursor.fetchone()[0]
    except Exception, info:
        fatal("Error retrieving titles for docs: %s" % info)

    # Tell user what will be done
    html += """
<style type='text/css'>
 td {
  font: 14pt 'Arial'; color: Blue; font-weight: bold; background transparent;
 }
</style>
<table class='P'>
 <tr>
   <td align='right' class='P'>Replace: </td><td>%s</td><td>%s</td>
 </tr>
 <tr>
   <td align='right'>With: </td><td>%s</td><td>%s</td>
 </tr>
</table>
""" % (oldDocIdStr, oldDocTitle, newDocIdStr, newDocTitle)

    html += """
<hr />
<h3>Validation Report:</h3>
"""
    if errList:
        html += """
<p>These errors occurred when validating the new document:</p>
<ul>
"""
        for err in errList:
            html += " <li>%s</li>\n" % err
        html += """
</ul>
<p>Replacing an existing document with a new one that is invalid is
allowed, but please consider whether you really want to do that.</p>

<p>The new document will be saved as a <strong>non-publishable</strong>
version.</p>
"""
    else:
        html += """
<p>There were no validation errors in the new document.</p>
"""

    # Check links to fragments in the old document
    html += """
<hr />
<h3>Linked Fragments Report:</h3>
"""
    linkHtml = getFragmentLinks(oldDocId)
    if linkHtml:
        html += """
<p>There are links from other documents to specific fragments in the
old document.  These are listed below.</p>

<p>Fragment identifiers in the new replacement document are likely not
the same as they are in the old document.  Therefore, when a publishable
version of the replaced document is created, a user must individually
fix these links to refer to valid fragment IDs in the new replacement
version, or the user must delete them.  Otherwise misdirected or broken
links are likely to occur in the published documents.</p>

<p>The new document will be saved as a <strong>non-publishable</strong>
version.  Please coordinate the creation of a publishable version with
fixups of fragment links to the document, so that both the new
publishable version of this document and new publishable versions of
any documents that link to it can all be published in the same
publishing job.</p>
""" + linkHtml

    else:
        html += """
<p>There were no external documents with links to specific fragments that
must be resolved.  The new document can replace the old one without
breaking any links.</p>

<p>The new document will be saved as a <strong>non-publishable</strong>
version.</p>
"""

    # Request confirmation
    log("Requesting confirmation, replace %s with %s" %
        (oldDocIdStr, newDocIdStr))
    html += """
<center>
<table border='0' cellpadding='10'>
 <tr>
  <td><input type='submit' name='%s' value='%s' /></td>
  <td><input type='submit' name='%s' value='%s' /></td>
 </tr>
</table>
<input type='hidden' name='newDocId' value='%s' />
<input type='hidden' name='oldDocId' value='%s' />
</center>
""" % (cdrcgi.REQUEST, CONFIRM_SUBMIT, cdrcgi.REQUEST, CONFIRM_CANCEL,
       newDocId, oldDocId)

    html += endPage

    cdrcgi.sendPage(html)

####################################################################
# Perform the replacement
####################################################################

# If we got this far, we have what we need, the pre-requisites are met,
#   the user has confirmed that we should proceed

# Check out old and new documents, bails out if fails
oldDoc = getLockedDoc(oldDocIdStr)
newDoc = getLockedDoc(newDocIdStr)

# Save the current working version of the old doc, if needed
versionDocIfNeeded(session, oldDocIdStr, str(oldDoc))

# Remove the WillReplace element from the new doc
xml = removeWillReplace(session, newDoc.xml)

# Use the new XML to replace the text of the old document
# We've still got all the CdrDocCtl fields from the new doc here
oldDoc.xml = xml

# Save the new doc under the old ID
reason = "Replacing old version with content of replacement doc ID=%s" % \
          newDocIdStr

# Decision of users was to only make a non-publishable version
log("Saving non-publishable version of new doc using old docId")
resp = cdr.repDoc(session, doc=str(oldDoc), checkIn='N', ver='Y',
                  verPublishable='N', comment=reason, showWarnings=True)

# Expecting (docId, error string)
# If no docId, there were errors
# If no error string there weren't
# If both, save was successful but there were warnings
errors = []
if resp[1]:
    errors = cdr.getErrors(resp[1], errorsExpected=False, asSequence=True)
if not resp[0]:
    # Null docID means errors were fatal
    msgs = ["Unable to save new document",]
    msgs.append(errors)
    fatal(msgs)

# Document stored
msgs = """
<p>The new document was stored successfully as a new version of the old
   document</p>
"""
# Else if messages occurred, they are warnings
if errors:
    msgs += """
<p>However, some warnings were returned:</p>
<ul>
"""
    for err in errors:
        msgs += " <li>%s</li>\n" % err
    msgs += "</ul\n"

# Block the new document from being re-used by accident
log("Blocking new docId: %s" % newDocIdStr)
reason = "This doc replaced %s.  Use that doc now, not this one." % oldDocIdStr
try:
    cdr.setDocStatus(session, newDocIdStr, 'I', comment=reason)
except cdr.Exception, info:
    # Report error, but don't stop
    log("Blocking raised exception: %s" % str(info))
    msgs += "<p><strong>Warning: Failed to block new document:\n</strong></p>"
    msgs += "<p>%s</p>\n" % str(info)

errs = unlockDocs("Completed replacement of %s with %s" %
                  (oldDocIdStr, newDocIdStr))
if errs:
    msgs += """
<p><strong>Errors encountered unlocking documents:</strong><br />
%s<br />
Please check the status of the documents.</p>
"""% str(errs)

msgs += "<p>Processing is complete.</p>"

log("Reporting final confirmation to user")
html = cdrcgi.header(TITLE, "Processing complete", 'Final confirmation',
                     script=SCRIPT, buttons=MENUBAR_BUTTONS)
html += msgs
html += endPage

# That's all
cdrcgi.sendPage(html)
