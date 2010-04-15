#----------------------------------------------------------------------
#
# $Id$
#
# Request form for all genetics professional mailers.
#
# Selection criteria for documents to mail include:
#   Must be GP Person doc
#   Must have 
#   Must be under version control, latest version is selected, whether
#     or not it is publishable.
#   Unless individual doc id entered by user, the mailer history for
#     the document must meet criteria for mailer type:
#       Initial mailers - Never mailed before.
#       Update mailers  - Minimum 12 months since last mailer.
#       Remailers       - No response rcvd to initial or update in 60 days.
#
# Cloned (but heavily modified) from Alan's directory mailer request form.
#
# BZIssue::4630
#
#----------------------------------------------------------------------
import sys, cgi, cdr, cdrcgi, cdrdb, cdrmailcommon
etree = cdr.importEtree()
LOGFILE = cdrmailcommon.LOGFILE

#----------------------------------------------------------------------
# If we've been through the form already, gather form variables
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
session  = cdrcgi.getSession(fields)
request  = cdrcgi.getRequest(fields)
check    = fields.getvalue("precheck")
docId    = fields.getvalue("DocId")
email    = fields.getvalue("Email")
userPick = fields.getvalue("userPick")
maxMails = fields.getvalue("maxMails") or 'No limit'

title    = "CDR Administration"
section  = "Genetics Professional Mailer Request Form"
buttons  = ["Submit", "Log Out"]
script   = 'GPMailerReqForm.py'
header   = cdrcgi.header(title, title, section, script, buttons,
                            stylesheet = """\
 <style type='text/css'>
   ul { margin-left: 40pt }
   h2 { font-size: 14pt; font-family:Arial; color:navy }
   h3 { font-size: 13pt; font-family:Arial; color:black; font-weight:bold }
   li, span.r {
        font-size: 12pt; font-family:"Times New Roman"; color:black;
        margin-bottom: 10pt; font-weight:normal
   }
   b {  font-size: 12pt; font-family:"Times New Roman"; color:black;
        margin-bottom: 10pt; font-weight:bold
   }
  </style>
 """)
dirIncludePath = ('/Person/ProfessionalInformation/GeneticsProfessionalDetails'
                  '/AdministrativeInformation/Directory/Include')

#----------------------------------------------------------------------
# Confirm that this version of the specified document can get an emailer.
#----------------------------------------------------------------------
class GP:
    def __cmp__(self, other):
        return cmp(self.docId, other.docId)
    def __init__(self, docId, docVersion, cursor):
        self.docId = docId
        self.docVersion = docVersion
        self.title = self.email = None
        cursor.execute("""\
            SELECT xml, title
              FROM doc_version
             WHERE id = ?
               AND num = ?""", (docId, docVersion))
        rows = cursor.fetchall()
        if rows:
            docXml, self.title = rows[0]
            tree = etree.XML(docXml.encode('utf-8'))
            for location in tree.findall("PersonLocations/PrivatePractice"):
                usedFor = location.get('UsedFor')
                if usedFor and 'GPMailer' in usedFor:
                    for email in location.findall('PrivatePracticeLocation'
                                                 '/Email'):
                        self.email = email.text
            for location in tree.findall("PersonLocations"
                                         "/OtherPracticeLocation"):
                usedFor = location.get('UsedFor')
                if usedFor and 'GPMailer' in usedFor:
                    for email in location.findall('SpecificEmail'):
                        self.email = email.text
                        
def hasEmailAddress(docId, docVersion):
    filterSet = ['set:Mailer GeneticsProfessional Set']
    response = cdr.filterDoc('guest', filterSet, docId, docVer=docVersion)
    if type(response) in (str, unicode):
        raise cdr.Exception(response)
    tree = etree.XML(response[0])
    for contact in tree.findall('PRACTICELOCATIONS'):
        if contact.get('UsedFor') == 'GPMailer':
            for email in contact.findall('CEML'):
                if type(email.text) in (str, unicode):
                    if '@' in email.text:
                        return True
    return False

def getOriginalMailerType():
    return { "InitRemail": "Genetics Professional-Initial",
             "AnnRemail": "Genetics Professional-Annual update" }.get(userPick)

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out":
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Put up the form if we don't have a request yet.
#----------------------------------------------------------------------
if not request:
    form = """\
   <h2>%s</h2>
   <ul>
    <li>
     To generate mailers for a batch, select type of mailer.
     It may take a minute to select documents to be included in the mailing.
     Please be patient.
     If you want to, you can limit the number of documents for
     which mailers will be generated in a given job, by entering a
     maximum number.
    </li>
    <li>
     To generate mailers for a single genetics professional, select type
     of mailer and enter the document ID of the Person document.
    </li>
    <li>
     To receive email notification when the job is completed, enter your
     email address.
    </li>
    <li>
     Click Submit to start the mailer job.
    </li>
   </ul>
   <h3>Select type of mailer</h3>
   <input type='radio' name='userPick' class='r' value='Init'>
    <span class='r'>Genetics Professional-Initial</span><br>
   <input type='radio' name='userPick' class='r' value='InitRemail'>
    <span class='r'>Genetics Professional-Initial remail</span><br>
   <input type='radio' name='userPick' class='r' value='AnnUpdate'>
    <span class='r'>Genetics Professional-Annual update</span><br>
   <input type='radio' name='userPick' class='r' value='AnnRemail'>
    <span class='r'>Genetics Professional-Annual remail</span><br>
<!-- -->
   <br />
   <input type='checkbox' name='precheck' />
    <span class='r'>Only run pre-mailer check (not available for remailers)
    </span>
<!-- -->
   <br><br><br>
   <b>Limit maximum number of mailers generated:&nbsp;</b>
   <input type='text' name='maxMails' size='12' value='No limit' />
   <br><br><br>
   <h3>To generate mailer for a single genetics professional, enter</h3>
   <b>Person document CDR ID:&nbsp;</b>
   <input name='DocId' />
   <br><br><br>
   <h3>To receive email notification when mailer is complete, enter</h3>
   <b>Email address:&nbsp;</b>
   <input name='Email' value='%s'/>
   <br><br><br>
   <input type='Submit' name = 'Request' value = 'Submit'>
   <input type='hidden' name='%s' value='%s'>
  </form>
""" % (section, cdr.getEmail(session), cdrcgi.SESSION, session)
    #------------------------------------------------------------------
    # cdrcgi.sendPage exits after sending page.
    # If we sent a page, we're done for this invocation.
    # We'll be back if the user fills in the form and submits it.
    #------------------------------------------------------------------
    cdrcgi.sendPage(header + form + "</BODY></HTML>")


#----------------------------------------------------------------------
# Validate that user picked a mailer type
# We only get here on the second invocation - user filled in form
#----------------------------------------------------------------------
if not userPick:
    cdrcgi.bail ('Must select a directory mailer type')

#----------------------------------------------------------------------
# Figure out how many mailers to produce
# If user accepted default 'No limit' or put in anything other than
#   a number, we set the limit arbitrarily high
# But if user entered a number, it must be positive
#----------------------------------------------------------------------
try:
    maxMailers = int (maxMails)
except ValueError:
    maxMailers = sys.maxint
if maxMailers < 1:
    cdrcgi.bail ("Can't request less than 1 mailer")

#----------------------------------------------------------------------
# Get a document's title from the all_docs table.
#----------------------------------------------------------------------
def getDocTitle(cursor, docId):
    cursor.execute("SELECT title FROM document WHERE id = ?", docId)
    rows = cursor.fetchall()
    return rows and rows[0][0] or u"NO TITLE FOUND"

#----------------------------------------------------------------------
# Map the mailer type from the CGI form variable.
#----------------------------------------------------------------------
mailType = { "Init": "Genetics Professional-Initial",
             "InitRemail": "Genetics Professional-Initial remail",
             "AnnUpdate": "Genetics Professional-Annual update",
             "AnnRemail": "Genetics Professional-Annual remail" }.get(userPick)
if not mailType:
    cdrcgi.bail("Form data corrupted")
if check:
    class Problem:
        def __init__(self, docId, docVersion, cursor):
            self.docId = docId
            self.docVersion = docVersion
            self.title = getDocTitle(cursor, docId)
        def __cmp__(self, other):
            return cmp(self.docId, other.docId)
        @staticmethod
        def report(docList, problems):
            docList.sort()
            problems.sort()
            html = [u"""\
<html>
 <head>
  <style type='text/css'>
   * { font-family: Arial, sans-serif }
   h1 { font-size: 16pt }
  </style>
 </head>
 <body>
  <h1>%d GPs Without Email Address In GPMailer Block</h1>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>Document ID</th>
    <th>Document Version</th>
    <th>Document Title</th>
   </tr>
""" % len(problems)]
            for problem in problems:
                html.append(u"""\
   <tr>
    <td>%d</td>
    <td>%d</td>
    <td>%s</td>
   </tr>
""" % (problem.docId, problem.docVersion,
       problem.title and cgi.escape(problem.title) or "NO TITLE FOUND"))
            html.append(u"""\
  </table>
  <br />
  <h1>%d GPs Which Would Receive Mailers</h1>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>Document ID</th>
    <th>Document Version</th>
    <th>Document Title</th>
   </tr>
""" % len(docList))
            cursor = conn.cursor()
            for gp in docList:
                title = getDocTitle(cursor, docId)
                html.append(u"""\
   <tr>
    <td>%d</td>
    <td>%d</td>
    <td>%s</td>
   </tr>
""" % (gp.docId, gp.docVersion,
       gp.title and cgi.escape(gp.title) or "NO TITLE FOUND"))
            html.append(u"""\
  </table>
 </body>
</html>
""")
            cdrcgi.sendPage(u"".join(html))

    problems = []
    if "Remail" in userPick:
        cdrcgi.bail("Pre-mailer check is not available for remail jobs")
    if docId:
        cdrcgi.bail("Can't specify document ID for pre-mailer check")
else:
    cdr.logwrite("Creating %s job" % mailType, LOGFILE)

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrPublishing')
    conn.setAutoCommit (1)
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Find the publishing system control document.
#----------------------------------------------------------------------
if not check:
    try:
        cursor.execute("""\
        SELECT d.id
          FROM document d
          JOIN doc_type t
            ON t.id    = d.doc_type
         WHERE t.name  = 'PublishingSystem'
           AND d.title = 'Mailers'""", timeout=90)
        rows = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail('Database failure looking up control document: %s' %
                    info[1][0])
    if len(rows) < 1:
        cdrcgi.bail('Unable to find control document for Mailers')
    if len(rows) > 1:
        cdrcgi.bail('Multiple Mailer control documents found')
    ctrlDocId = rows[0][0]

#----------------------------------------------------------------------
# Determine which documents are to be published.
#----------------------------------------------------------------------
if docId:

    # Simple case - user submitted single document id, isolate the digits
    try:
        intId = cdr.exNormalize(docId)[1]
    except Exception, e:
        cdrcgi.bail(e)

    # Make sure the corresponding document exists in version control
    #   and is not blocked
    try:
        cursor.execute("""\
            SELECT MAX(v.num)
              FROM doc_version v
              JOIN active_doc a
                ON a.id = v.id
             WHERE v.id = ?""", intId)
        row = cursor.fetchone()
        if not row or not row[0]:
            cdrcgi.bail("CDR%d blocked or not versioned" % intId)

        # Document list contains one tuple of doc id + version number
        docVersion = row[0]
        docList = ((intId, docVersion),)
    except cdrdb.Error, info:
        cdrcgi.bail("Database error finding version for document %d: %s" % \
                    (intId, info[1][0]))

    # Verify that this is a GP with an email address.
    try:
        gp = GP(intId, docVersion, cursor)
        if not gp.email:
            cdrcgi.bail("No email address found in mailer contact block")
    except Exception, e:
        cdrcgi.bail("Failure looking for email address in mailer contact "
                    "block: %s" % e)

    # If it's a remailer, have to build a remail selector for it so
    #   rest of software knows what to do
    if 'remail' in mailType.lower():
        rms = cdrmailcommon.RemailSelector (conn)
        remailerFound = True
        try:
            if not rms.select("'%s'" % getOriginalMailType(), singleId=intId):
                remailerFound = False
        except Exception, e:
            cdrcgi.bail("failure finding original mailer for remail: %s" % e)
        if not remailerFound:
            cdrcgi.bail("Can't remail document - "
                        "no matching original mailer found")

else:
    #------------------------------------------------------------------
    # Build a list of tuples, each containing a document ID and document
    # version number of a GP which will get a mailer for this job.
    #------------------------------------------------------------------
    docList = []
    if mailType == 'Genetics Professional-Initial':

        # Who's already been sent a GP mailer?  Query takes less than a second.
        cursor.execute("""\
            SELECT DISTINCT d.doc_id
                       FROM pub_proc_doc d
                       JOIN pub_proc p
                         ON p.id = d.pub_proc
                      WHERE p.pub_subset LIKE 'Genetics Professional-%'
                        AND p.status <> 'Failure'
                        AND p.completed IS NOT NULL""", timeout=300)
        alreadyGotOne = set([row[0] for row in cursor.fetchall()])

        # Get the doc and version IDs of all of the candidate GPs
        # Takes about 7 seconds on Franck.
        cursor.execute("""\
            SELECT v.id, MAX(v.num)
              FROM doc_version v
              JOIN active_doc a
                ON a.id = v.id
              JOIN query_term q
                ON q.doc_id = v.id
             WHERE q.path = '%s'
               AND q.value = 'Include'
          GROUP BY v.id
          ORDER BY v.id""" % dirIncludePath, timeout=300)

        # Get as many documents as the user asked for.
        rows = cursor.fetchall()
        for docId, docVersion in rows:
            if docId in alreadyGotOne:
                continue
            try:
                # Verify that this is a GP with an email address.
                gp = GP(docId, docVersion, cursor)
                if not gp.email:
                    if check:
                        problems.append(gp)
                    else:
                        cdr.logwrite("no email address found in mailer "
                                     "contact block for version %d of CDR%d" %
                                 (docVersion, docId), LOGFILE)
                else:
                    docList.append(gp)
                    if len(docList) >= maxMailers:
                        break
            except Exception, e:
                if check:
                    problems.append(Problem(docId, docVersion, cursor))
                else:
                    cdr.logwrite("Failure looking for email address in mailer"
                                 "contact block of version %d of CDR%d: %s" %
                                 (docVersion, docId, e), LOGFILE)
        if check:
            Problem.report(docList, problems)
        else:
            docList = [(gp.docId, gp.docVersion) for gp in docList]
    elif mailType == 'Genetics Professional-Annual update':

        #----------------------------------------------------------------
        # Find the ones which last got a GP mailer longer than 12 months ago.
        # Give priority to the ones which have gone the longest without
        # getting a mailer.
        #----------------------------------------------------------------
        cursor.execute("""\
            SELECT DISTINCT d.doc_id, MAX(p.completed)
                       FROM pub_proc_doc d
                       JOIN pub_proc p
                         ON p.id = d.pub_proc
                       JOIN query_term q
                         ON q.doc_id = d.doc_id
                      WHERE p.pub_subset LIKE 'Genetics Professional-%%'
                        AND p.status <> 'Failure'
                        AND p.completed IS NOT NULL
                        AND q.path = '%s'
                        AND q.value = 'Include'
                   GROUP BY d.doc_id
                   ORDER BY MAX(p.completed), d.doc_id""" % dirIncludePath,
                       timeout=300)
        for docId, lastMailer in cursor.fetchall():

            # Get the latest version and make sure it's not blocked.
            cursor.execute("""\
                SELECT MAX(v.num)
                  FROM doc_version v
                  JOIN active_doc a
                    ON a.id = v.id
                 WHERE v.id = ?""", docId, timeout=300)
            rows = cursor.fetchall()
            if not rows:
                cdr.logwrite("skipping CDR%d, which is blocked" % docId,
                             LOGFILE)
            elif not rows[0][0]:
                cdr.logwrite("skipping CDR%d, which is not versioned" % docId)
            else:
                docVersion = rows[0][0]
                try:
                    gp = GP(docId, docVersion, cursor)
                    if not gp.email:
                        if check:
                            problems.append(gp)
                        else:
                            cdr.logwrite("no email address found in mailer "
                                         "contact block for version %d of "
                                         "CDR%d" %
                                         (docVersion, docId), LOGFILE)
                    else:
                        docList.append(gp)
                        if len(docList) >= maxMailers:
                            break
                except Exception, e:
                    if check:
                        problems.append(Problem(docId, docVersion, cursor))
                    else:
                        cdr.logwrite("Failure looking for email address in "
                                     "mailer contact block of version %d "
                                     "of CDR%d: %s" %
                                     (docVersion, docId, e), LOGFILE)
        if check:
            Problem.report(docList, problems)
        else:
            docList = [(gp.docId, gp.docVersion) for gp in docList]

    else:

        if 'remail' not in mailType.lower():
            cdrcgi.bail("unexpected mailer type '%s'" % mailType)
        # This is for a remailer: execute a query that builds a temporary table
        try:
            rms = cdrmailcommon.RemailSelector(conn)
            rms.select("'%s'" % getOriginalMailerType(), maxMailers=maxMailers)

            # And create and execute one to fetch the doc ids from it
            qry = rms.getDocIdVerQuery()
            cursor.execute(rms.getDocIdVerQuery())
            docList = cursor.fetchall()

        except cdrdb.Error, info:
            cdrcgi.bail('Database failure selecting remailers: %s' % info[1][0])

# Log what we're doing
# Do we have any results?
docCount = len(docList)
if docCount == 0:
    cdrcgi.bail ("No documents found that qualify for this mailer type")

# Compose the docList results into a format that cdr.publish() wants
#   e.g., id=25, version=3, then form: "CDR0000000025/3"
# This works on a docList produced by a query, or produced by user entry
#   of a single document id
idVer = ["CDR%010d/%d" % pair for pair in docList]

# Drop the job into the queue.
result = cdr.publish (credentials=session, pubSystem='Mailers',
                      pubSubset=mailType, parms=(), docList=idVer,
                      allowNonPub='Y', email=email)

# cdr.publish returns a tuple of job id + messages
# If serious error, job id = None
if not result[0] or int(result[0]) < 0:
    cdrcgi.bail("Unable to initiate publishing job:<br>%s" % result[1])

jobId = int(result[0])

# Log what happened
msgs = ["Started directory mailer job - id = %d" % jobId,
        "                      Mailer type = %s" % mailType,
        "          Number of docs selected = %d" % docCount]
if docCount > 0:
    msgs.append ("                        First doc = %s" % idVer[0])
if docCount > 1:
    msgs.append ("                       Second doc = %s" % idVer[1])
cdr.logwrite (msgs, cdrmailcommon.LOGFILE)

# Tell user how to get status
header = cdrcgi.header(title, title, section, None, [])
html = """\
    <H3>Job Number %d Submitted</H3>
    <B>
     <P>Mailer type = %s</P>
     <P>Number of documents to be mailed = %d</P>
     <P><FONT COLOR='black'>Use
      <A HREF='%s/PubStatus.py?id=%d'>this link</A> to view job status.
     </FONT>
     </P>
    </B>
   </FORM>
  </BODY>
 </HTML>
""" % (jobId, mailType, docCount, cdrcgi.BASE, jobId)

# Remailers require permanent storage of the associated ids
#  in the database, using job id as a key
if 'remail' in mailType.lower():
    rms.fillMailerIdTable(jobId)

cdrcgi.sendPage(header + html)
