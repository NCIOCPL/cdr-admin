#----------------------------------------------------------------------
#
# $Id: ProtocolMailerReqForm.py,v 1.15 2004-05-18 12:42:53 bkline Exp $
#
# Request form for all protocol mailers.
#
# This program is invoked twice to create a mailer job.
#
# The first invocation is made by a high level mailer menu from which
# a user selected protocol mailers.  In the first invocation, the program
# detects that no specific mailer has been requested ("if not request")
# and returns an input form to the web browser to gather information
# needed to start a specific mailer job.
#
# When a user responds to the form, we get the input here in a second
# invocation.  We then validate the input and setup the requested mailer
# publication job for the publishing daemon to find and initiate.
#
# $Log: not supported by cvs2svn $
# Revision 1.14  2003/05/08 20:23:04  bkline
# Added code to skip blocked documents.
#
# Revision 1.13  2003/02/19 22:05:37  bkline
# Turned off query testing code for S&P mailers.
#
# Revision 1.12  2003/02/13 21:43:41  bkline
# Fixed comment to match previous change.
#
# Revision 1.11  2003/02/13 21:11:27  bkline
# Added 'Temporarily closed' for regular S&P mailers.
#
# Revision 1.10  2003/02/07 19:40:07  bkline
# Corrected a typo ("directory" changed to "protocol").  Added check for
# all S&P mailers to ensure that the protocol document is not blocked
# for publication (active_status = 'A').  Expended check for initial
# mailer to look for any kind of prior S&P mailer, not just another
# "initial" mailer (because we had to send our first round of quarterly
# S&P mailers without the benefit of any history from the legacy system).
# Suppressed check for previous mailer when sending quarterly S&P mailer
# (Sheri asked that we go ahead and send a quarterly anyway, even if
# they never got any S&P mailers before).
#
# Revision 1.9  2003/01/22 01:43:17  ameyer
# Added check for last valid version to single doc id.
# Added check for returned row with nothing in it at same place.
#
# Revision 1.8  2003/01/08 23:46:15  bkline
# Fixed cosmetic typo in SQL query.
#
# Revision 1.7  2002/12/06 16:01:59  bkline
# Fixed typo in WHERE clause (doc_version.publishable = 'P' should have
# been doc_version.publishable = 'Y').
#
# Revision 1.6  2002/11/18 14:39:09  bkline
# Fixed typo (change Person/Organization to Protocol).
#
# Revision 1.5  2002/11/14 14:27:15  bkline
# Adjusted selection criteria for issue #499.
#
# Revision 1.4  2002/11/13 20:34:52  bkline
# Fixed wording on limit documentation.
#
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
docId       = fields and fields.getvalue("DocId")      or None
email       = fields and fields.getvalue("Email")      or None
userPick    = fields and fields.getvalue("userPick")   or None
paper       = fields and fields.getvalue("paper")      or 0
electronic  = fields and fields.getvalue("electronic") or 0
maxMails    = fields and fields.getvalue("maxMails")   or 'No limit'
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
  <script language='JavaScript'>
   <!--
    function emOff() {
        document.forms[0].electronic.checked = false;
        document.forms[0].paper.checked = true;
    }
    function emOn() {
        document.forms[0].electronic.checked = true;
        document.forms[0].paper.checked = true;
    }
   // -->
  </script>
 """)
parms       = None
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
   <input type='radio' name='userPick' class='r' value='ProtAbstInit'
          onClick='emOff()'>
    <span class='r'>Initial Abstract Mailer</span><br>
   <input type='radio' name='userPick' class='r' value='ProtAbstAnnual'
          onClick='emOff()'>
    <span class='r'>Annual Abstract Mailer</span><br>
   <input type='radio' name='userPick' class='r' value='ProtAbstRemail'
          onClick='emOff()'>
    <span class='r'>Annual Abstract Remail</span><br>
   <input type='radio' name='userPick' class='r' value='ProtInitStatPart'
          onClick='emOn()'>
    <span class='r'>Initial Status/Participant Check</span><br>
   <input type='radio' name='userPick' class='r' value='ProtQuarterlyStatPart'
          onClick='emOn()'>
    <span class='r'>Quarterly Status/Participant Check</span>
   <br><br><br>
   <input id='paper' type="checkbox" name="paper" />&nbsp;
   <span class='r'>Paper Mailers</span><br>
   <input id='electronic' type="checkbox" name="electronic" />&nbsp;
   <span class='r'>Electronic Mailers</span>
   <br><br><br>
   <b>
    Limit maximum number of documents for which mailers will be
    generated:&nbsp;
   </b>
   <input type='text' name='maxMails' size='12' value='No limit' />
   <br><br><br>
   <h3>To generate mailer for a single Protocol, enter</h3>
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
if not electronic and not paper:
    cdrcgi.bail("Neither paper nor electronic mailers selected")
if electronic and userPick not in ('ProtInitStatPart',
                                   'ProtQuarterlyStatPart'):
    cdrcgi.bail("Only paper mailers supported for protocol abstracts")
                    
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
# Just for testing.
#----------------------------------------------------------------------
def showDocsAndRun(rows):
    if not rows:
        rows = []
    html = """\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Protocol S&amp;P Doc List</title>
  <style type='text/css'>
   th,h2    { font-family: Arial, sans-serif; font-size: 11pt;
              text-align: center; font-weight: bold; }
   h1       { font-family: Arial, sans-serif; font-size: 12pt;
              text-align: center; font-weight: bold; }
   td       { font-family: Arial, sans-serif; font-size: 10pt; }
  </style>
 </head>
 <body>
  <h1>Protocol S&amp;P Doc List</h1>
  <h2>%d docs selected</h2>
  <br><br>
  <table border='1' cellspacing='0' cellpadding='1'>
   <tr>
    <th>Document</th>
    <th>Version</th>
   </tr>
""" % len(rows)
    for row in rows:
        html += """\
   <tr>
    <td align='center'>CDR%010d</td>
    <td align='center'>%d</td>
   </tr>
""" % (row[0], row[1])
    cdrcgi.sendPage(html + """\
  </table>
 </body>
</html>""")
    
#----------------------------------------------------------------------
# Determine which documents are to be published.
#----------------------------------------------------------------------
if docId:
    # Simple case - user submitted single document id, isolate the digits
    digits = re.sub('[^\d]+', '', docId)
    intId  = int(digits)

    # Make sure the corresponding document exists in version control,
    #   getting the last version number of the last valid version.
    try:
        cursor.execute("""\
            SELECT MAX(num)
              FROM doc_version
             WHERE id = ?
               AND val_status = 'V'""", (intId,))
        row = cursor.fetchone()
        if not row or not row[0]:
            cdrcgi.bail("No valid version found for document %d" % intId)

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
                        AND prot_status.path       = '%s'
                        AND doc_version.val_status = 'V'
                        AND protocol.active_status = 'A'

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
                        AND doc_version.val_status = 'V'
                        AND doc_version.publishable = 'Y'
                        AND protocol.active_status = 'A'

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
               AND doc_version.publishable = 'Y'
               AND doc_version.val_status  = 'V'
               AND protocol.active_status = 'A'

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
else:
    if mailType not in ('Protocol-Initial status/participant check',
                        'Protocol-Quarterly status/participant check'):
        cdrcgi.bail("Unrecognized mailer type (%s)" % str(mailType))
    try:

        # Create a list of active protocols.
        cursor.execute("CREATE TABLE #mailer_prots (id INT, ver INT)")
        if mailType == "Protocol-Initial status/participant check":
            cursor.execute("""\
    INSERT INTO #mailer_prots (id, ver)
SELECT DISTINCT protocol.id, MAX(doc_version.num)
           FROM document protocol
           JOIN doc_version
             ON doc_version.id = protocol.id
           JOIN query_term prot_status
             ON prot_status.doc_id = protocol.id
           JOIN ready_for_review
             ON ready_for_review.doc_id = protocol.id
          WHERE prot_status.value IN ('Active',
                                      'Approved-Not Yet Active',
                                      'Temporarily closed')
            AND prot_status.path = '/InScopeProtocol/ProtocolAdminInfo'
                                 + '/CurrentProtocolStatus'
            AND doc_version.val_status = 'V'
            AND protocol.active_status = 'A'

            -- Don't send the initial mailer twice.
            AND NOT EXISTS (SELECT pd.doc_id
                              FROM pub_proc p
                              JOIN pub_proc_doc pd
                                ON p.id = pd.pub_proc
                             WHERE pd.doc_id = protocol.id
                               AND p.pub_subset IN ('Protocol-Quarterly status'
                                                  + '/participant check', 
                                                    'Protocol-Initial status'
                                                  + '/participant check')
                               AND (p.status = 'Success'
                                OR  p.completed IS NULL)
                               AND (pd.failure IS NULL
                                OR  pd.failure = 'N'))
       GROUP BY protocol.id""", timeout = 300)
        else:
            cursor.execute("""\
    INSERT INTO #mailer_prots (id, ver)
SELECT DISTINCT protocol.id, MAX(doc_version.num)
           FROM document protocol
           JOIN doc_version
             ON doc_version.id = protocol.id
           JOIN query_term prot_status
             ON prot_status.doc_id = protocol.id
          WHERE prot_status.value IN ('Active',
                                      'Approved-Not Yet Active',
                                      'Temporarily closed')
            AND prot_status.path = '/InScopeProtocol/ProtocolAdminInfo'
                                 + '/CurrentProtocolStatus'
            AND doc_version.publishable = 'Y'
            AND protocol.active_status  = 'A'
       GROUP BY protocol.id""", timeout = 300)

        # Find the lead organizations (and pups) for these protocols
        cursor.execute("""\
   CREATE TABLE #lead_orgs
       (prot_id INTEGER,
       prot_ver INTEGER,
         org_id INTEGER,
         pup_id INTEGER,
       pup_link VARCHAR(80),
    update_mode VARCHAR(80))""")
        cursor.execute("""\
    INSERT INTO #lead_orgs (prot_id, prot_ver, org_id, pup_id, pup_link,
                            update_mode)
         SELECT m.id, m.ver, o.int_val, p.int_val, p.value, u.value
           FROM #mailer_prots m
           JOIN query_term o
             ON o.doc_id = m.id
           JOIN query_term s
             ON s.doc_id = o.doc_id
            AND LEFT(s.node_loc, 8)  = LEFT(o.node_loc, 8)
           JOIN query_term p
             ON p.doc_id = o.doc_id
            AND LEFT(p.node_loc, 8)  = LEFT(o.node_loc, 8)
           JOIN query_term r
             ON r.doc_id = p.doc_id
            AND LEFT(r.node_loc, 12) = LEFT(p.node_loc, 12)
LEFT OUTER JOIN query_term u
             ON u.doc_id = o.doc_id
            AND LEFT(u.node_loc, 8)  = LEFT(o.node_loc, 8)
            AND u.path  = '/InScopeProtocol/ProtocolAdminInfo'
                        + '/ProtocolLeadOrg/UpdateMode'
LEFT OUTER JOIN query_term t
             ON t.doc_id = u.doc_id
            AND LEFT(t.node_loc, 12) = LEFT(u.node_loc, 12)
            AND t.path  = '/InScopeProtocol/ProtocolAdminInfo'
                        + '/ProtocolLeadOrg/UpdateMode/@MailerType'
            AND t.value = 'Protocol_SandP'
          WHERE o.path  = '/InScopeProtocol/ProtocolAdminInfo'
                        + '/ProtocolLeadOrg/LeadOrganizationID/@cdr:ref'
            AND s.path  = '/InScopeProtocol/ProtocolAdminInfo'
                        + '/ProtocolLeadOrg/LeadOrgProtocolStatuses'
                        + '/CurrentOrgStatus/StatusName'
            AND s.value IN ('Active', 'Approved-not yet active',
                            'Temporarily closed')
            AND p.path  = '/InScopeProtocol/ProtocolAdminInfo'
                        + '/ProtocolLeadOrg/LeadOrgPersonnel'
                        + '/Person/@cdr:ref'
            AND r.path  = '/InScopeProtocol/ProtocolAdminInfo'
                        + '/ProtocolLeadOrg/LeadOrgPersonnel'
                        + '/PersonRole'
            AND r.value = 'Update person'""", timeout = 300)


        # Fill in missing update modes.
        cursor.execute("""\
    CREATE TABLE #pup_update_mode
         (pup_id INTEGER,
     update_mode VARCHAR(80))""")
        cursor.execute("""\
    INSERT INTO #pup_update_mode (pup_id, update_mode)
SELECT DISTINCT u.doc_id, MAX(u.value) -- Avoid multiple values
           FROM #lead_orgs o
           JOIN query_term u
             ON u.doc_id = o.pup_id
           JOIN query_term t
             ON t.doc_id = u.doc_id
            AND LEFT(t.node_loc, 8) = LEFT(u.node_loc, 8)
          WHERE o.update_mode IS NULL
            AND u.path  = '/Person/PersonLocations/UpdateMode'
            AND t.path  = '/Person/PersonLocations/UpdateMode/@MailerType'
            AND t.value = 'Protocol_SandP'
       GROUP BY u.doc_id""", timeout = 300)
        cursor.execute("""\
         UPDATE #lead_orgs
            SET update_mode = p.update_mode
           FROM #lead_orgs o
           JOIN #pup_update_mode p
             ON p.pup_id = o.pup_id
          WHERE o.update_mode IS NULL
            AND p.update_mode IS NOT NULL""")

        # Select based on update mode.
        if paper:
            if electronic:
                updateMode = "IN ('Web-based', 'Mail')"
                parms = [['UpdateModes', '[Mail][Web-based]']]
            else:
                updateMode = "= 'Mail'"
                parms = [['UpdateModes', '[Mail]']]
        else:
            updateMode = "= 'Web-based'"
            parms = [['UpdateModes', '[Web-based]']]
        cursor.execute("""\
SELECT DISTINCT TOP %d prot_id, prot_ver
           FROM #lead_orgs
          WHERE update_mode %s
       ORDER BY prot_id""" % (maxDocs, updateMode))
        docList = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure retrieving document IDs: %s" % info[1][0])
    #showDocsAndRun(docList)


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
                      allowNonPub = 'Y', email = email, parms = parms)

# cdr.publish returns a tuple of job id + messages
# If serious error, job id = None
if not result[0] or int(result[0]) < 0:
    cdrcgi.bail("Unable to initiate publishing job:<br>%s" % result[1])

jobId = int(result[0])

# Log what happened
msgs = [" Started protocol mailer job - id = %d" % jobId,
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
