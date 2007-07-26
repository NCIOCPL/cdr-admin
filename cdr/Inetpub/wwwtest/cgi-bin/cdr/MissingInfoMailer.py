#----------------------------------------------------------------------
#
# $Id: MissingInfoMailer.py,v 1.1 2007-07-26 12:00:12 bkline Exp $
#
# Program to send out a mailer for missing protocol information.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdr, cdrdb, cgi, cdrcgi, textwrap, xml.dom.minidom, xml.sax.saxutils
import time, cdrmailcommon

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
        msg = "Already sent missing info emailers %s for CDR%d" % (mailerIds,
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
    recip      = ['***REMOVED***']
    #recip      = ('bkline@speakeasy.net', '***REMOVED***')
    #recip      = ['***REMOVED***', '***REMOVED***']
    #recip      = [email]
    address    = u"""\
   <MailerAddress>
    <Email>%s</Email>
   </MailerAddress>
""" % email
    try:
        cdr.sendMail(sender, recip, subject, body)
    except Exception, e:
        cdrcgi.bail("Failure sending email to %s: %s" % (email, e))

    try:
        trackerId = cdrmailcommon.recordMailer(session, docId, int(recipId),
                                               mailerMode, mailerType, sent,
                                               address)
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
  Emailer CDR%d successfully sent to %s
 </body>
</html>
""" % (trackerId, email))

# Collect the information we need.
class Protocol:
    def __init__(self, docId, cursor):
        self.docId       = docId
        self.primaryId   = u"[NO PRIMARY ID FOUND]"
        self.originalId  = u"[NO ORIGINAL ID FOUND]"
        self.missingInfo = []
        self.received    = u"[NO DATE OF RECEIPT FOUND]"
        self.title       = u"[NO ORIGINAL TITLE FOUND]"
        self.recip       = None
        self.recipId     = None
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
        personId = None
        for node in dom.getElementsByTagName('LeadOrgPersonnel'):
            if node.getAttribute("cdr:id") == mailAbstractTo:
                for child in node.childNodes:
                    if child.nodeName == 'Person':
                        personId = child.getAttribute('cdr:ref')
                        self.recipId, fragId = cdr.exNormalize(personId)[1:]
                        self.recip = Protocol.findEmailAddress(cursor,
                                                               self.recipId,
                                                               fragId)
                        break
        if not self.recipId:
            cdrcgi.bail("Unable to find lead org person for "
                        "MailAbstractTo value %s" % mailAbstractTo)
        if not self.recip:
            cdrcgi.bail("Unable to find email address for %s" % personId)
        for node in dom.documentElement.childNodes:
            if node.nodeName == "ProtocolIDs":
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
                                
    @staticmethod
    def findEmailAddress(cursor, docId, fragId):
        cursor.execute("""\
            SELECT e.value
              FROM query_term e
              JOIN query_term i
                ON e.doc_id = i.doc_id
               AND LEFT(e.node_loc, 8) = LEFT(i.node_loc, 8)
             WHERE e.path LIKE '/Person/PersonLocations/%Email'
               AND i.path LIKE '/Person/PersonLocations/%/@cdr:id'
               AND i.value = ?
               AND e.doc_id = ?""", (fragId, docId))
        rows = cursor.fetchall()
        if rows:
            return rows[0][0]
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
               AND o.doc_id = ?""", (fragId, docId))
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
        return rows and rows[0][0] or None

protocol = Protocol(docId, cursor)
if not protocol.missingInfo:
    cdrcgi.bail("CDR%d has no missing information" % docId)

# Assemble the email body.
wrapper = textwrap.TextWrapper()
paras = []
para = (u'Your protocol "%s," "%s," was received for inclusion in the '
        u'National Cancer Institute\'s PDQ database on %s.  The protocol '
        u'has been assigned the PDA Primary ID of: %s.  Please reference this '
        u'protocol number in all future communications' %
        (protocol.originalId, protocol.title, protocol.received,
         protocol.primaryId))
paras = [wrapper.fill(para)]
para = ('Your submission will publish to Cancer.gov within three weeks of '
        'receipt of a complete submission.  When the trial is published, you '
        'will receive a confirmation email with your trial registration '
        'numbers, including the NCT ID number.  Shortly after publication, '
        'and annually thereafter, you will also be sent a copy of the '
        'abstract and key retrieval terms for your review.')
paras.append(wrapper.fill(para))
para = wrapper.fill('At this time, your submission is not complete.  Before '
                    'we can list your trial in the PDQ Database on '
                    'Cancer.gov, we will need the following documentation:')
for mi in protocol.missingInfo:
    para += "\n  * %s" %mi
para += "\n" + wrapper.fill('This information can be emailed to '
                            'pdqupdate@cancer.gov or faxed to us at '
                            '301-402-6728.')
paras.append(para)
paras.append(wrapper.fill('If you have any questions, please call the PDQ '
                          'Protocol Coordinator at 301-496-7406 or send an '
                          'e-mail to PDQUpdate@cancer.gov.'))
paras.append("""\
PDQ Protocol Coordinator
Office of Cancer Content Management""")
paras.append("""\
Submitting new trials to PDQ?  Try our new online submission portal:
http://pdqupdate.cancer.gov/submission""")
body = u"\n\n".join(paras) + u"\n"

# Show it to the user for her approval.
html = """\
<html>
 <head>
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
  <form method='post'>
   <input type='submit' name='Send' value='Send' />
   <input type='hidden' name='%s' value='%s' />
   <input type='hidden' name='id' value='%s' />
   <input type='hidden' name='body' value=%s />
   <input type='hidden' name='email' value='%s' />
   <input type='hidden' name='recipId' value='%s' />
  </form>
 </body>
</html>
""" % (docId, protocol.recip, cgi.escape(body), cdrcgi.SESSION, session,
       docId, xml.sax.saxutils.quoteattr(body),
       protocol.recip, protocol.recipId)
cdrcgi.sendPage(html.encode('latin-1', 'replace'))
