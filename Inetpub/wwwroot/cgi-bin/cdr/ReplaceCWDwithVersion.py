#--------------------------------------------------------------
# Replace the Current Working Version of a document with an
# earlier version.
#
# Used when the most recent copy of a document has problems and
# we wish to revert to an earlier version.
#--------------------------------------------------------------
import time, cgi, cdr, cdrcgi, cdrdb

TITLE   = "Replace CWD with Older Version"
SCRIPT  = "ReplaceCWDwithVersion.py"
BUTTONS = (cdrcgi.MAINMENU, "Log Out")
LOGFILE = "%s/%s" % (cdr.DEFAULT_LOGDIR, "CWDReplacements.log")

def logReplacement(session, docIdNum, docType, verStat, verNum,
                   saveVer, savePub, comment):
    """
    Write a message to a log file in a program parsable format giving
    all details of the replacement.

    Pass:
        session - Used to get user ID.
        docIdNum- CDR doc ID.
        docType - Document type of docId.
        verStat - Sequence of version numbers from cdr.lastVersions().
        verNum  - Version number of doc made into CWD.
        saveVer - True = CWD saved as a version.
        savePub - True = CWD saved as publishable version.
        comment - User entered reason for the change.

    Return:
        Void, data is written to tab separated fields in the log file.
    """
    # Format parts needed for logging
    dateTime = time.strftime("%Y-%m-%d %H:%M:%S")

    # User ID
    result = cdr.idSessionUser(session, session)
    if type(result) not in (type(()), type([])):
        cdrcgi.bail("Unable to generate logging info: %s" % result)
    userId = result[0].encode('ascii', 'ignore')

    # Full message
    msg = "%s\t%d\t%s\t%s\t%d\t%d\t%s\t%s\t%s\t%s\t%s\n" % \
          (dateTime,docIdNum,docType,userId,verStat[0],verStat[1],verStat[2],
           verNum, saveVer,savePub,comment)

    # Log it
    try:
        fp = open(LOGFILE, "a")
        fp.write(msg)
        fp.close()
    except IOError, info:
        cdrcgi.bail("Error writing logfile %s: %s" % (LOGFILE, info))


fields = cgi.FieldStorage()
if not fields:
    cdrcgi.bail("Unable to load form fields - aborting")

session = cdrcgi.getSession(fields)
if not session:
    cdrcgi.bail("Unknown or expired session, please login")

# Get expected fields
docIdStr   = fields.getvalue("docId", None)
verStr     = fields.getvalue("verStr", None)
saveNewVer = fields.getvalue("saveNewVer", None)
savePub    = fields.getvalue("savePub", None)
comment    = fields.getvalue("comment", "")

# Action buttons
action = cdrcgi.getRequest(fields)
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
if action == "Log Out":
    cdrcgi.logout(session)
if action == "Confirm":
    confirmed = True
else:
    confirmed = False
if action == "Cancel":
    # Force re-input of data by clearing version
    verStr = None

# Check authorization to use this function
if not cdr.canDo(session, "REPLACE CWD WITH VERSION"):
    cdrcgi.bail(
     "Sorry, you are not authorized to promote a version to become "
     " the current working document")

# Did we get what we needed
if docIdStr and verStr:
    # Normalize ids to CDR0000012345, 12345
    (docIdStr, docIdNum, dontcare) = cdr.exNormalize(docIdStr)

    # Normalize checkboxes
    if savePub and savePub != 'N':
        savePub = 'Y'
    else:
        savePub = 'N'
    if saveNewVer and saveNewVer != 'N':
        saveNewVer = 'Y'
    else:
        saveNewVer = 'N'

    # If making version publishable, we're making a version
    if savePub == 'Y':
        saveNewVer = 'Y'

    # Validate docId and get type
    conn = cdrdb.connect()
    cursor = conn.cursor()
    docType = None
    docTitle = None
    try:
        cursor.execute("""
         SELECT t.name, d.title FROM doc_type t
           JOIN document d
             ON d.doc_type = t.id
          WHERE d.id = ?""", (docIdNum,))
        row = cursor.fetchone()
        if row:
            docType  = row[0]
            docTitle = row[1]

    except cdrdb.Error, info:
        cdrcgi.bail("Database error fetching doc type: %s" % str(info))

    # Did we find a doc type?  Also means we found a doc
    if docType:
        # Is the user authorized for this specific doctype?
        if not cdr.canDo(session, "MODIFY DOCUMENT", docType):
            cdrcgi.bail(
             "Sorry, you are not authorized to update documents of type %s" %
             docType)

        # Is there a version specified?
        if not verStr or not int(verStr):
            cdrcgi.bail("You must specify a numeric version number")

        # Get max version info
        verStatus = cdr.lastVersions(session, docIdStr)
        lastVer, lastPubVer, isChanged = verStatus

        # Normalize version to positive integer
        verNum = int(verStr)
        if verNum < 0:
            # e.g. verNum = 20 + (-1) + 1 = 20
            verNum = lastVer + verNum + 1
        if verNum < 1 or verNum > lastVer:
            cdrcgi.bail("Version not found.  There are %d versions" % lastVer)

        # More human readable Y/N flags
        showSavePub = "False"
        if savePub == 'Y':
            showSavePub = "True"
        showNewVer = "False"
        if saveNewVer == 'Y':
            showNewVer = "True"

        # If not confirmed, tell user what we'll do and get confirmation
        if not confirmed:
            buttons = ("Confirm", "Cancel") + BUTTONS
            html = cdrcgi.header(TITLE, TITLE, "Please confirm",
                                 script=SCRIPT, buttons=buttons) + """
<h1>Please confirm action</p>

<p>The following actions will be performed:</p>

<center>
<table border='2'>
 <tr>
  <td>Replace CWD for docId</td><td>%s</td>
 </tr>
 <tr>
  <td>Doc Type</td><td>%s</td>
 </tr>
 <tr>
  <td>Doc Title</td><td>%s</td>
 </tr>
 <tr>
  <td>Current total versions</td><td>%d</td>
 </tr>
 <tr>
  <td>Make this version the CWD</td><td>%d</td>
 </tr>
 <tr>
  <td>Also create new version</td><td>%s</td>
 </tr>
 <tr>
  <td>Make new version publishable</td><td>%s</td>
 </tr>
 <tr>
  <td>Reason to be logged</td><td>%s</td>
 </tr>
</table>

<p>Click <strong>Confirm</strong> to confirm these actions
or <strong>Cancel</strong> to re-enter data.</p>

<input type='hidden' name='%s' value='%s' />
<input type='hidden' name='docId' value='%s' />
<input type='hidden' name='verStr' value='%d' />
<input type='hidden' name='saveNewVer' value='%s' />
<input type='hidden' name='savePub' value='%s' />
<input type='hidden' name='comment' value='%s' />
<center>
</form>
</body>
</html>
""" % (docIdStr, docType, docTitle, lastVer, verNum,
       showNewVer, showSavePub, comment,
       cdrcgi.SESSION, session,
       docIdStr, verNum, saveNewVer, savePub, comment)

            cdrcgi.sendPage(html)

        else:
            # If we got here, we're ready to go
            # Get requested version
            try:
                doc = cdr.getDoc(session, docIdStr, checkout='Y',
                                 version=verNum, getObject=True)
            except Exception as e:
                cdrcgi.bail("Unable to check out version: {}".format(e))

            # Validation flag
            if savePub == 'Y':
                valDoc = 'Y'
            else:
                valDoc = 'N'

            # Insure that saved comment has full info
            comment = "Replacing CWD with version %d: %s" % (verNum, comment)

            # Save it
            resp = cdr.repDoc(session, doc=str(doc), checkIn='Y', val=valDoc,
                              ver=saveNewVer, verPublishable=savePub,
                              comment=comment, showWarnings=True)

            # Expecting (docId, error string)
            # If no docId, there were errors
            # If no error string there weren't
            # If both, save was successful but there were warnings
            errors = []
            if resp[1]:
                errors = cdr.getErrors(resp[1], errorsExpected=False,
                                       asSequence=True)
            if not resp[0]:
                # Null docID means errors were fatal
                html = "<h2>Document save <strong>failed</strong></h2>\n"
            else:
                logReplacement(session, docIdNum, docType, verStatus, verNum,
                               saveNewVer, savePub, comment)
                html = "<h2>Document save <strong>successful</strong></h2>\n"

            if errors:
                html += "<p>Messages were returned:</p>\n<ul>\n"
                for err in errors:
                    html += " <li>%s</li>\n" % err
                html += "</ul>\n"

            html += "<input type='hidden' name='%s' value='%s' />" % (
                      cdrcgi.SESSION, session)

            buttons = (cdrcgi.MAINMENU, "Log Out")
            html = cdrcgi.header(TITLE, TITLE, "Action complete",
                                 script=SCRIPT, buttons=buttons) + html + \
                                 "</form>\n</body>\n</html>\n"
            cdrcgi.sendPage(html)



#--------------------------------------------------------------
# Main form
#
# If we got here, there was insufficient data, put up the main form.
#--------------------------------------------------------------
buttons = ("Submit", cdrcgi.MAINMENU, "Log Out")
html = cdrcgi.header(TITLE, TITLE, "Please enter request information",
                     script=SCRIPT, buttons=buttons) + """

<h1>Replace CWD with earlier version</h1>

<p>This program will replace the current working version of a document
with the XML text of an earlier version.  It can be used to restore the
status of a document after it was damaged in some way.</p>

<strong>Warning!  Replacing the CWD with an older version will obscure and
complicate the true version history and will override recent changes.
Therefore this function should be used very sparingly, only when there is a
serious problem with the CWD that cannot be recovered by a simple
edit.</strong>

<p>Please enter the following information for the document:</p>

<center>
<table border='0'>
 <tr>
  <td align='right'>Doc ID to process<strong>*</strong>:</td>
  <td><input type='text' width='12' name='docId' /></td>
 </tr>
 <tr>
  <td align='right'>Version number to promote to CWD<strong>*</strong>:<br />
                   (or -1 = last, -2 = next last, etc.)
  </td>
  <td><input type='text' width='12' name='verStr' /></td>
 </tr>
 <tr>
  <td align='right'>Also create new version:</td>
  <td><input type='checkbox' name='saveNewVer' value='Y' /></td>
 </tr>
 <tr>
  <td align='right'>Make new version publishable:</td>
  <td><input type='checkbox' name='savePub' value='Y' /></td>
 </tr>
 <tr>
  <td align='right'>Log this comment:</td>
  <td><textarea name='comment' rows='4' cols='30'></textarea></td>
 </tr>
</table>
<br /><strong>*</strong> = required fields
<input type='hidden' name='%s' value='%s' />
<center>
</form>
</body>
</html>
""" % (cdrcgi.SESSION, session)

cdrcgi.sendPage(html)
