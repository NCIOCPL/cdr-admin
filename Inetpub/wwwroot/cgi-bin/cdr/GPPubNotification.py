#----------------------------------------------------------------------
#
# $Id$
#
# Send out email notification to GP who has been added to the directory.
#
# BZIssue::4779
#
#----------------------------------------------------------------------
import cgi, cdr, cdrcgi, re, string, cdrdb, cdrpubcgi, cdrmailcommon, sys
import textwrap, time, lxml.etree as etree

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields      = cgi.FieldStorage()
session     = cdrcgi.getSession(fields)
request     = cdrcgi.getRequest(fields)
docId       = fields and fields.getvalue("DocId")      or None
userPick    = fields and fields.getvalue("userPick")   or None
maxMails    = fields and fields.getvalue("maxMails")   or 'No limit'
title       = "CDR Administration"
section     = "GP Publication Notification"
SUBMENU     = "Mailer Menu"
buttons     = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script      = 'GPPubNotification.py'
header      = cdrcgi.header(title, title, section, script, buttons,
                            stylesheet = """\
 <style type='text/css'>
   th { font-size: 11pt }
  </style>
  <script language='JavaScript'>
  </script>
 """)
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
   <table border='0'>
    <tr>
     <th align='right'>Send only to GP for this CDR ID (optional):&nbsp;</th>
     <td><input name='DocId' /></td>
    </tr>
    <tr>
     <th align='right'
     >Send no more than this many notifications (optional):&nbsp;</th>
     <td><input name='maxMails' value='No limit'/></td>
    </tr>
   </table>
   <br />   
   <input type='Submit' name = 'Request' value = 'Submit'>
   <input type='hidden' name='%s' value='%s'>
  </form>
 </body>
</html>
""" % (cdrcgi.SESSION, session)
    cdrcgi.sendPage(header + form)

#----------------------------------------------------------------------
# Send out a publication notification email message.
#----------------------------------------------------------------------
class GP:

    # Class-level values.
    wrapper = textwrap.TextWrapper()
    sender  = 'GeneticsDirectory@cancer.gov'
    subject = u"NCI Cancer Genetics Services Directory Listing Notification"
    url = u"http://www.cancer.gov/search/view_geneticspro.aspx?personid=%d"

    @staticmethod
    def getMailerAddress(node):
        usedFor = set((node.get('UsedFor') or u'').split())
        if 'GPMailer' in usedFor:
            for child in node.findall(".//SpecificEmail"):
                email = child.text
                if email:
                    return email.strip()
        return None

    def __init__(self, cursor, docId):
        self.docId = docId
        self.name = self.email = None
        cursor.execute("SELECT xml FROM document WHERE id = ?", docId)
        docXml = cursor.fetchall()[0][0]
        tree = etree.XML(docXml.encode('utf-8'))
        first = last = u""
        for node in tree.findall('PersonNameInformation'):
            for child in node:
                if child.tag == 'GivenName':
                    first = child.text
                elif child.tag == 'SurName':
                    last = child.text
        self.name = (u"%s %s" % (first, last)).strip()
        for name in ('OtherPracticeLocation', 'PrivatePractice'):
            for node in tree.findall('PersonLocations/%s' % name):
                self.email = GP.getMailerAddress(node)
                if self.email:
                    return
        #self.name = u'Klem Kadiddlehopper'
        #self.email = u'klem@kadiddle.org'

def fix(me):
    if not me:
        return ""
    return cgi.escape(me).encode('utf-8')
    
def sendPubNotificationEmail(gp, cursor, conn):

    addresses = [gp.email]
    url = GP.url % gp.docId
    top = u""
    if True or not cdr.isProdHost():
        top = u"""\
<p>[SENT TO YOU FOR TESTING, INSTEAD OF TO %s]</p>
""" % ", ".join(addresses)
        addresses = ['***REMOVED***', '***REMOVED***',
                     '***REMOVED***', '***REMOVED***']
    body = u"""\
%s<p>Thank you for applying to be listed in the NCI Cancer Genetics Services Directory. Your application has been processed and your information has been added to the directory on NCI's Web site, <a href='http://www.cancer.gov/'>Cancer.gov</a>.</p>

<p>You can view your information in the directory by clicking on the link below or by searching the <a href='http://www.cancer.gov/search/geneticsservices/'>Directory</a> using your last name.</p>

<a href='%s'>%s</a>

<p>Please contact us at <a href='mailto:GeneticsDirectory@cancer.gov'
>GeneticsDirectory@cancer.gov</a> with any changes that you may have.
We will also be contacting you annually to verify your directory
information.  We appreciate your help in keeping the NCI Cancer
Genetics Directory current.</p>

<p style='font-style: italic'
>The NCI Genetics Services Directory Coordinator<br />
Office of Cancer Content Management<br />
National Cancer Institute</p>
""" % (top, url, url)
    try:
        cdr.sendMailMime(GP.sender, addresses, GP.subject, body, 'html')
    except Exception, e:
        raise Exception("failure sending email notice to %s: %s" %
                        (", ".join(addresses), e))
    mailerMode, mailerType = 'Email', 'GP publication notification email'
    sent = time.strftime('%Y-%m-%dT%M:%H:%S')
    address = u"""\
   <MailerAddress>
    <Email>%s</Email>
   </MailerAddress>
""" % gp.email
    try:
        tId = cdrmailcommon.recordMailer(session, gp.docId, gp.docId,
                                         mailerMode, mailerType, sent,
                                         address)
    except Exception, e:
        raise Exception("Failure recording mailer to %s for CDR%d: %s" %
                        (gp.email, gp.docId, e))
    return tId

#----------------------------------------------------------------------
# If we get this far, we've been asked to send out mailers.
#----------------------------------------------------------------------
conn = cdrdb.connect()
cursor = conn.cursor()

#----------------------------------------------------------------------
# Find all of the legacy GPs (don't send them mailers).
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT doc_id
      FROM query_term
     WHERE path = '/Person/ProfessionalInformation/GeneticsProfessionalDetails'
                + '/LegacyGeneticsData/LegacyID'""")
legacyGPs = set([row[0] for row in cursor.fetchall()])

#----------------------------------------------------------------------
# Don't send notification twice.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT d.int_val
      FROM query_term d
      JOIN query_term t
        ON d.doc_id = t.doc_id
     WHERE d.path = '/Mailer/Document/@cdr:ref'
       AND t.path = '/Mailer/Type'
       AND t.value = 'GP publication notification email'""")
alreadySent = set([row[0] for row in cursor.fetchall()])
    
#----------------------------------------------------------------------
# Collect a list of all published GP docs.
#----------------------------------------------------------------------
cursor.execute("""\
    SELECT g.doc_id
      FROM query_term g
      JOIN pub_proc_cg p
        ON p.id = g.doc_id
     WHERE g.path = '/Person/ProfessionalInformation'
                  + '/GeneticsProfessionalDetails/AdministrativeInformation'
                  + '/Directory/Include'""")
pubGPs = set([row[0] for row in cursor.fetchall()])

#----------------------------------------------------------------------
# Have we been asked to send out a specific mailer?
#----------------------------------------------------------------------
if docId:
    docId = cdr.exNormalize(docId)[1]
    if docId in legacyGPs:
        cdrcgi.bail("We're not allowed to send notification to legacy "
                    "GP %d" % docId)
    if docId in alreadySent:
        cdrcgi.bail("GP for %d has already received publication notification" %
                    docId)
    if docId not in pubGPs:
        cdrcgi.bail("CDR%d does not represent a published GP document")
    docIds = [docId]
    
#----------------------------------------------------------------------
# If not, collect the GPs due for the notification.
#----------------------------------------------------------------------
docIds = []
# legacyGPs = set() # for debugging
for docId in pubGPs:
    if docId not in legacyGPs and docId not in alreadySent:
        docIds.append(docId)
        if len(docIds) >= maxDocs:
            break

#----------------------------------------------------------------------
# Show the user what we've done as we're sending out the mailers.
#----------------------------------------------------------------------
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
    <th>Name</th>
    <th>Email</th>
    <th>Mailer Tracking Doc</th>
   </tr>"""
for docId in docIds:
    try:
        gp = GP(cursor, docId)
    except Exception, e:
        print """\
   <tr>
    <td colspan='4' class='err'>Failure parsing CDR%d: %s</td>
   </tr>""" % (docId, e)
        continue
    if not gp.email:
        print """\
   <tr>
    <td colspan='4' class='err'>CDR%d has no email address</td>
   </tr>""" % gp.docId
    else:
        try:
            mailerId = sendPubNotificationEmail(gp, cursor, conn)
            print (u"""\
   <tr>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>""" % (gp.docId, fix(gp.name), fix(gp.email), mailerId)).encode('utf-8')
        except Exception, e:
            print """\
   <tr>
    <td colspan='5' class='err'>CDR%d: %s</td>
   </tr>""" % (docId, e)
print """\
  </table>
 </body>
</html>"""
