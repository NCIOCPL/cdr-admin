#----------------------------------------------------------------------
#
# $Id$
#
# Prototype for editing CDR filter documents.
#
# Revision 1.23  2008/08/15 04:03:34  ameyer
# Fixed little bug - err check in "session" should have checked "prodSession".
#
# Revision 1.22  2008/06/03 21:58:55  bkline
# Replaced StandardError (going away at some point) with Exception objects.
#
# Revision 1.21  2008/04/29 19:57:34  ameyer
# Some additional utf-8 fixes.
#
# Revision 1.20  2007/11/03 14:15:07  bkline
# Unicode encoding cleanup (issue #3716).
#
# Revision 1.19  2006/10/18 22:53:29  venglisc
# Modified error message. (Bug 2561)
#
# Revision 1.18  2006/10/18 17:41:54  venglisc
# Added an extra check to ensure that a filter that is being renamed is
# indeed a filter document on BACH. (Bug 2561)
#
# Revision 1.17  2005/07/19 15:13:24  venglisc
# Modified the dataSource passed to the connect module after the server was
# moved behind the OTSA firewall. The hostname now has to be specified to
# be resolved within the firewall (without the nci.nih.gov domain).
#
# Revision 1.16  2003/12/30 22:49:14  venglisc
# Added text explaining usage of bachid field.
#
# Revision 1.15  2003/11/05 14:48:35  bkline
# Added optional field for ID of existing CDR document on Bach when
# title is being changed.
#
# Revision 1.14  2003/09/16 19:14:56  bkline
# Escaped blank filter template to work around bug in Mozilla.  Removed
# hook to xEditFilter.py (added by Peter back in the spring for an
# unspecified reason).
#
# Revision 1.13  2003/03/19 17:43:42  bkline
# Modified file writing code to ensure timely file closing.
#
# Revision 1.12  2003/03/19 15:33:51  bkline
# Added massive amounts of (conditional) debug logging to CVS processing.
# Trying to track down failures which leave CVS lockfiles hanging around.
#
# Revision 1.11  2003/02/25 20:03:59  pzhang
# Show edit feature only on Dev machine (MAHLER now).
#
# Revision 1.10  2002/09/13 17:08:10  bkline
# Added View command.
#
# Revision 1.9  2002/09/13 11:36:50  bkline
# Added Compare function.
#
# Revision 1.8  2002/09/07 13:14:25  bkline
# Added auto-cvs to filter editing.
#
# Revision 1.7  2002/07/29 19:23:37  bkline
# Fixed some bail() calls (had wrong first arg).
#
# Revision 1.6  2002/06/26 11:46:45  bkline
# Added option to version document.
#
# Revision 1.5  2001/12/01 17:58:54  bkline
# Added support for checking the filter back in to the CDR.
#
# Revision 1.4  2001/07/06 16:02:40  bkline
# Added missing / for closing CdrDoc tag in BLANKDOC.
#
# Revision 1.3  2001/06/13 20:15:39  bkline
# Added code to strip carriage returns from text for TEXTAREA control.
#
# Revision 1.2  2001/04/08 22:54:59  bkline
# Added Unicode mapping calls.
#
#----------------------------------------------------------------------

#----------------------------------------------------------------------
# Import required modules.
#----------------------------------------------------------------------
import cgi, cdr, cdrdb, os, re, cdrcgi, sys, tempfile, string, socket, time

#----------------------------------------------------------------------
# Edit only on Dev machine.
# Since we moved to SVN for source control we're not editing filters
# through this interface anymore
#----------------------------------------------------------------------
localhost = socket.gethostname()
#if string.upper(localhost) == "MAHLER":
#    localhost = "Dev"

#----------------------------------------------------------------------
# Set some initial values.
#----------------------------------------------------------------------
banner   = "CDR Filter Editing"
title    = "Edit CDR Filter"
BLANKDOC = cgi.escape("""\
<CdrDoc Type='Filter'>
 <CdrDocCtl>
  <DocTitle>*** PUT YOUR TITLE HERE ***</DocTitle>
 </CdrDocCtl>
 <CdrDocXml><![CDATA[<?xml version="1.0"?>
  <xsl:transform xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                 version="1.0">
   <xsl:output method="html"/>
   <xsl:template match="/">
    *** PUT YOUR TEMPLATE RULES HERE ***
   </xsl:template>
  </xsl:transform>]]>
 </CdrDocXml>
</CdrDoc>
""")

#----------------------------------------------------------------------
# Load the fields from the form.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
if not fields: cdrcgi.bail("Unable to read form fields", banner)
session    = cdrcgi.getSession(fields)
request    = cdrcgi.getRequest(fields)
version    = fields.getvalue('version')
cvsid      = fields.getvalue('cvsid')
cvspw      = fields.getvalue('cvspw')
cvscomment = fields.getvalue('cvscomment')
bachid     = fields.getvalue('bachid') or None
logName    = "%s/cvs-filter.log" % cdr.DEFAULT_LOGDIR
debugging  = 1
if not session: cdrcgi.bail("Unable to log into CDR Server", banner)
if not request: cdrcgi.bail("No request submitted", banner)

#----------------------------------------------------------------------
# Logging to keep an eye on problems (mostly with CVS).
#----------------------------------------------------------------------
def debugLog(what):
    #cdrcgi.bail("debugging=%s" % str(debugging))
    if debugging:
        try:
            f = open(logName, "a")
            f.write("%s: %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), what))
            f.close()
        except Exception, info:
            cdrcgi.bail("Failure writing to %s: %s" % (logName, str(info)))

#----------------------------------------------------------------------
# Display the CDR document form.
#----------------------------------------------------------------------
def showForm(doc, subBanner, buttons):
    hdr = cdrcgi.header(title, banner, subBanner, "EditFilter.py", buttons,
                        numBreaks = 1)
    html = hdr + u"""\
   <br>
   <textarea name='Doc' rows='40' cols='80'>%s</textarea>
   <input type='hidden' name='%s' value='%s'>
   <br>
   <br>
   <input type='submit' name='%s' value='Compare With'>&nbsp;&nbsp;
   <input name='DiffWith' value='bach'>
  </form>
 </body>
</html>
""" % (doc.replace('\r', ''),
       cdrcgi.SESSION,
       session,
       cdrcgi.REQUEST)
    cdrcgi.sendPage(html)

#----------------------------------------------------------------------
# Don't leave dross around if we can help it.
#----------------------------------------------------------------------
def cleanup(abspath):
    debugLog("cleaning up %s" % abspath)
    try:
        os.chdir("..")
        runCommand("rm -rf %s" % abspath)
    except:
        pass

#----------------------------------------------------------------------
# Fetch a document by title for a specified server.
#----------------------------------------------------------------------
def getFilterXml(title, server = 'localhost'):
    filters = ['name:Fast Denormalization Filter With Indent']
    try:
        conn = cdrdb.connect('CdrGuest', server)
        cursor = conn.cursor()
        cursor.execute("""\
                SELECT d.xml
                  FROM document d
                  JOIN doc_type t
                    ON t.id = d.doc_type
                 WHERE t.name = 'Filter'
                   AND d.title = ?""", title)
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail("Cannot find filter '%s' on %s" %
                    (cgi.escape(title), server))
        if len(rows) > 1:
            cdrcgi.bail("Ambiguous filter document title '%s' on %s" %
                    (cgi.escape(title), server))
        return rows[0][0].replace('\r', '')

    except Exception, info:
        cdrcgi.bail("Failure retrieving '%s' from %s: %s" %
                    (cgi.escape(title), server, str(info)))

#----------------------------------------------------------------------
# Remove the document ID attribute so we can save the doc under a new ID.
#----------------------------------------------------------------------
def stripId(doc):
    pattern = re.compile(r"(.*<CdrDoc[^>]*)\sId='[^']*'(.*)", re.DOTALL)
    return pattern.sub(r'\1\2', doc)

#----------------------------------------------------------------------
# Object for results of an external command.
#----------------------------------------------------------------------
class CommandResult:
    def __init__(self, code, output):
        self.code   = code
        self.output = output

#----------------------------------------------------------------------
# Run an external command.
#----------------------------------------------------------------------
def runCommand(command):
    debugLog("runCommand(%s)" % command)
    try:
        commandStream = os.popen('%s 2>&1' % command)
        output = commandStream.read()
        code = commandStream.close()
        return CommandResult(code, output)
    except Exception, info:
        debugLog("failure running command: %s" % str(info))

#----------------------------------------------------------------------
# Find id of document on production server; create doc if necessary.
#----------------------------------------------------------------------
def getProdId(docId, doc, session):
    if bachid:
        id = int(re.sub(r'[^\d]+', '', bachid))

        # Make sure the docId provided when renaming a filter title
        # is indeed a filter document on BACH
        # ---------------------------------------------------------
        conn = cdrdb.connect('CdrGuest', dataSource = cdr.PROD_NAME)
        prodCursor = conn.cursor()
        prodCursor.execute("""\
            SELECT t.name
              FROM doc_type t
              JOIN document d
                ON t.id = d.doc_type
             WHERE d.id = ?""", id)

        row = prodCursor.fetchone()
        if not row:
            cdrcgi.bail("%s%s %s" %
                         ('ERROR: Changes saved locally but cannot ',
                          'find document on Bach with ID', bachid))
        elif row[0] != 'Filter':
            cdrcgi.bail("%s%s %s (%s)" %
                         ('ERROR: Changes saved locally but cannot ',
                          'find filter on Bach with ID',
                          bachid, row[0]))
        return "CDR%010d" % id

    try:
        # Find out what the title is.
        id = int(re.sub(r'[^\d]+', '', docId))
        conn = cdrdb.connect('CdrGuest')
        devCursor = conn.cursor()
        devCursor.execute("""\
                SELECT title
                  FROM document
                 WHERE id = ?""", id)
        row = devCursor.fetchone()
        if not row:
            cdrcgi.bail("Cannot find title for %s" % docId)
        title = row[0]

        # Look up the ID on the production server using the title.
        conn = cdrdb.connect('CdrGuest', dataSource = cdr.PROD_NAME)
        prodCursor = conn.cursor()
        prodCursor.execute("""\
            SELECT d.id
              FROM document d
              JOIN doc_type t
                ON t.id = d.doc_type
             WHERE d.title = ?
               AND t.name = 'Filter'""", title)
        rows = prodCursor.fetchall()

        # If there's exactly one document, we're done.
        if len(rows) == 1:
            return "CDR%010d" % rows[0][0]

        # If there are multiple documents, stop.
        if len(rows) > 1:
            cdrcgi.bail("More than one document found on %s with title %s" %
                    (cdr.PROD_SERVER, cgi.escape(title)))

        # The production server doesn't have the document yet; create it.
        devCursor.execute("""\
                SELECT u.name, u.password
                  FROM usr u
                  JOIN session s
                    ON s.usr = u.id
                 WHERE s.name = ?""", session)
        rows = devCursor.fetchall()
        if not rows:
            cdrcgi.bail("Failure locating session information")
        uid, pwd = rows[0]
        reason = "Migrating new filter from development server"
        prodSession = cdr.login(uid, pwd, host = cdr.PROD_NAME)
        if prodSession.find("<Err") != -1:
            cdrcgi.bail("Failure logging onto production server: %s" %
                    prodSession)
        doc = stripId(doc)
        docId = cdr.addDoc(prodSession, doc = doc, reason = reason,
                host = cdr.PROD_NAME)
        if docId.find("<Err") != -1:
            cdr.logout(prodSession, host = cdr.PROD_NAME)
            cdrcgi.bail("Failure adding %s to production server: %s" %
                    (cgi.escape(title), docId))
        doc = cdr.getDoc(prodSession, docId, 'Y', host = cdr.PROD_NAME)
        if doc.find("<Err") == 0:
            cdr.logout(prodSession, host = cdr.PROD_NAME)
            cdrcgi.bail("Failure checking out %s from production server: %s" %
                    (cgi.escape(title), doc))
        docId = cdr.repDoc(prodSession, doc = doc, checkIn = 'Y',
                ver = 'Y', reason = reason, host = cdr.PROD_NAME)
        cdr.logout(prodSession, host = cdr.PROD_NAME)
        if docId.find("<Err") != -1:
            cdrcgi.bail("Failure checking in %s to production server: %s" %
                    (cgi.escape(title), docId))
        return docId
    except:
        raise
        cdrcgi.bail("Failure locating production document ID")

#----------------------------------------------------------------------
# Replace the development document ID with the production document ID.
#----------------------------------------------------------------------
def replaceId(doc, devId, prodId):
    if doc.find(devId) == -1:
        cdrcgi.bail("Cannot find document ID %s in document" % devId)
    return doc.replace(devId, prodId, 1)

#----------------------------------------------------------------------
# Load an existing document.
#----------------------------------------------------------------------
if request in ("Load", "View"):
    if not fields.has_key(cdrcgi.DOCID):
        cdrcgi.bail("No document ID specified", banner)
    if request == "Load":
        checkOut = "Y"
        buttons  = ("Load", "Save", "Checkin", "Clone")
        banner   = "Edit existing document"
    else:
        checkOut = "N"
        buttons  = (localhost == "Dev") and ("Load", "Clone") or ()
        banner   = "View existing document"
    doc = cdr.getDoc(session, fields[cdrcgi.DOCID].value, checkOut)
    doc = cdrcgi.decode(doc)
    if doc.find("<Errors>") >= 0:
        cdrcgi.bail(doc, banner)
    showForm(cgi.escape(doc), banner, buttons)

#--------------------------------------------------------------------
# Show the differences with a copy of the filter on another server.
#--------------------------------------------------------------------
elif request == 'Compare With':
    if not fields.has_key("Doc"):
        cdrcgi.bail("No document found to compare")
    if not fields.has_key("DiffWith"):
        cdrcgi.bail("No server specified for comparison")
    doc = fields["Doc"].value
    server = fields["DiffWith"].value
    pattern = re.compile(r"<DocTitle[^>]*>([^<]+)</DocTitle>", re.DOTALL)
    match = pattern.search(doc)
    if not match: cdrcgi.bail("No DocTitle found")
    title = match.group(1)
    doc1 = getFilterXml(title, 'localhost')
    doc2 = getFilterXml(title, server)
    name1 = "localhost-copy.xml"
    name2 = "%s-copy.xml" % server
    cmd = "diff -au %s %s" % (name1, name2)
    try:
        workDir = cdr.makeTempDir('diff')
    except Exception, args:
        cdrcgi.bail("%s: %s" % (args[0], args[1]))
    f1 = open(name1, "w")
    f1.write(doc1.encode('utf-8'))
    f1.close()
    f2 = open(name2, "w")
    f2.write(doc2.encode('utf-8'))
    f2.close()
    result = cdr.runCommand(cmd)
    cleanup(workDir)
    report = cgi.escape(result.output)
    if report.strip():
        title = "Differences between %s and %s" % (name1, name2)
    else:
        title = "%s and %s are identical" % (name1, name2)
    cdrcgi.sendPage(u"""\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>%s</title>
 </head>
 <body>
  <h3>%s</h3>
  <pre>%s</pre>
 </body>
</html>""" % (title, title, report.replace('\r', '')))

#----------------------------------------------------------------------
# Tell the user we don't know how to do what he asked.
#----------------------------------------------------------------------
else: cdrcgi.bail("Request not yet implemented: " + request, banner)
