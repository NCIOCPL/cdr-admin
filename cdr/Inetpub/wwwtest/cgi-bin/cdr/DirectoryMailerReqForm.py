#----------------------------------------------------------------------
#
# $Id: DirectoryMailerReqForm.py,v 1.13 2002-11-08 03:07:50 ameyer Exp $
#
# Request form for all directory mailers.
#
# Selection criteria for documents to mail include:
#   Must be person or organization documents.
#   Must be under version control, latest version is selected, whether
#     or not it is publishable.
#   Unless individual doc id entered by user, the mailer history for
#     the document must meet criteria for mailer type:
#       Initial mailers - Never mailed before.
#                         Marked "ready for review".
#       Update mailers  - Minimum 12 months since last mailer.
#       Remailers       - No response rcvd to initial or update in 60 days.
#
# This program is invoked twice to  create a mailer job.
#
# The first invocation is made by a high level mailer menu from which
# a user selected directory mailers.  In the first invocation, the program
# detects that no specific mailer has been requested ("if not request")
# and returns an input form to the web browser to gather information
# needed to start a specific mailer job.
#
# When a user responds to the form, we get the input here in a second
# invocation.  We then validate the input and setup the requested mailer
# publication job for the publishing daemon to find and initiate.
#
# Based on an original request form for new physician initial mailers by
# Bob Kline.
#
# $Log: not supported by cvs2svn $
# Revision 1.12  2002/11/08 02:35:07  ameyer
# Revised user interface to match Lakshmi's change request.
#
# Revision 1.11  2002/11/01 05:25:45  ameyer
# Changed form of parameter passed to remail selector.
# Added publishable='Y' to version selection (forgot to comment this
# in previous checkin.)
#
# Revision 1.10  2002/11/01 02:44:44  ameyer
# Fix top document/distinct selection commands.
#
# Revision 1.9  2002/10/22 21:54:26  ameyer
# Added user control to limit the number of docs selected for mailing.
#
# Revision 1.8  2002/10/09 15:23:06  ameyer
# Optimized queries - run significantly faster.
# Set autocommit on.
#
# Revision 1.7  2002/10/03 20:33:35  ameyer
# About to change the queries yet again, and want to save this version.
#
# Revision 1.6  2002/10/03 17:38:43  ameyer
# Optimized physican annual update selection query.  Still untested.
#
# Revision 1.4  2002/09/26 15:13:55  ameyer
# Revised queries for selecting docs, other development changes.
#
# Revision 1.2  2002/06/07 00:12:44  ameyer
# Continuing development.  This is still a pre-production version.
#
# Revision 1.1  2002/03/19 23:39:06  ameyer
# CGI portion of the directory mailer selection software.
# Displays menu, selects documents, initiates publishing job.
#
#
#----------------------------------------------------------------------
import sys, cgi, cdr, cdrcgi, re, string, cdrdb, cdrpubcgi, cdrmailcommon

#----------------------------------------------------------------------
# If we've been through the form already, gather form variables
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
docId   = fields and fields.getvalue("DocId")    or None
email   = fields and fields.getvalue("Email")    or None
userPick= fields and fields.getvalue("userPick") or None
maxMails= fields and fields.getvalue("maxMails") or 'No limit'

title   = "CDR Administration"
section = "Directory Mailer Request Form"
buttons = ["Submit", "Log Out"]
script  = 'DirectoryMailerReqForm.py'
header  = cdrcgi.header(title, title, section, script, buttons,
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
     If you want to, you can limit the number of directory documents for
     which mailers will be generated in a given job, by entering a
     maximum number.
    </li>
    <li>
     To generate mailers for a single directory entry, select type of mailer
     and enter the document ID of the Physician or Organization.
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
   <input type='radio' name='userPick' class='r' value='PhysInit'>
    <span class='r'>Physician-Initial</span><br>
   <input type='radio' name='userPick' class='r' value='PhysInitRemail'>
    <span class='r'>Physician-Initial remail</span><br>
   <input type='radio' name='userPick' class='r' value='PhysAnnUpdate'>
    <span class='r'>Physician-Annual update</span><br>
   <input type='radio' name='userPick' class='r' value='PhysAnnRemail'>
    <span class='r'>Physician-Annual remail</span><br>
   <input type='radio' name='userPick' class='r' value='OrgAnnUpdate'>
    <span class='r'>Organization-Annual update</span><br>
   <input type='radio' name='userPick' class='r' value='OrgAnnRemail'>
    <span class='r'>Organization-Annual remail</span><br>
   <br><br><br>
   <b>Limit maximum number of mailers generated:&nbsp;</b>
   <input type='text' name='maxMails' size='12' value='No limit' />
   <br><br><br>
   <h3>To generate mailer for a single Physician/Organization, enter</h3>
   <b>Directory document CDR ID:&nbsp;</b>
   <input name='DocId' />
   <br><br><br>
   <h3>To receive email notification when mailer is complete, enter</h3>
   <b>Email address:&nbsp;</b>
   <input name='Email' />
   <br><br><br>
   <input type='Submit' name = 'Request' value = 'Submit'>
   <input type='hidden' name='%s' value='%s'>
  </form>
""" % (section, cdrcgi.SESSION, session)
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
if userPick == None:
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
# Set variables based on user selections on CGI form:
#   docType     = Document type of document to be mailed.
#   timeType    = Why we're mailing - 'Initial', 'Update', or 'Remail'
#   mailType    = MailerType enumeration from the Mailer tracking doc schema
#   orgMailType = For a remailer, the original mailType we are remailing
#----------------------------------------------------------------------
if userPick == 'PhysInit':
    docType     = 'Person'
    timeType    = 'Initial'
    mailType    = 'Physician-Initial'
elif userPick == 'PhysInitRemail':
    docType     = 'Person'
    timeType    = 'Remail'
    mailType    = 'Physician-Initial remail'
    orgMailType = 'Physician-Initial'
elif userPick == 'PhysAnnUpdate':
    docType     = 'Person'
    timeType    = 'Update'
    mailType    = 'Physician-Annual update'
elif userPick == 'PhysAnnRemail':
    docType     = 'Person'
    timeType    = 'Remail'
    mailType    = 'Physician-Annual remail'
    orgMailType = 'Physician-Annual update'
elif userPick == 'OrgAnnUpdate':
    docType     = 'Organization'
    timeType    = 'Update'
    mailType    = 'Organization-Annual update'
elif userPick == 'OrgAnnRemail':
    docType     = 'Organization'
    timeType    = 'Remail'
    mailType    = 'Organization-Annual remail'
    orgMailType = 'Organization-Annual update'

#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrPublishing')
    conn.setAutoCommit (1)
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Find the publishing system control document.
#----------------------------------------------------------------------
try:
    cursor = conn.cursor()
    cursor.execute("""\
        SELECT d.id
          FROM document d
          JOIN doc_type t
            ON t.id    = d.doc_type
         WHERE t.name  = 'PublishingSystem'
           AND d.title = 'Mailers'
""", timeout=90)
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
    digits = re.sub('[^\d]+', '', docId)
    intId  = int(digits)

    # Make sure the corresponding document exists in version control
    try:
        cursor.execute("""\
            SELECT MAX(num)
              FROM doc_version
             WHERE id = ?
               AND publishable = 'Y'
            """, (intId,))
        row = cursor.fetchone()

        # Document list contains one tuple of doc id + version number
        docList = ((intId, row[0]),)
    except cdrdb.Error, info:
        cdrcgi.bail("No version found for document %d: %s" % (intId,
                                                              info[1][0]))

    # Validate that document matches type implied by mailer type selection
    try:
        cursor.execute ("""\
            SELECT name
              FROM doc_type t, document d
             WHERE t.id = d.doc_type
               AND d.id = %d""" % intId)
        row = cursor.fetchone()
        if (row[0] != docType):
            cdrcgi.bail ("Document %d is of type %s, expecting type %s" %
                         (intId, row[0], docType))
    except cdrdb.Error, info:
        cdrcgi.bail("Unable to find document type for id = %d: %s" %
                    (intId, info[1][0]))


else:
    #------------------------------------------------------------------
    # Create queries for the correct document and mailer type.
    #
    # Two queries are created for each type of original mailer
    # (remailers are done differently).
    #
    # One query creates a temporary table of id's of mailers that
    # went out in the last year - indicating that no new mailer is
    # needed, and one selects candidates for mailing, which then
    # drop out ones for which mailers have already been sent (because
    # they are found in the temporary table.
    #
    # The original version of this didn't use a temporary table,
    # but the temp table speeds things up dramatically.
    #------------------------------------------------------------------
    if mailType == 'Physician-Initial':
        # ID's of docs not requiring an initial mailer because
        #   they've already had one
        tmpQry = """
            INSERT INTO #already_mailed_ids (tmpid)
                    SELECT DISTINCT pd2.doc_id
                      FROM pub_proc_doc pd2
                      JOIN pub_proc p2
                        ON p2.id = pd2.pub_proc
                     WHERE
                       (
                            p2.pub_subset = 'Physician-Initial'
                         OR
                            p2.pub_subset = 'Physician-Annual update'
                       )
                       AND p2.status <> 'Failure'
        """
        # Main query:
        # Select last version (not CWD) of document for which:
        #   Doc_type = Person.
        #   Doc is marked ready_for_review ("Ready for Pre-Publication Mailer"
        #       is checked on last save in XML editor client.)
        #   .../CurrentStatus = "Active".
        #   .../Directory/Include = "Pending".
        #   No non-failing mailer has previously been generated of
        #       of type Physician-Initial.
        qry = """
            SELECT TOP %d document.id, MAX(doc_version.num)
                       FROM doc_version
                       JOIN ready_for_review
                         ON ready_for_review.doc_id = doc_version.id
                       JOIN document document
                         ON document.id = ready_for_review.doc_id
                       JOIN query_term qstat
                         ON qstat.doc_id = document.id
                       JOIN query_term qinc
                         ON qinc.doc_id = document.id
                      WHERE qstat.path = '/Person/Status/CurrentStatus'
                        AND doc_version.publishable = 'Y'
                        AND qstat.value = 'Active'
                        AND qinc.path =
                           '/Person/ProfessionalInformation/PhysicianDetails/AdministrativeInformation/Directory/Include'
                        AND qinc.value = 'Pending'
                        AND NOT EXISTS (
                                SELECT tmpid
                                  FROM #already_mailed_ids
                                 WHERE document.id = tmpid
                             )
                   GROUP BY document.id""" % maxMailers

    elif mailType == 'Physician-Annual update':
        # Preselect all mailers sent to physicians in the last year.
        # Include initial, annual, and all remailers.
        tmpQry = """
            INSERT INTO #already_mailed_ids (tmpid)
                    SELECT DISTINCT pd2.doc_id
                      FROM pub_proc_doc pd2
                      JOIN pub_proc p2
                        ON p2.id = pd2.pub_proc
                     WHERE
                       (
                            p2.pub_subset = 'Physician-Initial'
                         OR
                            p2.pub_subset = 'Physician-Initial remail'
                         OR
                            p2.pub_subset = 'Physician-Annual update'
                         OR
                            p2.pub_subset = 'Physician-Annual remail'
                       )
                       AND p2.completed > DATEADD(year,-1,GETDATE())
                       AND p2.status <> 'Failure'
        """

        # Main query:
        # Select last version (not CWD) of document for which:
        #   Doc_type = Person.
        #   .../CurrentStatus = "Active".
        #   .../Directory/Include = "Include".
        #   There has been at least one previous mailer sent of type
        #       Physician-Initial, or Physician-Annual update.
        #   No non-failing mailer has been sent for this person in
        #       the last one year of any of the following types:
        #         Physician-Initial
        #         Physician-Initial remail
        #         Physician-Annual update
        #         Physician-Annual remail
        qry = """
            SELECT TOP %d document.id, MAX(doc_version.num)
                       FROM doc_version
                       JOIN document
                         ON doc_version.id = document.id
                       JOIN pub_proc_doc pd1
                         ON document.id = pd1.doc_id
                       JOIN pub_proc p1
                         ON pd1.pub_proc = p1.id
                       JOIN query_term qstat
                         ON qstat.doc_id = document.id
                       JOIN query_term qinc
                         ON qinc.doc_id = document.id
                      WHERE qstat.path = '/Person/Status/CurrentStatus'
                        AND doc_version.publishable = 'Y'
                        AND qstat.value = 'Active'
                        AND (
                             p1.pub_subset = 'Physician-Initial'
                          OR
                             p1.pub_subset = 'Physician-Annual update'
                            )
                        AND qinc.path =
                           '/Person/ProfessionalInformation/PhysicianDetails/AdministrativeInformation/Directory/Include'
                        AND qinc.value = 'Include'

                        -- But not if a mailer was sent in past year
                        AND NOT EXISTS (
                                SELECT tmpid
                                  FROM #already_mailed_ids
                                 WHERE document.id = tmpid
                             )
                   GROUP BY document.id""" % maxMailers

    elif mailType == 'Organization-Annual update':
        # Perform same optimization as for physicians
        # Preselect all mailers sent to orgs in last year
        tmpQry = """
            INSERT INTO #already_mailed_ids (tmpid)
                    SELECT DISTINCT pd2.doc_id
                      FROM pub_proc_doc pd2
                      JOIN pub_proc p2
                        ON p2.id = pd2.pub_proc
                     WHERE
                       (
                            p2.pub_subset = 'Organization-Annual update'
                         OR
                            p2.pub_subset = 'Organization-Annual remail'
                       )
                       AND p2.completed > DATEADD(year,-1,GETDATE())
                       AND p2.status <> 'Failure'
        """

        # Main query:
        # Select last version (not CWD) of document for which:
        #   Doc_type = Organization.
        #   .../IncludeInDirectory = "Include".
        #   .../OrganizationType <> "NCI division, office, or laboratory".
        #   .../OrganizationType <> "NIH institute, center or division".
        #   No non-failing update mailer sent in the past year.
        #   No non-failing remailer sent in the past year.
        qry = """
            SELECT DISTINCT TOP %d document.id, MAX(doc_version.num)
                       FROM doc_version
                       JOIN document
                         ON doc_version.id = document.id
                       JOIN query_term qinc
                         ON qinc.doc_id = document.id
                       JOIN query_term qorgtype
                         ON qorgtype.doc_id = document.id
                      WHERE qinc.path =
                           '/Organization/OrganizationDetails/OrganizationAdministrativeInformation/IncludeInDirectory'
                        AND doc_version.publishable = 'Y'
                        AND qinc.value = 'Include'
                        AND qorgtype.path = '/Organization/OrganizationType'
                        AND qorgtype.value <>
                                    'NCI division, office, or laboratory'
                        AND qorgtype.value <>
                                    'NIH institute, center, or division'

                        -- But not if a mailer was sent in past year
                        AND NOT EXISTS (
                                SELECT tmpid
                                  FROM #already_mailed_ids
                                 WHERE document.id = tmpid
                             )
                   GROUP BY document.id""" % maxMailers

    elif timeType == 'Remail':
        # Execute a query that builds a temporary table
        try:
            rms = cdrmailcommon.RemailSelector (conn)
            rms.select ("'%s'" % orgMailType, maxMailers=maxMailers)

            # And create one to fetch the doc ids from it
            qry = rms.getDocIdVerQuery()

        except cdrdb.Error, info:
            cdrcgi.bail('Database failure selecting remailers: %s'
                        % info[1][0])

    # Create the temp table - remailers are handled differently
    if timeType != 'Remail':
        try:
            cursor.execute ("CREATE TABLE #already_mailed_ids (tmpid int)")
        except cdrdb.Error, info:
            cdrcgi.bail("Failure creating temp table for mailers: %s" \
                        % info[1][0])

        # Fill it
        try:
            cursor.execute(tmpQry)
        except cdrdb.Error, info:
            cdrcgi.bail("Failure filling temp table for mailers: %s" \
                        % info[1][0])

    # Execute the main query to find all matching documents
    try:
        cursor.execute(qry)
        docList = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving document IDs: %s" % info[1][0])

# Log what we're doing
# Do we have any results?
docCount = len(docList)
if docCount == 0:
    cdrcgi.bail ("No documents found")

# Compose the docList results into a format that cdr.publish() wants
#   e.g., id=25, version=3, then form: "CDR0000000025/3"
# This works on a docList produced by a query, or produced by user entry
#   of a single document id
idVer = []
for pair in docList:
    idVer.append (cdr.exNormalize(pair[0])[0] + "/" + str(pair[1]))

# Information to be made available to batch portion of the job
jobParms = (('docType', docType), ('timeType', timeType))

# Drop the job into the queue.
result = cdr.publish (credentials=session, pubSystem='Mailers',
                      pubSubset=mailType, parms=jobParms, docList=idVer,
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
if timeType == 'Remail':
    rms.fillMailerIdTable(jobId)

cdrcgi.sendPage(header + html)
