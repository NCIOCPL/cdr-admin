#----------------------------------------------------------------------
#
# $Id$
#
#----------------------------------------------------------------------
import cdrdb, glob, xml.dom.minidom, os, sys, cgi, cdrcgi, cdr, cdrmailcommon
import tarfile

#----------------------------------------------------------------------
# Get the parameters from the request.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
jobId    = fields and fields.getvalue("JobId")      or None
xmlFile  = fields and fields.getvalue("XmlFile")    or None
rtsBatch = fields and fields.getvalue("RtsBatch")   or None
session  = cdrcgi.getSession(fields) or 'guest' # cdrcgi.bail("Not logged in")
action   = cdrcgi.getRequest(fields)
script   = 'EmailerReview.py'
title    = "CDR Administration"
section  = "Electronic Mailer Review"
SUBMENU  = "Mailer Menu"
buttons  = [SUBMENU, cdrcgi.MAINMENU, "Log Out"]
extra    = ""
style    = """\
  <style type='text/css'>
   li { font-size: 13; font-family: Arial, sans-serif; }
   a:link, a.visited, a.active  { text-decoration: underline }
  </style>
"""

#----------------------------------------------------------------------
# Handle navigation requests.
#----------------------------------------------------------------------
if action == cdrcgi.MAINMENU:
    cdrcgi.navigateTo("Admin.py", session)
elif action == SUBMENU:
    cdrcgi.navigateTo("Mailers.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if action == "Log Out": 
    cdrcgi.logout(session)

#----------------------------------------------------------------------
# Do all the work from the mailer output area.
# Try the new output location first, then fall back on the old.
#----------------------------------------------------------------------
try:
    os.chdir('d:/cdr/Output/Mailers')
except:
    os.chdir('d:/cdr/mailers/output')

#----------------------------------------------------------------------
# Clear out original files for a job if requested.
#----------------------------------------------------------------------
if action == 'Archive Job':
    try:
        directory = 'Job%s-e' % jobId
        for name in glob.glob('%s/*' % directory):
            os.unlink(name)
        os.rmdir(directory)
    except:
        cdrcgi.bail('Failure archiving job %s' % jobId)
    extra = "<p style='color:green'>Job %s archived successfully</p>" % jobId
    jobId = None

#----------------------------------------------------------------------
# Information about upload/import of an electronic mailer job.
#----------------------------------------------------------------------
class JobInfo:
    def __init__(self, status = None, uploaded = None, imported = None):
        self.status   = status
        self.uploaded = uploaded,
        self.imported = imported
    def showStatus(self):
        if self.status == 'UPL':
            return '(sent %s)' % self.uploaded
        elif self.status == 'IMP':
            return '(imported %s)' % self.imported
        elif self.status:
            return '(status: %s)' % self.status
        else:
            return '(not yet sent)'

#----------------------------------------------------------------------
# Show the raw XML for a single emailer document if requested.
#----------------------------------------------------------------------
if xmlFile:
    file = open(xmlFile, "rb")
    cdrcgi.sendPage(file.read(), 'xml')

#----------------------------------------------------------------------
# Put up a menu of emailer jobs.
#----------------------------------------------------------------------
if not jobId:
    html = cdrcgi.header(title, title, section, script, buttons,
                         numBreaks = 1, stylesheet = style) + u"""\
   <input type='hidden' name='%s' value='%s'>
   %s
   <p>Select job to review:</p>
   <ul>
""" % (cdrcgi.SESSION, session, extra)
    conn = cdrmailcommon.emailerConn('dropbox')
    cursor = conn.cursor()
    cursor.execute("SELECT id, status, uploaded, imported FROM emailer_job")
    uploadedJobs = {}
    for (job, status, uploaded, imported) in cursor.fetchall():
        uploadedJobs[job] = JobInfo(status, uploaded, imported)
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
    cursor.execute("""\
    SELECT DISTINCT j.id
               FROM pub_proc j
               JOIN pub_proc_parm p
                 ON p.pub_proc = j.id
              WHERE p.parm_name = 'UpdateModes'
                AND p.parm_value LIKE '%[Web-based]%'
                AND j.status = 'Success'
                AND j.completed IS NOT NULL""")
    okJobs = {}
    for row in cursor.fetchall():
        okJobs[row[0]] = 1
    jobs = []
    for name in glob.glob('Job*-e'):
        jobId = int(name[3:-2])
        if jobId in okJobs:
            jobs.append(jobId)
    jobs.sort()
    jobs.reverse()
    for job in jobs:
        if job in uploadedJobs:
            jobInfo = uploadedJobs[job]
        else:
            jobInfo = JobInfo()
        html += u"""\
   <li><a href='%s?JobId=%d&%s=%s'>Mailer Job %d %s</a></li>
""" % (script, job, cdrcgi.SESSION, session, job, jobInfo.showStatus())
    html += u"""\
  </ul>
 </body>
</html>
"""
    cdrcgi.sendPage(html)
#----------------------------------------------------------------------
# Dig the pub_subset value out of the manifest file.
#----------------------------------------------------------------------
def lookupMailerType():
    dom = xml.dom.minidom.parse('manifest.xml')
    mailerType = dom.documentElement.getAttribute('PubSubset')
    return mailerType or "Unknown"

#----------------------------------------------------------------------
# Display the components of a single emailer job.
#----------------------------------------------------------------------
jobName = "Job%s-e" % jobId
os.chdir(jobName)

emConn = cdrmailcommon.emailerConn('dropbox')
emCursor = emConn.cursor()
if action == 'Send Job':
    emCursor.execute("SELECT COUNT(*) FROM emailer_job WHERE id = %s", jobId)
    rows = emCursor.fetchall()
    if rows[0][0]:
        cdrcgi.bail("Job %s already sent" % jobId)
    mailerType = lookupMailerType()
    #result = cdr.runCommand("d:\\bin\\zip ../%s *" % jobName)
    #if result.code:
    #    cdrcgi.bail("Failure creating archive for %s: %s" % (jobName,
    #                                                         result.output))
    #file = open("../%s.zip" % jobName, "rb")
    tarName = "../%s.tar.bz2" % jobName
    workFile = tarfile.open(tarName, 'w:bz2')
    for xmlFilename in glob.glob("*.xml"):
        workFile.add(xmlFilename)
    workFile.close()
    file = open(tarName, "rb")
    package = file.read()
    file.close()
    emCursor.execute("""\
        INSERT INTO emailer_job (id, archive, archive_type, uploaded,
                                 mailer_type)
             VALUES (%s, %s, %s, NOW(), %s)""", (jobId, package, "tarfile",
                                                 mailerType))
    emConn.commit()

if rtsBatch:
    emCursor.execute("""\
        UPDATE emailer_batch
           SET failed = NOW()
         WHERE recip = %s""", rtsBatch)
    emConn.commit()
emCursor.execute("""\
    SELECT status, uploaded, imported
      FROM emailer_job
     WHERE id = %s""", jobId)
rows = emCursor.fetchall()
if rows:
    (status, uploaded, imported) = rows[0]
    jobInfo = JobInfo(status, uploaded, imported)
else:
    jobInfo = JobInfo()
button = jobInfo.status and 'Archive Job' or 'Send Job'
header = cdrcgi.header(title, title, section, script, [button] + buttons,
                       numBreaks = 1, stylesheet = style + """\
  <script language='JavaScript'>
   <!--
    function markAsRts(batch) {
        if (!confirm('Mark this mailer set as \\'Returned to Sender\\'?\\n' +
                     'This will block the recipient from further ' +
                     'access to the mailers in the set.'))
            return;
        var frm = document.forms[0];
        frm.RtsBatch.value = batch;
        frm.method         = 'POST';
        frm.submit();
    // -->
   }
  </script>
""")
title  = "Emailers For Job %s %s" % (jobId, jobInfo.showStatus())
html   = header + u"""\
  <input type='hidden' name='JobId' value='%s'>
  <input type='hidden' name='%s' value='%s'>
  <input type='hidden' name='RtsBatch' value=''>
  <h3>%s</h3>
""" % (jobId, cdrcgi.SESSION, session, title)

class Emailer:
    def __init__(self, node):
        self.docId = node.getAttribute('id')
        self.fileName = ''
        self.protId = ''
        for child in node.childNodes:
            if child.nodeName == 'EmailerFilename':
                self.fileName = cdr.getTextContent(child)
            elif child.nodeName == 'EmailerAttrs':
                for grandchild in child.childNodes:
                    if grandchild.nodeName == 'EmailerAttr':
                        if grandchild.getAttribute('name') == 'ProtID':
                            self.protId = cdr.getTextContent(grandchild)
                            break

class Recipient:
    def __init__(self, node):
        self.recipId = ''
        self.fileName = ''
        self.address = ''
        self.emailers = []
        for child in node.childNodes:
            if child.nodeName == 'EmailerRecipientID':
                val = cdr.getTextContent(child)
                hash = val.find('#')
                self.recipId = val[:hash]
            elif child.nodeName == 'EmailerFilename':
                self.fileName = cdr.getTextContent(child)
            elif child.nodeName == 'EmailerAddress':
                self.address = cdr.getTextContent(child)
            elif child.nodeName == 'EmailerDocuments':
                for grandchild in child.childNodes:
                    if grandchild.nodeName == 'EmailerDocument':
                        self.emailers.append(Emailer(grandchild))

dom = xml.dom.minidom.parse('manifest.xml')
html += u"""\
  <b>Job Time: </b> %s<br>
  <b>Job Type: </b> %s<br>
  <ul>
""" % (dom.documentElement.getAttribute('JobTime'),
       dom.documentElement.getAttribute('JobType'))
recipients = []
if jobInfo.status == "IMP":
    emCursor.execute("""\
        SELECT recip, reported, failed
          FROM emailer_batch
         WHERE job = %s
      ORDER BY recip""", jobId)
    emailerBatches = emCursor.fetchall()
for node in dom.documentElement.childNodes:
    if node.nodeName == 'EmailerRecipient':
        recipients.append(Recipient(node))
label = jobInfo.status and "Mailed" or "Mail"
for i in range(len(recipients)):
    recipient = recipients[i]
    address   = recipient.address
    fileName  = recipient.fileName
    recipId   = recipient.recipId
    extra     = ""
    if jobInfo.status == "IMP":
        # NOTE: This code relies on the fact that the emailer batches
        #       are imported into the emailer database in the order
        #       that they appear in the manifest file, and are assigned
        #       a recipient ID in ascending order.
        recip, reported, failed = emailerBatches[i]
        if failed:
            extra = (" <span style='color:red; font-weight:bold'>"
                     "(Marked RTS %s)</span>" % str(failed)[:10])
        elif reported:
            extra = " (Tracking updated %s)" % str(reported)[:10]
        else:
            extra = ("&nbsp;&nbsp;&nbsp;"
                     "<button onclick='javascript:markAsRts(%s)'>"
                     "Mark As RTS</button>" % recip)
            
    html += u"""\
   <li><b>%s to: </b> %s
    (<a href='%s?XmlFile=Job%s-e/%s'>Recipient XML</a>)
    (<a href='QcReport.py?Session=guest&DocId=%s'>Person QC Report</a>)%s
    <ul>
""" % (label, address, script, jobId, fileName, recipId, extra)
    for emailer in recipient.emailers:
        html += u"""\
     <li>
      <b>Protocol ID: </b> %s
      (<a href='%s?XmlFile=Job%s-e/%s'>Emailer XML</a>)
      (<a href='QcReport.py?Session=guest&DocId=%s'>Document QC Report</a>)
     </li>
""" % (emailer.protId, script, jobId, emailer.fileName, emailer.docId)
    html += u"""\
    </ul>
   </li>
"""
html += u"""
  </ul>
 </body>
</html>
"""
cdrcgi.sendPage(html)
