#----------------------------------------------------------------------
#
# $Id: ProtocolMailerReqForm.py,v 1.4 2002-11-13 20:34:52 bkline Exp $
#
# Request form for all protocol mailers.
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
# $Log: not supported by cvs2svn $
# Revision 1.3  2002/11/07 18:54:47  bkline
# Incorporated interface changes requested by Lakshmi.
#
# Revision 1.2  2002/10/24 02:46:22  bkline
# Ready for user testing.
#
# Revision 1.1  2002/10/22 14:41:51  bkline
# Consolidated menu for all protocol mailers.
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb, cdrpubcgi, cdrmailcommon, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields      = cgi.FieldStorage()
session     = cdrcgi.getSession(fields)
request     = cdrcgi.getRequest(fields)
docId       = fields and fields.getvalue("DocId")    or None
email       = fields and fields.getvalue("Email")    or None
userPick    = fields and fields.getvalue("userPick") or None
maxMails    = fields and fields.getvalue("maxMails") or 'No limit'
title       = "CDR Administration"
section     = "Protocol Mailer Request Form"
SUBMENU     = "Mailer Menu"
buttons     = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script      = 'ProtocolMailerReqForm.py'
header      = cdrcgi.header(title, title, section, script, buttons, 
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
statusPath  = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
brussels    = 'NCI Liaison Office-Brussels'
sourcePath  = '/InScopeProtocol/ProtocolSources/ProtocolSource/SourceName'
docType     = 'InScopeProtocol'
modePath    = '/Organization/OrganizationDetails/PreferredProtocolContactMode'
leadOrgPath = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'\
              '/LeadOrganizationID/@cdr:ref'
if maxMails == 'No limit': maxDocs = sys.maxint
else:
    try:
        maxDocs = int(maxMails)
    except:
        cdrcgi.bail("Invalid value for maxMails: %s" % maxMails)
if maxDocs < 1:
    cdrcgi.bail("Invalid value for maxMails: %s" % maxMails)

#----------------------------------------------------------------------
# Make sure we're logged in.
#----------------------------------------------------------------------
if not session: cdrcgi.bail('Unknown or expired CDR session.')

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if request == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif request == SUBMENU:
    cdrcgi.navigateTo("Mailers.py", session)

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
     If you want to, you can limit the number of protocol documents for
     which mailers will be generated in a given job, by entering a 
     maximum number.
    </li>
    <li>
     To generate mailers for a single Protocol, select type of mailer 
     and enter the document ID of the Protocol.
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
   <input type='radio' name='userPick' class='r' value='ProtAbstInit'>
    <span class='r'>Initial Abstract Mailer</span><br>
   <input type='radio' name='userPick' class='r' value='ProtAbstAnnual'>
    <span class='r'>Annual Abstract Mailer</span><br>
   <input type='radio' name='userPick' class='r' value='ProtAbstRemail'>
    <span class='r'>Annual Abstract Remail</span><br>
   <input type='radio' name='userPick' class='r' value='ProtInitStatPart'>
    <span class='r'>Initial Status/Participant Check</span><br>
   <input type='radio' name='userPick' class='r' value='ProtQuarterlyStatPart'>
    <span class='r'>Quarterly Status/Participant Check</span>
   <br><br><br>
   <b>
    Limit maximum number of documents for which mailers will be 
    generated:&nbsp;
   </b>
   <input type='text' name='maxMails' size='12' value='No limit' />
   <br><br><br>
   <h3>To generate mailer for a single Physician/Organization, enter</h3>
   <b>Protocol document CDR ID:&nbsp;</b>
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
    cdrcgi.bail ('Must select a protocol mailer type')

#----------------------------------------------------------------------
# Set variables based on user selections on CGI form:
#   timeType    = Why we're mailing - 'Initial', 'Update', or 'Remail'
#   mailType    = MailerType enumeration from the Mailer tracking doc schema
#   orgMailType = For a remailer, the original mailType we are remailing
#   orgType     = 'Coop' or 'Non-Coop' (status/participant checks only)
#----------------------------------------------------------------------
if userPick    == 'ProtAbstInit':
    timeType    = 'Initial'
    mailType    = 'Protocol-Initial abstract'
elif userPick  == 'ProtAbstAnnual':
    timeType    = 'Update'
    mailType    = 'Protocol-Annual abstract'
    orgMailType = 'Protocol-Initial abstract'
elif userPick  == 'ProtAbstRemail':
    timeType    = 'Remail'
    mailType    = 'Protocol-Annual abstract remail'
elif userPick  == 'ProtInitStatPart':
    timeType    = 'Initial'
    mailType    = 'Protocol-Initial status/participant check'
elif userPick  == 'ProtQuarterlyStatPart':
    timeType    = 'Update'
    mailType    = 'Protocol-Quarterly status/participant check'
    orgMailType = 'Protocol-Initial status/participant check'

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
        if not row:
            cdrcgi.bail("No version found for document %d" % intId)

        # Document list contains one tuple of doc id + version number
        docList = ((intId, row[0]),)
    except cdrdb.Error, info:
        cdrcgi.bail("Database failure finding version for document %d: %s" % 
                    (intId, info[1][0]))

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

#----------------------------------------------------------------------
# Select protocols ready for the initial abstract mailer.
#----------------------------------------------------------------------
elif mailType == 'Protocol-Initial abstract':
    try:
        cursor.execute("""\
        SELECT DISTINCT TOP %d protocol.id, MAX(doc_version.num)
                       FROM doc_version
                       JOIN ready_for_review
                         ON ready_for_review.doc_id = doc_version.id
                       JOIN document protocol
                         ON protocol.id = ready_for_review.doc_id
                       JOIN query_term prot_status
                         ON prot_status.doc_id = protocol.id
                      WHERE prot_status.value IN ('Active', 
                                                  'Approved-not yet active')
                        AND prot_status.path = '%s'

                        -- Don't send mailers to Brussels.
                        AND NOT EXISTS (SELECT *
                                          FROM query_term src
                                         WHERE src.value = '%s'
                                           AND src.path  = '%s'
                                           AND src.doc_id = protocol.id)

                        -- Don't send the initial mailer twice.
                        AND NOT EXISTS (SELECT *
                                          FROM pub_proc p
                                          JOIN pub_proc_doc pd
                                            ON p.id = pd.pub_proc
                                         WHERE pd.doc_id = protocol.id
                                           AND p.pub_subset = '%s'
                                           AND (p.status = 'Success'
                                           AND pd.failure IS NULL
                                            OR p.completed IS NULL))
                   GROUP BY protocol.id""" % (maxDocs, statusPath, brussels,
                                              sourcePath, mailType))
        docList = cursor.fetchall()
        if not docList:
            cdrcgi.bail("No documents match the selection criteria")
    except cdrdb.Error, info:
        cdrcgi.bail("Failure selecting protocols: %s" % info[1][0])

#----------------------------------------------------------------------
# Select protocols ready for an annual abstract update mailer.
#----------------------------------------------------------------------
elif mailType == 'Protocol-Annual abstract':
    try:

        # For which protocols have we already sent abstract mailers this year?
        cursor.execute("""\
            SELECT DISTINCT d.doc_id
                       INTO #already_mailed
                       FROM pub_proc_doc d
                       JOIN pub_proc p
                         ON p.id = d.pub_proc
                      WHERE p.status <> 'Failure'
                        AND p.started > DATEADD(year, -1, GETDATE())
                        AND p.pub_subset IN ('Protocol-Initial abstract',
                                             'Protocol-Annual abstract',
                                             'Protocol-Annual abstract remail')
                        AND p.pub_system = %d""" % ctrlDocId)
                                             
        cursor.execute("""\
            SELECT DISTINCT TOP %d protocol.id, MAX(doc_version.num)
                       FROM document protocol
                       JOIN doc_version
                         ON doc_version.id = protocol.id
                       JOIN query_term prot_status
                         ON prot_status.doc_id = protocol.id
                      WHERE prot_status.value IN ('Active', 
                                                  'Approved-Not Yet Active')
                        AND prot_status.path = '%s'

                        -- Make sure the initial mailer has gone out.
                        AND EXISTS (SELECT *
                                      FROM pub_event e
                                      JOIN published_doc d
                                        ON e.id = d.pub_proc
                                     WHERE d.doc_id = protocol.id
                                       AND e.pub_system = %d
                                       AND e.pub_subset = '%s')

                        -- Don't send mailers to Brussels.
                        AND NOT EXISTS (SELECT *
                                          FROM query_term
                                         WHERE value  = '%s'
                                           AND path   = '%s'
                                           AND doc_id = protocol.id)
                        AND NOT EXISTS (SELECT *
                                          FROM #already_mailed
                                         WHERE doc_id = protocol.id)
                   GROUP BY protocol.id""" % (maxDocs,
                                              statusPath,
                                              ctrlDocId,
                                              orgMailType,
                                              brussels,
                                              sourcePath))
        docList = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure selecting protocols: %s" % info[1][0])

#----------------------------------------------------------------------
# Send out a protocol abstract mailer reminder for the slackers.
# Note that the remailers are specified in section 2.6.2 of the
# requirements document.  This is a subsection of the requirements
# for the annual abstract update mailers, not for all protocol
# abstract mailers, so these don't get sent for the initial abstract
# mailers.
#----------------------------------------------------------------------
elif mailType == 'Protocol-Annual abstract remail':
    annualMailers = 'Protocol-Annual abstract'
    try:
        cursor.execute("""\
   SELECT DISTINCT TOP %d protocol.id, MAX(doc_version.num)
              FROM document protocol
              JOIN doc_version
                ON doc_version.id = protocol.id
              JOIN query_term mailer_prot_doc
                ON mailer_prot_doc.int_val = protocol.id
              JOIN query_term mailer_type
                ON mailer_type.doc_id = mailer_prot_doc.doc_id
              JOIN query_term mailer_sent
                ON mailer_sent.doc_id = mailer_type.doc_id
             WHERE mailer_prot_doc.path = '/Mailer/Document/@cdr:ref'
               AND mailer_type.path = '/Mailer/Type'
               AND mailer_type.value = '%s'
               AND mailer_sent.path = '/Mailer/Sent'
               AND mailer_sent.value BETWEEN DATEADD(day, -120, GETDATE())
                                         AND DATEADD(day,  -60, GETDATE())

               -- Don't bug the folks who have already answered.
               AND NOT EXISTS (SELECT *
                                 FROM query_term
                                WHERE path = '/Mailer/Response/Received'
                                  AND doc_id = mailer_sent.doc_id
                                  AND value IS NOT NULL
                                  AND value <> '')

               -- Don't dun them more than once.
               AND NOT EXISTS (SELECT *
                                 FROM query_term
                                WHERE path = '/Mailer/RemailerFor/@cdr:ref'
                                  AND int_val = mailer_sent.doc_id)
          GROUP BY protocol.id""" % (maxDocs, annualMailers))
    
        docList = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure selecting protocols: %s" % info[1][0])

#----------------------------------------------------------------------
# Find the protocols which need an initial status and participant check.
#----------------------------------------------------------------------
elif mailType == 'Protocol-Initial status/participant check':
    try:
        cursor.execute("""\
            SELECT DISTINCT TOP %d protocol.id, MAX(doc_version.num)
                       FROM document protocol
                       JOIN doc_version
                         ON doc_version.id = protocol.id
                       JOIN ready_for_review
                         ON ready_for_review.doc_id = protocol.id
                       JOIN query_term prot_status
                         ON prot_status.doc_id = protocol.id
                       JOIN query_term lead_org
                         ON lead_org.doc_id = protocol.id
                      WHERE prot_status.value IN ('Active', 
                                                  'Approved-Not Yet Active')
                        AND prot_status.path   = '%s'
                        AND lead_org.path      = '%s'

                        -- Don't send paper when they want electronic mailers.
                        AND NOT EXISTS (SELECT *
                                          FROM query_term contact_mode
                                         WHERE contact_mode.doc_id =
                                               lead_org.int_val
                                           AND contact_mode.path = '%s')

                        -- Don't send mailers for Brussels protocols.
                        AND NOT EXISTS (SELECT *
                                          FROM query_term src
                                         WHERE src.value = '%s'
                                           AND src.path  = '%s'
                                           AND src.doc_id = protocol.id)

                        -- Don't send the initial mailer twice.
                        AND NOT EXISTS (SELECT *
                                          FROM pub_proc p
                                          JOIN pub_proc_doc pd
                                            ON p.id = pd.pub_proc
                                         WHERE pd.doc_id = protocol.id
                                           AND p.pub_subset = '%s'
                                           AND (p.status = 'Success'
                                            OR p.completed IS NULL))
                   GROUP BY protocol.id""" % (maxDocs,
                                              statusPath, 
                                              leadOrgPath,
                                              modePath,
                                              brussels, 
                                              sourcePath,
                                              mailType))
        docList = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving document IDs: %s" % info[1][0])

#----------------------------------------------------------------------
# Find the protocols which need an initial status and participant check.
#----------------------------------------------------------------------
elif mailType == 'Protocol-Quarterly status/participant check':
    try:
        # From the mailer requirements, section 2.81:  "Regular 
        # Status/Participant Update mailers will be generated for 
        # protocols with Status = Active, and [i.e. or] Approved,
        # Temporarily Closed [i.e. Approved-not yet active], and
        # with Source not = NCI Liaison Office, and has flag of
        # Generate Hardcopy Mailer in Org record [no such flag;
        # using PreferredContactMode of 'Hardcopy' instead]."
        # Also, we need to make sure that a successful initial
        # participant and status check mailer has been sent, and
        # that the last participant and status check mailer went
        # out at least three months earlier for the protocols
        # selected.
        # [RMK 2002-10-22: Another change in the preferred contact
        # mode mechanism.  According to the users, we can now regard
        # any organization with the PreferredContactMode element
        # present as requesting electronic mailers.]
        cursor.execute("""\
            SELECT DISTINCT d.doc_id
                       INTO #recent_mailers
                       FROM pub_proc_doc d
                       JOIN pub_proc p
                         ON p.id = d.pub_proc
                      WHERE p.pub_subset IN ('%s', '%s')
                        AND p.completed IS NULL
                         OR (p.status = 'Success'
                        AND DATEADD(quarter, -1, GETDATE()) < p.completed)
                        AND p.pub_system = %d""" % (mailType,
                                                    orgMailType,
                                                    ctrlDocId))
        cursor.execute("""\
            SELECT DISTINCT TOP %d protocol.id, MAX(doc_version.num)
                       FROM document protocol
                       JOIN doc_version
                         ON doc_version.id = protocol.id
                       JOIN query_term prot_status
                         ON prot_status.doc_id = protocol.id
                       JOIN query_term lead_org
                         ON lead_org.doc_id = protocol.id

                      -- Only send mailers for active or approved protocols
                      WHERE prot_status.value IN ('Active', 
                                                  'Approved-Not Yet Active')
                        AND prot_status.path   = '%s'
                        AND lead_org.path      = '%s'

                        -- Make sure they've gotten their original mailer.
                        AND EXISTS (SELECT *
                                      FROM pub_proc orig_mailer
                                      JOIN pub_proc_doc om_doc
                                        ON orig_mailer.id = om_doc.pub_proc
                                     WHERE orig_mailer.pub_subset = '%s'
                                       AND orig_mailer.status = 'Success'
                                       AND om_doc.doc_id = protocol.id)

                        -- Don't send paper to those who want electronic.
                        AND NOT EXISTS (SELECT *
                                          FROM query_term
                                         WHERE doc_id = lead_org.int_val
                                           AND path = '%s')

                        -- Don't bug them too often.
                        AND NOT EXISTS (SELECT *
                                          FROM #recent_mailers
                                         WHERE doc_id = protocol.id)

                        -- Don't send mailers to Brussels.
                        AND NOT EXISTS (SELECT *
                                          FROM query_term
                                         WHERE value  = '%s'
                                           AND path   = '%s'
                                           AND doc_id = protocol.id)
                   GROUP BY protocol.id""" % (maxDocs,
                                              statusPath,
                                              leadOrgPath,
                                              orgMailType,
                                              modePath,
                                              brussels,
                                              sourcePath))
        docList = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving document IDs: %s" % info[1][0])

# Check to make sure we have at least one mailer to send out.
docCount = len(docList)
if docCount == 0:
    cdrcgi.bail ("No documents found")

# Compose the docList results into a format that cdr.publish() wants
#   e.g., id=25, version=3, then form: "CDR0000000025/3"
# This works on a docList produced by a query, or produced by user entry
#   of a single document id
docs = []
for doc in docList:
    docs.append("CDR%010d/%d" % (doc[0], doc[1]))

# Drop the job into the queue.
result = cdr.publish(credentials = session, pubSystem = 'Mailers',
                      pubSubset = mailType, docList = docs,
                      allowNonPub = 'Y', email = email)

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
    msgs.append ("                        First doc = %s" % docs[0])
if docCount > 1:
    msgs.append ("                       Second doc = %s" % docs[1])
cdr.logwrite (msgs, cdrmailcommon.LOGFILE)

# Tell user how to get status
header = cdrcgi.header(title, title, section, None, [])
cdrcgi.sendPage(header + """\
    <H3>Job Number %d Submitted</H3>
    <B>
     <FONT COLOR='black'>Use
      <A HREF='%s/PubStatus.py?id=%d'>this link</A> to view job status.
     </FONT>
    </B>
   </FORM>
  </BODY>
 </HTML>
""" % (jobId, cdrcgi.BASE, jobId))
