#----------------------------------------------------------------------
#
# $Id: DirectoryMailerReqForm.py,v 1.7 2002-10-03 20:33:35 ameyer Exp $
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
import cgi, cdr, cdrcgi, re, string, cdrdb, cdrpubcgi, cdrmailcommon

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields  = cgi.FieldStorage()
session = cdrcgi.getSession(fields)
request = cdrcgi.getRequest(fields)
docId   = fields and fields.getvalue("DocId")    or None
email   = fields and fields.getvalue("Email")    or None
userPick= fields and fields.getvalue("userPick") or None
title   = "CDR Administration"
section = "Directory Mailer Request Form"
buttons = ["Submit", "Log Out"]
script  = 'DirectoryMailerReqForm.py'
header  = cdrcgi.header(title, title, section, script, buttons)

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
   <h2>Enter request parameters</h2>
   <b>Document ID and email notification address are both optional.
       If document ID is specified, only a mailer for that document
       will be generated; otherwise all eligible documents for which
       mailers have not yet been sent will have mailers generated.</b>
   <table>
    <tr>
     <th align='right' nowrap>
      <b>Directory document CDR ID: &nbsp;</b>
     </th>
     <td><input name='DocId' /></td>
    </tr>
    <tr>
     <th align='right' nowrap>
      <b>Notification email address: &nbsp;</b>
     </th>
     <td><input name='Email' /></td>
    </tr>
    <tr><td>&nbsp;</td></tr>
   </table>
   <p><p>
   <table>
    <tr><td><b>
     Select the directory mailer type to generate, then click Submit.<br>
     Please be patient, it may take a minute to select documents for mailing.
     <br>
    </b></td></tr>
    <tr><td><input type='radio' name='userPick'
          value='PhysInit'>Physician-Initial</input>
    </td></tr>
    <tr><td><input type='radio' name='userPick'
          value='PhysInitRemail'>Physician-Initial remail</input>
    </td></tr>
    <tr><td><input type='radio' name='userPick'
          value='PhysAnnUpdate'>Physician-Annual update</input>
    </td></tr>
    <tr><td><input type='radio' name='userPick'
          value='PhysAnnRemail'>Physician-Annual remail</input>
    </td></tr>
    <tr><td><input type='radio' name='userPick'
          value='OrgAnnUpdate'>Organization-Annual update</input>
    </td></tr>
    <tr><td><input type='radio' name='userPick'
          value='OrgAnnRemail'>Organization-Annual remail</input>
    </td></tr>
   </table>
   <input type='hidden' name='%s' value='%s'>

  </form>
""" % (cdrcgi.SESSION, session)
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
""")
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
             WHERE id = ?""", (intId,))
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
    # Create a query for the correct document and mailer type
    # A different query is required for each of the three mailer types.
    # Document types are passed in to the query creation and do not
    #   change the structure of the query.
    #------------------------------------------------------------------
    if mailType == 'Physician-Initial':
        # Select last version (not CWD) of document for which:
        #   Doc_type = Person.
        #   Doc is marked ready_for_review ("Ready for Pre-Publication Mailer"
        #       is checked on last save in XML editor client.)
        #   .../CurrentStatus = "Active".
        #   .../Directory/Include = "Pending".
        #   No non-failing mailer has previously been generated of
        #       of type Physician-Initial.
        qry = """
            SELECT DISTINCT document.id, MAX(doc_version.num)
                       FROM doc_version
                       JOIN ready_for_review
                         ON ready_for_review.doc_id = doc_version.id
                       JOIN document document
                         ON document.id = ready_for_review.doc_id
                       JOIN doc_type
                         ON doc_type.id = document.doc_type
                       JOIN query_term qstat
                         ON qstat.doc_id = document.id
                       JOIN query_term qinc
                         ON qinc.doc_id = document.id
                      WHERE doc_type.name = 'Person'
                        AND qstat.path = '/Person/Status/CurrentStatus'
                        AND qstat.value = 'Active'
                        AND qinc.path =
                           '/Person/ProfessionalInformation/PhysicianDetails/AdministrativeInformation/Directory/Include'
                        AND qinc.value = 'Pending'
                        AND NOT EXISTS (
                                SELECT *
                                  FROM pub_proc p
                                  JOIN pub_proc_doc pd
                                    ON p.id = pd.pub_proc
                                 WHERE pd.doc_id = document.id
                                   AND p.pub_subset = 'Physician-Initial'
                                   AND p.status <> 'Fail'
                                )
                   GROUP BY document.id"""

    elif mailType == 'Physician-Annual update':
        # Preselect all mailers sent to physicians in the last year.
        # Include initial, annual, and all remailers.
        # Testing shows that creating a temporary table in this way
        #   speeds the subsequent query by a factor of about 8
        qry = """
            -- Temp table
            CREATE TABLE #mail_physician_annual_ids (tmpid int)

            -- Fill it with ids of all physician mailers < 1 year old
            INSERT INTO #mail_physician_annual_ids (tmpid)
                    SELECT pd2.doc_id
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
                       AND p2.status <> 'Fail'
        """
        try:
            cursor.execute(qry)
        except cdrdb.Error, info:
            cdrcgi.bail("Failure creating temp physician remailr table: %s" \
                        % info[1][0])

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
            SELECT DISTINCT document.id, MAX(doc_version.num)
                       FROM doc_version
                       JOIN document
                         ON doc_version.id = document.id
                       JOIN doc_type
                         ON doc_type.id = document.doc_type
                       JOIN pub_proc_doc pd1
                         ON document.id = pd1.doc_id
                       JOIN pub_proc p1
                         ON pd1.pub_proc = p1.id
                       JOIN query_term qstat
                         ON qstat.doc_id = document.id
                       JOIN query_term qinc
                         ON qinc.doc_id = document.id
                      WHERE doc_type.name = 'Person'
                        AND qstat.path = '/Person/Status/CurrentStatus'
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
                                  FROM #mail_physician_annual_ids
                                 WHERE document.id = tmpid
                             )
                   GROUP BY document.id"""

    elif mailType == 'Organization-Annual update':
        # Perform same optimization as for physicians
        # Preselect all mailers sent to orgs in last year
        qry = """
            -- Temp table
            CREATE TABLE #mail_org_annual_ids (tmpid int)

            -- Fill it with ids of all organization mailers < 1 year old
            INSERT INTO #mail_org_annual_ids (tmpid)
                    SELECT pd2.doc_id
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
                       AND p2.status <> 'Fail'
        """
        try:
            cursor.execute(qry)
        except cdrdb.Error, info:
            cdrcgi.bail("Failure creating temp org remailer table: %s" \
                        % info[1][0])


        # Select last version (not CWD) of document for which:
        #   Doc_type = Organization.
        #   .../IncludeInDirectory = "Include".
        #   .../OrganizationType <> "NCI division, office, or laboratory".
        #   .../OrganizationType <> "NIH institute, center or division".
        #   No non-failing update mailer sent in the past year.
        #   No non-failing remailer sent in the past year.
        qry = """
            SELECT DISTINCT document.id, MAX(doc_version.num)
                       FROM doc_version
                       JOIN document
                         ON doc_version.id = document.id
                       JOIN doc_type
                         ON doc_type.id = document.doc_type
                       JOIN query_term qinc
                         ON qinc.doc_id = document.id
                       JOIN query_term qorgtype
                         ON qorgtype.doc_id = document.id
                      WHERE doc_type.name = 'Organization'
                        AND qinc.path =
                           '/Organization/OrganizationDetails/OrganizationAdministrativeInformation/IncludeInDirectory'
                        AND qinc.value = 'Include'
                        AND qorgtype.path = 'Organization/OrganizationType'
                        AND qorgtype.value <>
                                    'NCI division, office, or laboratory'
                        AND qorgtype.value <>
                                    'NIH institute, center, or division'

                        -- But not if a mailer was sent in past year
                        AND NOT EXISTS (
                                SELECT tmpid
                                  FROM #mail_org_annual_ids
                                 WHERE document.id = tmpid
                             )
                   GROUP BY document.id"""

    elif timeType == 'Remail':
        # Execute a query that builds a temporary table
        try:
            rms = cdrmailcommon.RemailSelector (conn)
            rms.select (orgMailType)

            # And create one to fetch the doc ids from it
            qry = rms.getDocIdVerQuery()

        except cdrdb.Error, info:
            cdrcgi.bail('Database failure selecting remailers: %s'
                        % info[1][0])

    # Execute the query to find all matching documents
    try:
        cursor.execute(qry)
        docList = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving document IDs: %s" % info[1][0])

# Do we have any results?
if len(docList) == 0:
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

# Tell user how to get status
header = cdrcgi.header(title, title, section, None, [])
html = """\
    <H3>Job Number %d Submitted</H3>
    <B>
     <FONT COLOR='black'>Use
      <A HREF='%s/PubStatus.py?id=%d'>this link</A> to view job status.
     </FONT>
    </B>
   </FORM>
  </BODY>
 </HTML>
""" % (jobId, cdrcgi.BASE, jobId)

# Remailers require permanent storage of the associated ids
#  in the database, using job id as a key
if timeType == 'Remail':
    rms.fillMailerIdTable(jobId)

cdrcgi.sendPage(header + html)
