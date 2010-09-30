#----------------------------------------------------------------------
#
# $Id$
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
# BZIssue::499
# BZIssue::1350
# BZIssue::1570
# BZIssue::1664
# BZIssue::3326
# BZIssue::4913
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb, cdrpubcgi, cdrmailcommon, sys
import textwrap, time

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields      = cgi.FieldStorage()
session     = cdrcgi.getSession(fields)
request     = cdrcgi.getRequest(fields)
docId       = fields and fields.getvalue("DocId")      or None
email       = fields and fields.getvalue("Email")      or None
userPick    = fields and fields.getvalue("userPick")   or None
leadOrg     = fields and fields.getvalue("leadOrg")    or None
pup         = fields and fields.getvalue("pup")        or None
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
   .thLabel { font-size: 11pt; font-weight: bold; 
              color: black; font-family: Arial;
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
    function emOnly() {
        document.forms[0].electronic.checked = true;
        document.forms[0].paper.checked = false;
    }
   // -->
  </script>
 """)
statusPath  = '/InScopeProtocol/ProtocolAdminInfo/CurrentProtocolStatus'
brussels    = 'NCI Liaison Office-Brussels'
sourcePath  = '/InScopeProtocol/ProtocolSources/ProtocolSource/SourceName'
docType     = 'InScopeProtocol'
modePath    = '/Organization/OrganizationDetails/PreferredProtocolContactMode'
leadOrgPath = '/InScopeProtocol/ProtocolAdminInfo/ProtocolLeadOrg'\
              '/LeadOrganizationID/@cdr:ref'
statPartTypes =  ('ProtInitStatPart', 'ProtQuarterlyStatPart')
if maxMails == 'No limit': maxDocs = sys.maxint
else:
    try:
        maxDocs = int(maxMails)
    except:
        cdrcgi.bail("Invalid value for maxMails: %s" % maxMails)
if maxDocs < 1:
    cdrcgi.bail("Invalid value for maxMails: %s" % maxMails)
pupId = None
leadOrgId = None
parms = None
if userPick in statPartTypes:
    if paper:
        if electronic:
            parms = [['UpdateModes', '[Mail][Web-based]']]
        else:
            parms = [['UpdateModes', '[Mail]']]
    else:
        parms = [['UpdateModes', '[Web-based]']]

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
    <span class='r'>Quarterly Status/Participant Check</span><br>
   <input type='radio' name='userPick' class='r' value='PubNotif'
          onClick='emOnly()'>
    <span class='r'>Publication Notification Email</span>
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
   <table cellspacing='0' cellpadding='1'>
    <tr>
     <td width='10'>&nbsp;</td>
     <th class='thLabel' align='right'>Protocol document CDR ID:&nbsp;</th>
     <td><input name='DocId' /></td>
    </tr>
    <tr>
     <td width='10'>&nbsp;</td>
     <th class='thLabel' align='right'>Lead Org ID:&nbsp;</th>
     <td><input name='leadOrg' /> (Status and Participant mailers only)</td>
    </tr>
   </table>
   <br><br>
   <h3>OR (Status and Participant mailers only)</h3>
   <b>PUP ID:&nbsp;</b>
   <input name='pup' />
   <br><br><br>
   <h3>
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
if userPick == 'PubNotif' and paper:
    cdrcgi.bail("Publication notification only available as email")
if electronic and userPick not in statPartTypes and userPick != 'PubNotif':
    cdrcgi.bail("Only paper mailers supported for protocol abstracts")
if leadOrg:
    if not docId:
        cdrcgi.bail("Lead organization specified without protocol ID")
    elif userPick not in statPartTypes:
        cdrcgi.bail("Lead org can only be specified for Status and "
                    "Participant mailers.")
if pup and userPick not in statPartTypes:
    cdrcgi.bail("Protocol Update Person can only be specified for "
                "Status and Participant mailers.")
if pup and docId:
    cdrcgi.bail("Protocol Update Person and Protocol ID cannot both "
                "be specified.")
                    
#----------------------------------------------------------------------
# Connect to the CDR database.
#----------------------------------------------------------------------
try:
    conn = cdrdb.connect('CdrPublishing')
    conn.setAutoCommit (1)
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Send out a publication notification email message.
#----------------------------------------------------------------------
class PubNotificationProtocol:

    # Class-level values.
    wrapper = textwrap.TextWrapper()
    sender  = 'PDQUpdate@cancer.gov'
    subject = (u"NCI's PDQ Cancer Clinical Trials Registry Registration "
               u"Notification")

    class Recip:

        # Class hash for caching email addresses by fragment link value.
        addresses = {}

        # Constructor for nested Recip class.
        def __init__(self, fragLink, cursor):

            # Shorthand for this class object.
            PNPRecip = PubNotificationProtocol.Recip

            # Initialize members.
            self.docId, self.fragId = cdr.exNormalize(fragLink)[1:]
            self.trackingDocId = None
            self.email = PNPRecip.addresses.get(fragLink)
            if fragLink not in PNPRecip.addresses:
                cursor.execute("""\
                    SELECT e.value
                      FROM query_term e
                      JOIN query_term i
                        ON e.doc_id = i.doc_id
                       AND LEFT(e.node_loc, 8) = LEFT(i.node_loc, 8)
                     WHERE e.path LIKE '/Person/PersonLocations/%Email'
                       AND i.path LIKE '/Person/PersonLocations/%/@cdr:id'
                       AND i.value = ?
                       AND e.doc_id = ?""", (self.fragId, self.docId))
                rows = cursor.fetchall()
                if rows:
                    PNPRecip.addresses[fragLink] = rows[0][0]
                else:
                    cursor.execute("""\
                        SELECT o.value
                          FROM query_term o
                          JOIN query_term i
                            ON o.doc_id = i.doc_id
                           AND LEFT(o.node_loc, 8) = LEFT(i.node_loc, 8)
                         WHERE o.path = '/Person/PersonLocations'
                                      + '/OtherPracticeLocation'
                                      + '/OrganizationLocation/@cdr:ref'
                           AND i.path = '/Person/PersonLocations'
                                      + '/OtherPracticeLocation/@cdr:id'
                           AND i.value = ?
                           AND o.doc_id = ?""", (self.fragId, self.docId))
                    rows = cursor.fetchall()
                    if rows:
                        docId, fragId = cdr.exNormalize(rows[0][0])[1:]
                        cursor.execute("""\
                            SELECT e.value
                              FROM query_term e
                              JOIN query_term i
                                ON e.doc_id = i.doc_id
                               AND LEFT(e.node_loc, 8) = LEFT(i.node_loc, 8)
                             WHERE e.path LIKE '/Organization' +
                                               '/OrganizationLocations' +
                                               '/OrganizationLocation' +
                                               '/Location/%Email%'
                               AND i.path = '/Organization'
                                          + '/OrganizationLocations'
                                          + '/OrganizationLocation'
                                          + '/Location/@cdr:id'
                               AND i.value = ?
                               AND e.doc_id = ?""", (fragId, docId))
                        rows = cursor.fetchall()
                        if rows:
                            PNPRecip.addresses[fragLink] = rows[0][0]
            self.email = PNPRecip.addresses.get(fragLink)

    def __init__(self, docId, nctId, cursor):
        self.docId      = docId
        self.nctId      = nctId 
        self.primaryId  = u'[NO PRIMARY ID]'
        self.title      = u'[NO ORIGINAL TITLE]'
        self.originalId = u'[NO ORIGINAL ID]'
        self.recips     = {}
        cursor.execute("""\
            SELECT value
              FROM query_term
             WHERE path = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
               AND doc_id = ?""", docId)
        rows = cursor.fetchall()
        if rows:
            self.primaryId = rows[0][0]
        cursor.execute("""\
            SELECT i.value
              FROM query_term i
              JOIN query_term t
                ON i.doc_id = t.doc_id
               AND LEFT(i.node_loc, 8) = LEFT(t.node_loc, 8)
             WHERE i.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
               AND t.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
               AND t.value = 'Institutional/Original'
               AND i.doc_id = ?""", docId)
        rows = cursor.fetchall()
        if rows:
            self.originalId = rows[0][0]
        cursor.execute("""\
            SELECT o.value
              FROM query_term o
              JOIN query_term t
                ON o.doc_id = t.doc_id
               AND LEFT(o.node_loc, 4) = LEFT(t.node_loc, 4)
             WHERE o.path = '/InScopeProtocol/ProtocolTitle'
               AND t.path = '/InScopeProtocol/ProtocolTitle/@Type'
               AND t.value = 'Original'
               AND o.doc_id = ?""", docId)
        rows = cursor.fetchall()
        if rows:
            self.title = rows[0][0]
        cursor.execute("""\
            SELECT p.value
              FROM query_term p
              JOIN query_term r
                ON p.doc_id = r.doc_id
               AND LEFT(p.node_loc, 12) = LEFT(r.node_loc, 12)
             WHERE p.path = '/InScopeProtocol/ProtocolAdminInfo'
                          + '/ProtocolLeadOrg/LeadOrgPersonnel/Person'
                          + '/@cdr:ref'
               AND r.path = '/InScopeProtocol/ProtocolAdminInfo'
                          + '/ProtocolLeadOrg/LeadOrgPersonnel/PersonRole'
               AND r.value = 'Update person'
               AND p.doc_id = ?""", docId)
        rows = cursor.fetchall()
        if rows:
            recip = PubNotificationProtocol.Recip(rows[0][0], cursor)
            if recip.email:
                self.recips[recip.email.lower()] = recip
        cursor.execute("""\
            SELECT p.value
              FROM query_term p
              JOIN query_term i
                ON p.doc_id = i.doc_id
               AND LEFT(p.node_loc, 12) = LEFT(i.node_loc, 12)
              JOIN query_term a
                ON a.doc_id = p.doc_id
             WHERE p.path = '/InScopeProtocol/ProtocolAdminInfo'
                          + '/ProtocolLeadOrg/LeadOrgPersonnel/Person'
                          + '/@cdr:ref'
               AND i.path = '/InScopeProtocol/ProtocolAdminInfo'
                          + '/ProtocolLeadOrg/LeadOrgPersonnel/@cdr:id'
               AND a.path = '/InScopeProtocol/ProtocolAdminInfo'
                          + '/ProtocolLeadOrg/MailAbstractTo'
               AND a.value = i.value
               AND p.doc_id = ?""", docId)
        rows = cursor.fetchall()
        if rows:
            recip = PubNotificationProtocol.Recip(rows[0][0], cursor)
            if recip.email:
                self.recips[recip.email.lower()] = recip

def sendPubNotificationEmail(docId, nctId, cursor, conn):
    p = PubNotificationProtocol(docId, nctId, cursor)
    if not p.recips:
        raise Exception("no recipient email addresses found")
    addresses = [r.email for r in p.recips.values()]
    url = u"http://www.cancer.gov/clinicaltrials/%s" % p.primaryId
    line = (u'Thank you for registering your trial "%s", "%s" with '
            u'NCI\'s PDQ\u00ae Cancer Clinical Trials Registry.  '
            u'Your trial has been assigned a PDQ ID of "%s" and can '
            u'be viewed on the NCI Web site by clicking on the link below:'
            % (p.originalId, p.title, p.primaryId))
    top = u""
    if not cdr.isProdHost():
        top = u"""\
[SENT TO YOU FOR TESTING, INSTEAD OF TO %s]

""" % ", ".join(addresses)
        addresses = ['***REMOVED***', '***REMOVED***']
    body = u"""\
%s%s

%s

Your trial has also been registered in the National Library of
Medicine's ClinicalTrials.gov Web site as "%s."

We will be contacting you periodically to verify the information and
look forward to your cooperation.

Protocol Coordinator
NCI's PDQ\u00ae Cancer Clinical Trials Registry
Office of Communications and Education
National Cancer Institute
Email: pdqupdate@cancer.gov
""" % (top, PubNotificationProtocol.wrapper.fill(line), url, p.nctId)
    try:
        cdr.sendMail(PubNotificationProtocol.sender, addresses,
                     PubNotificationProtocol.subject, body, mime = True)
    except Exception, e:
        raise Exception("failure sending email notice to %s: %s" %
                        (", ".join(addresses), e))
    mailerMode, mailerType = 'Email', 'Publication notification email'
    sent = time.strftime('%Y-%m-%dT%M:%H:%S')
    for recip in p.recips.values():
        address = u"""\
   <MailerAddress>
    <Email>%s</Email>
   </MailerAddress>
""" % recip.email
        try:
            tId = cdrmailcommon.recordMailer(session, docId, recip.docId,
                                             mailerMode, mailerType, sent,
                                             address)
            recip.trackingDocId = tId
        except Exception, e:
            raise Exception("Failure recording mailer to %s for CDR%d: %s" %
                            (recip.email, docId, e))
    return p

#----------------------------------------------------------------------
# Send out publication notification emails if so requested.
#----------------------------------------------------------------------
if userPick == 'PubNotif':

    cursor = conn.cursor()

    # Gather the NCT IDs.
    cursor.execute("""\
        SELECT i.doc_id, i.value
          FROM query_term i
          JOIN query_term t
            ON i.doc_id = t.doc_id
           AND LEFT(i.node_loc, 8) = LEFT(t.node_loc, 8)
         WHERE i.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
           AND t.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
           AND t.value = 'ClinicalTrials.gov ID'""", timeout = 300)
    rows = cursor.fetchall()
    nctIds = {}
    for cdrId, nctId in rows:
        nctIds[cdrId] = nctId

    if docId:
        docIds = [cdr.exNormalize(docId)[1]]
    else:
        cursor.execute("""\
            SELECT d.doc_id, MIN(p.completed)
              FROM pub_proc_doc d
              JOIN pub_proc p
                ON p.id = d.pub_proc
              JOIN document doc
                ON d.doc_id = doc.id
              JOIN doc_type t
                ON doc.doc_type = t.id
             WHERE t.name = 'InScopeProtocol'
               AND doc.active_status = 'A'
               AND p.pub_subset LIKE 'Push_Documents_To_Cancer.Gov%'
               AND p.status = 'SUCCESS'
               AND (d.failure IS NULL OR d.failure <> 'Y')
               AND d.removed = 'N'
               AND d.doc_id NOT IN (SELECT md.int_val
                                      FROM query_term md
                                      JOIN query_term mt
                                        ON md.doc_id = mt.doc_id
                                     WHERE md.path = '/Mailer/Document'
                                                   + '/@cdr:ref'
                                       AND mt.path = '/Mailer/Type'
                                       AND mt.value = 'Publication '
                                                    + 'notification email')
          GROUP BY d.doc_id
         HAVING MIN(p.completed) >= '2007-09-01'
          ORDER BY MIN(p.completed), d.doc_id""", timeout = 300)
        docIds = []
        for row in cursor.fetchall():
            if len(docIds) >= maxDocs:
                break
            docId = row[0]
            if docId in nctIds:
                docIds.append(docId)
    #if not docIds:
    #    cdrcgi.bail("No matching protocols found")
    print """\
Content-type: text/html

<html>
 <head>
  <title>Publication Notification Emails</title>
  <style type='text/css'>
   body { font-family: 'Arial'; font-size: 10pt; }
   h1   { font-size: 14pt; color: blue; }
   th   { font-size: 12pt; color: maroon; }
   td   { font-size: 10pt; color: green; }
   b    { font-size: 10pt; color: maroon; }
   .err { color: red; font-weight: bold; }
  </style>
 </head>
 <body>
  <h1>Publication Notification Emails</h1>
  <b>Publication Notification Emails have been sent to:</b><br /><br />
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>CDR ID</th>
    <th>Primary ID</th>
    <th>NCT ID</th>
    <th>Recipients</th>
    <th>Mailer Tracking Docs</th>
   </tr>"""
    for docId in docIds:
        nctId = nctIds.get(docId)
        if not nctId:
            print """\
   <tr>
    <td colspan='5' class='err'>CDR%d has no NCT ID</td>
   </tr>""" % docId
        else:
            try:
                p = sendPubNotificationEmail(docId, nctId, cursor, conn)
                recips = p.recips.values()
                print (u"""\
   <tr>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>""" % (docId, p.primaryId, nctId,
               "; ".join(r.email for r in recips),
               ", ".join([`r.trackingDocId` for r in recips]))).encode('utf-8')
            except Exception, e:
                print """\
   <tr>
    <td colspan='5' class='err'>CDR%d: %s</td>
   </tr>""" % (docId, e)
    print """\
  </table>
 </body>
</html>"""
    sys.exit(0)

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
    digits = re.sub('[^\\d]+', '', docId)
    intId  = int(digits)

    # Make sure the corresponding document exists in version control,
    #   getting the last version number of the last valid version.
    try:
        cursor.execute("""\
            SELECT MAX(num)
              FROM doc_version
             WHERE id = ?
               AND val_status = 'V'""", intId)
        row = cursor.fetchone()
        if not row or not row[0]:
            cdrcgi.bail("No valid version found for document %d" % intId)

        # Document list contains one tuple of doc id + version number
        docList = ((intId, row[0]),)

        # Check to make sure requested lead org is in protocol.
        if leadOrg:
            leadOrgId = int(re.sub('[^\\d]+', '', leadOrg))
            cursor.execute("""\
                SELECT COUNT(*)
                  FROM query_term
                 WHERE path = '/InScopeProtocol/ProtocolAdminInfo'
                            + '/ProtocolLeadOrg/LeadOrganizationID/@cdr:ref'
                   AND doc_id = ?
                   AND int_val = ?""", (intId, leadOrgId))
            row = cursor.fetchone()
            if row[0] < 1:
                cdrcgi.bail("Protocol %s does not have lead org %s" %
                            (docId, leadOrg))
                            
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
                                              sourcePath, mailType),
                       timeout = 300)
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
                        AND p.pub_system = %d""" % ctrlDocId,
                       timeout = 300)

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
                                              sourcePath), timeout = 300)
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
             JOIN query_term prot_status
               ON prot_status.doc_id = protocol.id
             WHERE mailer_prot_doc.path = '/Mailer/Document/@cdr:ref'
               AND mailer_type.path = '/Mailer/Type'
               AND mailer_type.value = '%s'
               AND mailer_sent.path = '/Mailer/Sent'
               AND mailer_sent.value BETWEEN DATEADD(day, -120, GETDATE())
                                         AND DATEADD(day,  -60, GETDATE())
               AND doc_version.publishable = 'Y'
               AND doc_version.val_status  = 'V'
               AND protocol.active_status = 'A'
               AND prot_status.path = '/InScopeProtocol/ProtocolAdminInfo'
                                    + '/CurrentProtocolStatus'
               AND prot_status.value IN ('Active',
                                         'Approved-Not Yet Active')

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
          GROUP BY protocol.id""" % (maxDocs, annualMailers), timeout = 300)

        docList = cursor.fetchall()
    except cdrdb.Error, info:
        cdrcgi.bail("Failure selecting protocols: %s" % info[1][0])

#----------------------------------------------------------------------
# Find the protocols which need a status and participant check.
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
        pupCheck = ""
        if pup:
            pupDigits = re.sub('[^\d]+', '', pup)
            pupId  = int(pupDigits)
            pupCheck = " AND p.int_val = %d " % pupId
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
            AND r.value = 'Update person'""" + pupCheck, timeout = 300)

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
            AND p.update_mode IS NOT NULL""", timeout = 300)

        # Select based on update mode.
        if paper:
            if electronic:
                updateMode = "IN ('Web-based', 'Mail')"
            else:
                updateMode = "= 'Mail'"
        else:
            updateMode = "= 'Web-based'"
        cursor.execute("""\
SELECT DISTINCT TOP %d prot_id, prot_ver
           FROM #lead_orgs
          WHERE update_mode %s
       ORDER BY prot_id""" % (maxDocs, updateMode), timeout = 300)
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
if leadOrgId:
    parms.append(['LeadOrg', "%d" % leadOrgId])
if pupId:
    parms.append(['PUP', "%d" % pupId])
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
