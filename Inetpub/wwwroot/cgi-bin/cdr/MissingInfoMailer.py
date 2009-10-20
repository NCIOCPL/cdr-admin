#----------------------------------------------------------------------
#
# $Id$
#
# Program to send out a mailer for missing protocol information.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2008/09/02 20:00:23  bkline
# Wording changes and Unicode cleanup.
#
# Revision 1.2  2007/10/31 16:16:54  bkline
# Final modifications before being placed in production.
#
# Revision 1.1  2007/07/26 12:00:12  bkline
# New script to send out an email message asking for protocol information
# which has been omitted.
#
#----------------------------------------------------------------------
import cdr, cdrdb, cgi, cdrcgi, textwrap, xml.dom.minidom, xml.sax.saxutils
import time, cdrmailcommon, sys

# Collect parameters.
fields  = cgi.FieldStorage()
docId   = fields.getvalue('id') or None
body    = fields.getvalue('body') or None
email   = fields.getvalue('email') or None
recipId = fields.getvalue('recipId') or None
session = cdrcgi.getSession(fields) or None

# Make sure we're logged in.
if not session:
    cdrcgi.bail("Missing or expired CDR session")
if not cdr.canDo(session, "PROTOCOL MAILERS"):
    cdrcgi.bail("You are not authorized to send Protocol mailers")
if not cdr.canDo(session, "ADD DOCUMENT", "Mailer"):
    cdrcgi.bail("You are not authorized to create mailer tracking documents")

# Normalize the document ID.
if not docId:
    cdrcgi.bail("No document ID specified")
docId = cdr.exNormalize(docId)[1]

# Make sure we haven't already sent a mailer out for this protocol.
def checkForPreviousEmails(cursor, docId):
    cursor.execute("""\
        SELECT d.doc_id
          FROM query_term d
          JOIN query_term t
            ON d.doc_id = t.doc_id
         WHERE d.path = '/Mailer/Document/@cdr:ref'
           AND t.path = '/Mailer/Type'
           AND t.value = 'Missing information email'
           AND d.int_val = ?""", docId)
    mailerIds = [row[0] for row in cursor.fetchall()]
    if mailerIds:
        mailerIds = "; ".join([("CDR%d" % mailerId) for mailerId in mailerIds])
        msg = "Already sent missing info emailer(s) %s for CDR%d" % (mailerIds,
                                                                     docId)
        cdrcgi.bail(msg)
conn = cdrdb.connect('CdrGuest')
cursor = conn.cursor()
checkForPreviousEmails(cursor, docId)

# Send out the emailer if the user has approved it.
if body and email and recipId:
    sender     = "PDQUpdate@cancer.gov"
    subject    = "Missing required protocol information"
    sent       = time.strftime('%Y-%m-%dT%M:%H:%S')
    mailerMode = 'Email'
    mailerType = 'Missing information email'
    addresses  = email.split(';')
    recip      = addresses
    recipIds   = recipId.split(';')
    if not cdr.isProdHost():
        recip  = ['***REMOVED***', '***REMOVED***']
    try:
        cdr.sendMail(sender, recip, subject, body, mime = True)
    except Exception, e:
        cdrcgi.bail("Failure sending email to %s: %s" % (email, e))
    i = 0
    trackerIds = []
    for address in addresses:
        addressElement = u"""\
   <MailerAddress>
    <Email>%s</Email>
   </MailerAddress>
""" % address
        try:
            trackerId = cdrmailcommon.recordMailer(session, docId,
                                                   int(recipIds[i]),
                                                   mailerMode, mailerType,
                                                   sent, addressElement)
            trackerIds.append("CDR%d" % trackerId)
            i += 1
        except Exception, e:
            cdrcgi.bail("Failure recording email to %s: %s" % (email, e))
    cdrcgi.sendPage(u"""\
<html>
 <head>
  <title>Emailer for Missing Required Protocol Information</title>
  <style type='text/css'>
   body { font-family: arial; color: green; font-size: 12pt; font-weight: bold }
  </style>
 </head>
 <body>
  Emailer(s) %s successfully sent to %s
 </body>
</html>
""" % (u", ".join(trackerIds), u", ".join(addresses)))

# Collect the information we need.
class Protocol:

    class LeadOrgPerson:
        def __init__(self, node):
            self.role    = None
            self.cdrId   = None
            self.fragId  = None
            self.address = None
            self.nodeId  = node.getAttribute("cdr:id")
            for child in node.childNodes:
                if child.nodeName == "PersonRole":
                    self.role = cdr.getTextContent(child)
                elif child.nodeName == "Person":
                    personId = child.getAttribute('cdr:ref')
                    self.cdrId, self.fragId = cdr.exNormalize(personId)[1:]

        def wanted(self, mailAbstractTo, leadOrgRole):

            # If this is the person we send the abstract mailers to,
            # send this mailer to the person as well.
            if self.nodeId == mailAbstractTo:
                return True

            # Send to PUP at primary lead org.
            return self.role == "Update person" and leadOrgRole == "Primary"

        def findEmailAddress(self, cursor):
            cursor.execute("""\
                SELECT e.value
                  FROM query_term e
                  JOIN query_term i
                    ON e.doc_id = i.doc_id
                   AND LEFT(e.node_loc, 8) = LEFT(i.node_loc, 8)
                 WHERE e.path LIKE '/Person/PersonLocations/%Email'
                   AND i.path LIKE '/Person/PersonLocations/%/@cdr:id'
                   AND i.value = ?
                   AND e.doc_id = ?""", (self.fragId, self.cdrId))
            rows = cursor.fetchall()
            if rows:
                self.address = rows[0][0]
                return self.address
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
                   AND o.doc_id = ?""", (self.fragId, self.cdrId))
            rows = cursor.fetchall()
            if not rows:
                return None
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
            self.address = rows and rows[0][0] or None
            return self.address

    def __init__(self, docId, cursor):
        self.docId       = docId
        self.primaryId   = None
        self.originalId  = None
        self.missingInfo = []
        self.recips      = {}
        self.received    = u"[NO DATE OF RECEIPT FOUND]"
        self.title       = u"[NO ORIGINAL TITLE FOUND]"
        versions         = cdr.lastVersions(session, "CDR%010d" % docId)
        lastVersion      = versions[0]
        if lastVersion == -1:
            cdrcgi.bail("CDR%d has not been versioned" % docId)
        cursor.execute("""\
            SELECT xml
              FROM doc_version
             WHERE id = ?
               AND num = ?""", (docId, lastVersion))
        rows = cursor.fetchall()
        if not rows:
            cdrcgi.bail("Unable to retrieve version %d of CDR%d" % (lastVersion,
                                                                    docId))
        try:
            dom = xml.dom.minidom.parseString(rows[0][0].encode('utf-8'))
        except Exception, e:
            cdrcgi.bail("Failure parsing version %d of CDR%d: %s" %
                        (lastVersion, docId, e))
        nodes = dom.getElementsByTagName('MailAbstractTo')
        if not nodes:
            cdrcgi.bail("CDR%d has no MailAbstractTo element" % docId)
        mailAbstractTo = cdr.getTextContent(nodes[0])
        for node in dom.documentElement.childNodes:
            if node.nodeName == "ProtocolAdminInfo":
                for child in node.childNodes:
                    if child.nodeName == "ProtocolLeadOrg":
                        orgRole = Protocol.getOrgRole(child)
                        for grandchild in child.childNodes:
                            if grandchild.nodeName == "LeadOrgPersonnel":
                                person = Protocol.LeadOrgPerson(grandchild)
                                if person.cdrId not in self.recips:
                                    if person.wanted(mailAbstractTo, orgRole):
                                        if person.findEmailAddress(cursor):
                                            self.recips[person.cdrId] = person
            elif node.nodeName == "ProtocolIDs":
                for child in node.childNodes:
                    if child.nodeName == "PrimaryID":
                        for grandchild in child.childNodes:
                            if grandchild.nodeName == 'IDString':
                                primaryId = cdr.getTextContent(grandchild)
                                self.primaryId = primaryId.strip()
                    elif child.nodeName == 'OtherID':
                        idType = None
                        idString = None
                        for grandchild in child.childNodes:
                            if grandchild.nodeName == 'IDString':
                                idString = cdr.getTextContent(grandchild)
                            elif grandchild.nodeName == 'IDType':
                                idType = cdr.getTextContent(grandchild)
                        if idType.strip() == "Institutional/Original":
                            originalId = idString.strip()
                            if originalId:
                                self.originalId = originalId
            elif node.nodeName == 'ProtocolProcessingDetails':
                for elem in node.getElementsByTagName('MissingInformation'):
                    mi = cdr.getTextContent(elem).strip()
                    if mi:
                        self.missingInfo.append(mi)
            elif node.nodeName == 'ProtocolTitle':
                if node.getAttribute('Type') == 'Original':
                    title = cdr.getTextContent(node)
                    if title:
                        self.title = title
            elif node.nodeName == 'ProtocolSources':
                for child in node.childNodes:
                    if child.nodeName == 'ProtocolSource':
                        for grandchild in child.childNodes:
                            if grandchild.nodeName == 'DateReceived':
                                received = cdr.getTextContent(grandchild)
                                received = received.strip()
                                if received:
                                    self.received = received
        if not self.recips:
            cdrcgi.bail("Unable to find suitable recipient for mailer")
        if not self.originalId:
            self.originalId = self.primaryId or u"[NO ORIGINAL ID FOUND]"
        if not self.primaryId:
            self.primaryId = u"[NO PRIMARY ID FOUND]"

    @staticmethod
    def getOrgRole(node):
        for child in node.getElementsByTagName('LeadOrgRole'):
            return cdr.getTextContent(child).strip()

protocol = Protocol(docId, cursor)
if not protocol.missingInfo:
    cdrcgi.bail("CDR%d has no missing information" % docId)

# Assemble the email body.
wrapper = textwrap.TextWrapper()
paras = []
para = (u'Your protocol "%s," "%s," was received for inclusion in the '
        u'National Cancer Institute\'s PDQ database on %s.  The protocol '
        u'has been assigned the PDQ Primary ID of: %s.  Please reference this '
        u'protocol number in all future communications.' %
        (protocol.originalId, protocol.title, protocol.received,
         protocol.primaryId))
paras = [wrapper.fill(para)]
para = (u'Your submission will publish to Cancer.gov within three weeks of '
        u'receipt of a complete submission.  When the trial is published, you '
        u'will receive a confirmation email with your trial registration '
        u'numbers, including the NCT ID number.  Shortly after publication, '
        u'and annually thereafter, you will also be sent a copy of the '
        u'abstract and key retrieval terms for your review.')
paras.append(wrapper.fill(para))
para = wrapper.fill(u'At this time, your submission is not complete.  Before '
                    u'we can list your trial in the PDQ Database on '
                    u'Cancer.gov, we will need the following documentation:')
for mi in protocol.missingInfo:
    para += u"\n  * %s" % mi
paras.append(para)
if 'Responsible party' in protocol.missingInfo:
    paras.append(u"""\
Responsible Party: The entity responsible for registering is the
"responsible party."

Responsible party is defined as:

(1) the sponsor of the clinical trial (as defined in 21 C.F.R. 50.3)
    [http://sturly.com/resppartystatute],

    or

(2) the principal investigator of such clinical trial if so designated
    by a sponsor, grantee, contractor, or awardee (provided that "the
    principal investigator is responsible for conducting the trial, has
    access to and control over the data from the clinical trial, has
    the right to publish the results of the trial, and has the ability
    to meet all of the requirements" for submitting information under
    the law.)""")
paras.append(wrapper.fill(u'This information can be emailed to '
                          u'PDQUpdate@cancer.gov or faxed to us at '
                          u'301-402-6728.'))
paras.append(wrapper.fill(u'If you have any questions, please call the PDQ '
                          u'Protocol Coordinator at 301-496-7406 or send an '
                          u'e-mail to PDQUpdate@cancer.gov.'))
paras.append(u"""\
PDQ Protocol Coordinator
Office of Cancer Content Management""")
paras.append(u"""\
Submitting new trials to PDQ?  Try our new online submission portal:
http://pdqupdate.cancer.gov/submission""")
body = u"\n\n".join(paras) + u"\n"

# Show it to the user for her approval.
keys = protocol.recips.keys()
keys.sort()
addresses = []
recipIds  = []
for key in keys:
    addresses.append(protocol.recips[key].address)
    recipIds.append(`key`)
html = u"""\
Content-type: text/html; charset=utf-8

<html>
 <head>
  <meta http-equiv='Content-Type' content='text/html;charset=utf-8' />
  <title>Emailer for Missing Required Protocol Information</title>
  <style type='text/css'>
   body { font-family: arial; }
   h1   { color: maroon; font-size: 14pt; }
   h2   { color: maroon; font-size: 12pt; }
   pre  { font-size: 10pt; color: blue; }
  </style>
 </head>
 <body>
  <h1>Proposed Emailer for CDR%d</h1>
  <h2>To be sent to %s</h2>
  <pre>%s</pre>
  <form method='post' action='MissingInfoMailer.py'>
   <input type='submit' name='Send' value='Send' />
   <input type='hidden' name='%s' value='%s' />
   <input type='hidden' name='id' value='%s' />
   <input type='hidden' name='body' value=%s />
   <input type='hidden' name='email' value='%s' />
   <input type='hidden' name='recipId' value='%s' />
  </form>
 </body>
</html>
""" % (docId, u", ".join(addresses), cgi.escape(body), cdrcgi.SESSION, session,
       docId, xml.sax.saxutils.quoteattr(body),
       u";".join(addresses), u";".join(recipIds))
sys.stdout.write(html.encode('utf-8'))
