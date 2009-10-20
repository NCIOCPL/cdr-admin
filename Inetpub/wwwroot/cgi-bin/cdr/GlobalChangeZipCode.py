#----------------------------------------------------------------------
# Perform global change of Person SpecificPostalAddress zip codes when
# an associated Organization zip code changes.
#
# $Id$
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2009/04/17 04:41:01  ameyer
# Initial version.
#
#----------------------------------------------------------------------

# Useful for testing, but for production, let's keep any tracebacks
#  in the standard GlobalChange.log file
# import cgitb; cgitb.enable()

import cgi, cdr, cdrcgi, cdrdb, cdrbatch
import lxml.etree as etree

# Logfile
LF=cdr.DEFAULT_LOGDIR + "/GlobalChange.log"

# Name of job for batch_job table
JOB_NAME = "Global Change Zipcode"
JOB_HTML_NAME = "GlobalChangeZip"


#----------------------------------------------------------------------
# Encapsulate parameters from all forms
#----------------------------------------------------------------------
class Parms:
    """
    Holds all form parameters for convenience of passing them around.
    """

    def __init__(self, fields):
        """
        Pass:
            fields - return value of cgi.FieldStorage()
        """
        # Validate user session
        self.__session = cdrcgi.getSession(fields)
        if not self.__session:
            cdrcgi.bail ("Unknown or expired CDR session.", logfile=LF)

        # Other form variables
        self.__orgId    = None
        self.__orgIdStr = fields.getvalue("orgId", '')
        self.__orgName  = fields.getvalue("orgName", '')
        self.__oldZip   = fields.getvalue("oldZip", '')
        self.__newZip   = fields.getvalue("newZip", '')
        self.__runMode  = fields.getvalue("runMode", '')
        self.__email    = fields.getvalue("email", '')

        # Info based on the Organization CDR ID
        if self.__orgIdStr:
            # Create integer form
            try:
                self.__orgId = cdr.exNormalize(self.__orgIdStr)[1]
            except cdr.Exception, info:
                cdrcgi.bail("Unable to convert Org CDR ID '%s': %s" %
                             self.__orgIdStr, str(info))

            # Discard user orgName if any and align orgName with ID
            try:
                conn   = cdrdb.connect()
                cursor = conn.cursor()
                cursor.execute("SELECT title FROM document WHERE id=?",
                                self.__orgId)
                row    = cursor.fetchone()
            except cdrdb.Error, info:
                cdrcgi.bail("Database error fetching Org name: %s" % info,
                            logfile = LF)
            if row:
                self.__orgName = row[0]

        # Normalize zip codes
        if self.__oldZip:
            self.__oldZip = normalizeZip(self.__oldZip, "Old zip code")
        if self.__newZip:
            self.__newZip = normalizeZip(self.__newZip, "Old zip code")

    # Make everything available, read-only
    @property
    def orgName(self): return self.__orgName
    @property
    def orgIdStr(self): return self.__orgIdStr
    @property
    def orgId(self): return self.__orgId
    @property
    def oldZip(self): return self.__oldZip
    @property
    def newZip(self): return self.__newZip
    @property
    def runMode(self): return self.__runMode
    @property
    def email(self): return self.__email
    @property
    def session(self): return self.__session


def makeHiddenParms(parms):
    """
    Create a block of html with all of the parameters hidden in it.

    Pass:
        Form parameters.
    """
    html = """
<input type='hidden' name='orgId' value='%d' />
<input type='hidden' name='orgName' value='%s' />
<input type='hidden' name='oldZip' value='%s' />
<input type='hidden' name='newZip' value='%s' />
<input type='hidden' name='runMode' value='%s' />
<input type='hidden' name='email' value='%s' />
""" % (parms.orgId, parms.orgName, parms.oldZip, parms.newZip,
       parms.runMode, parms.email)

    return html


#----------------------------------------------------------------------
# Generate a page in uniform style for form
#----------------------------------------------------------------------
def sendGlblChgPage(session, formContent, subBanner=None, buttons='default'):

    """
    Generate an HTML page in our standard style with all saved
    state information, buttons, etc.

    Send it to the browser.

    Pass:
        Page header sub-banner.
        Contents of the form, as HTML.
    """
    # Fixed header values
    if buttons == 'default':
        buttons = ('Submit', 'Cancel')
    title   = "CDR Global Change Zip Code"
    script  = "GlobalChangeZipCode.py"
    if not subBanner:
        subBanner = title

    # Create an overall header using the common header code
    html = cdrcgi.header (title, title, subBanner, script, buttons)

    # Add form contents
    html += formContent

    # Add session variable to every form
    html += "\n<input type='hidden' name='%s' value='%s' />\n" % \
             (cdrcgi.SESSION, session)

    # Form termination
    html += "\n</form>\n</body>\n</html>\n"

    cdrcgi.sendPage (html)


def sendInitialScreen(parms):
    """
    Construct the initial input screen for user specified parameters.

    Pass:
        Parameter object.
    """
    # Set default runmode to 'test' if not already set
    if parms.runMode == 'live':
        liveChecked = " checked='checked'"
        testChecked = ""
    else:
        liveChecked = ""
        testChecked = " checked='checked'"

    # Set default email address to current user's if not already set
    email = parms.email
    if not email:
        email = cdr.getEmail(parms.session)

    # Form content
    html = """
<p>Please enter parameters for global change of specific postal
address zip code for Persons linked to an organization whose zip
code has changed.</p>

<table border='0'>
<tr><td align='right'>Organization Name: </td>
    <td><input type='text' name='orgName' size='60' value='%s' /></td></tr>
<tr><td align='right'>or Organization CDR ID: </td>
    <td><input type='text' name='orgId' size='15' value='%s' /></td></tr>
<tr><td align='right'>Old 5-digit zip code: </td>
    <td><input type='text' name='oldZip' size='5' value='%s' /></td></tr>
<tr><td align='right'>New 5-digit zip code: </td>
    <td><input type='text' name='newZip' size='5' value='%s' /></td></tr>
</table>

<p>Select global change run mode:
<input type='radio' name='runMode' value='test'%s>test</input> &nbsp;
<input type='radio' name='runMode' value='live'%s>live</input>
</p>

<p>Enter list of comma separated email addresses for report:</p>
<input type='text' size='85' name='email' value='%s' />

""" % (parms.orgName, parms.orgIdStr, parms.oldZip, parms.newZip,
       testChecked, liveChecked, email)

    sendGlblChgPage (parms.session, html, "Input global change parameters")


def sendOrgPickList(parms):
    """
    Generate and display a pick list form for selecting a specific
    Organization matching a user entered Organization name.

    Pass:
        Form parameters.
    """
    qry = """
SELECT TOP 100 d.id, d.title
  FROM document d
  JOIN doc_type t ON d.doc_type = t.id
 WHERE d.title LIKE '%s%%'
   AND t.name = 'Organization'
 ORDER BY d.title""" % parms.orgName

    # Search for Org docs matching user entered name
    rows = None
    try:
        conn   = cdrdb.connect()
        cursor = conn.cursor()
        cursor.execute(qry)
        rows   = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Database error creating Org picklist: %s" % info,
                    logfile = LF)

    # No hits?
    if not rows or not len(rows):
        cdrcgi.bail(
          "No Organizations match '%s', please press Back and try again" %
          orgName)

    # Create a page with the picklist
    htmlArray = []
    htmlArray.append(u"""
<style type='text/css'>
 option { font-family: monospace }
</style>
<p>Please choose a specific Organization from those matching "%s..."</p>
<select name='orgId' size='15'>
""" % parms.orgName)

    for row in rows:
        orgId = row[0]
        name  = row[1]

        # Make the ID number fixed width
        leadSpaces = 8 - len(str(orgId))
        optStr = ""
        while leadSpaces > 0:
            optStr += "&nbsp;"
            leadSpaces -= 1
        optStr = "%s%d: %s" % (optStr, orgId, name)
        htmlArray.append(u"  <option value=%d>%s</option>" % (orgId, optStr))

    html = u"".join(htmlArray)

    html += u"""
</select>

<input type='hidden' name='oldZip' value='%s' />
<input type='hidden' name='newZip' value='%s' />
<input type='hidden' name='runMode' value='%s' />
<input type='hidden' name='email' value='%s' />

</body>
</html>""" % (parms.oldZip, parms.newZip, parms.runMode, parms.email)
    sendGlblChgPage(parms.session, html, "Pick a specific Organization")


def validateOrg(parms):
    """
    Validate the document specified by orgId.  It must be an Organization.
    The new zip code must be in the document.  The old one must not.

    Bail out if error.

    Pass:
        Form parameters.
    """
    # Get the document and parse it for zip codes
    try:
        conn   = cdrdb.connect()
        cursor = conn.cursor()
        cursor.execute("""
          SELECT t.name, d.xml
            FROM document d
            JOIN doc_type t ON d.doc_type = t.id
           WHERE d.id=?""", parms.orgId)
        row = cursor.fetchone()
    except cdrdb.Error, info:
        cdrcgi.bail("Database error fetching doc for Org ID=%d: %s" %
                     (parms.orgId, str(info)))

    # Doc exists
    if not row:
        cdrcgi.bail("No active document exists with ID=%d" % parms.orgId)

    # It's an Org
    docType = row[0]
    xml     = row[1]
    if docType != 'Organization':
        cdrcgi.bail("Document %d is a %s, not an Organization" %
                     (parms.orgId, docType))

    # There must be a zip code in the document
    docTree  = etree.fromstring(xml.encode('utf-8'))
    zipNodes = docTree.findall("OrganizationLocations/OrganizationLocation" +
                               "/Location/PostalAddress/PostalCode_ZIP")
    if not zipNodes:
        cdrcgi.bail("No zip codes found in Organization %d" % parms.orgId)

    # Check all the addresses.  Caller should not be running on non-US
    foundOldZip = False
    foundNewZip = False
    zips = ""
    for zipNode in zipNodes:
        zip = zipNode.text[:5]
        if zip == parms.oldZip:
            foundOldZip = True
        if zip == parms.newZip:
            foundNewZip = True
        zips += "  %s" % zip

    # cdrcgi.bail("Found these zip codes: %s" % zips)

    if not foundNewZip:
        cdrcgi.bail("New zip code %s not found in Organization %d" %
                     (parms.newZip, parms.orgId))
    if foundOldZip:
        cdrcgi.bail(
    "Old zip code %s is still in Organization %d.  Global change is unsafe." %
                         (parms.oldZip, parms.orgId))

    # If we got here, we're okay


def normalizeZip(zipStr, zipName):
    """
    Make sure we have 5 digit zip codes.

    Pass:
        Zip code as a string.
        Name to display if error, e.g., "Old zip code"

    Return:
        Normalized zip code string or bail out.
    """
    normZip = zipStr.strip()[:5]
    try:
        chkzip  = str(int(normZip))
        if len(normZip) != 5:
            raise TypeError
    except TypeError:
        cdrcgi.bail("%s must be exactly 5 decimal digits, not %s" %
                     (zipName, zipStr))
    return normZip


def finalConfirm(parms):
    """
    Request final confirmation from the user.

    Pass:
        Form parameters.
    """
    html = """
<p>Click "Submit" to start a batch job with the following parameters.</p>

<table border='0'>
<tr><td align='right'>Organization Name: '</td><td>%s</td></tr>
<tr><td align='right'>or Organization CDR ID: '</td><td>%d</td></tr>
<tr><td align='right'>Old 5-digit zip code: '</td><td>%s</td></tr>
<tr><td align='right'>New 5-digit zip code: '</td><td>%s</td></tr>
<tr><td align='right'>Run mode: '</td><td>%s</td></tr>
<tr><td align='right'>Email: '</td><td>%s</td></tr>
</table>

<p>Otherwise click "Cancel".</p>
""" % (parms.orgName, parms.orgId, parms.oldZip, parms.newZip,
       parms.runMode, parms.email)

    html += makeHiddenParms(parms)
    html += "\n<input type='hidden' name='confirmed' value='yes' />\n"

    sendGlblChgPage(parms.session, html, "Final confirmation")


##----------------------------------------------------------------------
##----------------------------------------------------------------------
## START OF MAIN
##----------------------------------------------------------------------
##----------------------------------------------------------------------

# Parse form variables
fields = cgi.FieldStorage()
if not fields:
    cdrcgi.bail ("Unable to load form fields - should not happen!", logfile=LF)

# Retrieve all parameters
parms = Parms(fields)

# Check authorization
if not cdr.canDo (parms.session, "MAKE GLOBAL CHANGES", "Person"):
    cdrcgi.bail ("Sorry, user not authorized to make these global changes",
                  logfile=LF)

# Is user cancelling global change operations?
action = cdrcgi.getRequest(fields)
if action in ("Cancel", cdrcgi.MAINMENU):
    # Cancel button pressed.  Return user to admin screen
    cdrcgi.navigateTo ("Admin.py", parms.session)

# Don't allow two global changes to run concurrently
countRunning = 0
try:
    # Gets number of active Global Change jobs
    countRunning = cdrbatch.activeCount (JOB_NAME)
except cdrbatch.BatchException, e:
    cdrcgi.bail (str(e), logfile=LF)
if countRunning > 0:
    cdrcgi.bail ("""
Another global change job is still active.<br>
Please wait until it completes before starting another.<br>
See <a href='getBatchStatus.py?Session=%s&jobName=%s&jobAge=1'>
<u>Batch Status Report</u></a>
or go to the CDR Administration menu and select 'View Batch Job Status'.</p>
<p><p><p>""" % (parms.session, JOB_HTML_NAME))

# Gather input parameters if first screen or not all parms entered in first
if not ((parms.orgId or parms.orgName) and parms.oldZip and parms.newZip
         and parms.runMode and parms.email):
    sendInitialScreen(parms)

# If user entered Org name but no ID, get him to be specific
if not parms.orgId:
    sendOrgPickList(parms)

# Make sure organization is okay
validateOrg(parms)

# Last step is final confirmation confirmation
confirm = fields.getvalue("confirmed", None)
if not confirm:
    finalConfirm(parms)

# Setup parameters for job
response = cdr.idSessionUser(parms.session, parms.session)
if type(response) in (type(""), type(u"")):
    cdrcgi.bail("Internal session error: %s" % response)
usrId = response[0]
pw    = response[1]
args  = (('usrId', usrId),
         ('pw', pw),
         ('orgId', parms.orgId),
         ('oldZip', parms.oldZip),
         ('newZip', parms.newZip),
         ('runMode', parms.runMode))
cmd   = cdr.BASEDIR + "/Utilities/OldZipToNewGlobalBatch.py"

# Start the job
cdr.logwrite(
"""
About to launch batch job to change Person specific address zip codes.
      User: %s
Parameters:
     orgId = %s
    oldZip = %s
    newZip = %s
     Email = %s
""" % (usrId, parms.orgId, parms.oldZip, parms.newZip, parms.email))
batchJob = cdrbatch.CdrBatch(jobName=JOB_NAME, command=cmd,
                             args=args, email=parms.email)
try:
    batchJob.queue()
except Exception, info:
    cdrcgi.bail("Unable to start batch job: " + str(info), logfile=LF)

# Inform user
html = """
<h4>The global change has been queued for batch processing</h4>
<p>To monitor the status of the job, click this
<a href='getBatchStatus.py?Session=%s&jobId=%s'><u>link</u></a>
or go to the CDR Administration menu and select 'View Batch Job Status'.</p>
""" % (parms.session, batchJob.getJobId())

buttons = ((cdrcgi.MAINMENU,))
sendGlblChgPage(parms.session, html, "Global change has been queued",
                buttons=buttons)
