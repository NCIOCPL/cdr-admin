#----------------------------------------------------------------------
#
# $Id$
#
# New report to track the processing of audio pronunciation media
# documents.
#
# BZIssue::5123
#
#----------------------------------------------------------------------
import cdr, cdrcgi, cgi, time, cdrbatch

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
today     = time.strftime('%Y-%m-%d')
fields    = cgi.FieldStorage()
request   = cdrcgi.getRequest(fields)
session   = cdrcgi.getSession(fields)
email     = cdr.getEmail(session)
language  = fields.getvalue('Language') or 'all'
startDate = fields.getvalue('StartDate') or '2011-01-01'
endDate   = fields.getvalue('EndDate') or today
SUBMENU   = "Report Menu"
buttons   = ["Submit", SUBMENU, cdrcgi.MAINMENU, "Log Out"]
script    = "PronunciationRecordings.py"
title     = "CDR Administration"
section   = "Audio Pronunciation Recordings Tracking Report"
header    = cdrcgi.header(title, title, section, script, buttons,
                          stylesheet = """\
   <link type='text/css' rel='stylesheet' href='/stylesheets/CdrCalendar.css'>
   <script language='JavaScript' src='/js/CdrCalendar.js'></script>
   <style type='text/css'>
    .CdrDateField { width: 100px; }
   </style>
""")

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
    cdrcgi.navigateTo("Reports.py", session)

#----------------------------------------------------------------------
# Handle request to log out.
#----------------------------------------------------------------------
if request == "Log Out": 
    cdrcgi.logout(session)

## #----------------------------------------------------------------------
## # Connect to the CDR database.
## #----------------------------------------------------------------------
## try:
##     conn   = cdrdb.connect('CdrGuest')
##     cursor = conn.cursor()
## except cdrdb.Error, info:
##     cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Put up the menu if we don't have selection criteria yet.
#----------------------------------------------------------------------
if not request:
    form = """\
   <input type='hidden' name='%s' value='%s' />
   <fieldset class='dates'>
    <legend>Date Range</legend>
    <label for='start'>Start Date:</label>
    <input name='StartDate' value='2011-01-01' class='CdrDateField'
           id='start' /> &nbsp;
    <label for='end'>End Date:</label>
    <input name='EndDate' value='%s' class='CdrDateField' id='end' />
   </fieldset>
   <fieldset>
    <legend>Language</legend>
    <input name='Language' type='radio' value='all' class='choice'
           checked='checked' /> All<br />
    <input name='Language' type='radio' value='en' class='choice' /> English
    <br />
    <input name='Language' type='radio' value='es' class='choice' /> Spanish
  </form>
""" % (cdrcgi.SESSION, session, today)
    cdrcgi.sendPage(header + form + """\
 </body>
</html>
""")

#----------------------------------------------------------------------
# Collection information we'll need for each Media document.
#----------------------------------------------------------------------
## class MediaDoc:
##     def __init__(self, docId, created, cursor):
##         self.docId = docId
##         self.created = created
##         self.title = self.status = self.statusDate = None
##         self.firstPub = self.lastMod = None
##         self.pubDate = None
##         self.glossaryTerms = []
##         self.comments = []
##         self.lastVersionPublishable = False
##         versions = cdr.lastVersions('guest', 'CDR%010d' % docId)
##         if versions[0] == versions[1] and versions[0] > 0:
##             self.lastVersionPublishable = True
##         cursor.execute("SELECT dt FROM last_doc_publication WHERE doc_id = ?",
##                        docId)
##         rows = cursor.fetchall()
##         if rows:
##             self.pubDate = rows[0][0]
##         cursor.execute("SELECT first_pub, xml FROM document WHERE id = ?",
##                        docId)
##         self.firstPub, docXml = cursor.fetchall()[0]
##         tree = etree.XML(docXml.encode('utf-8'))
##         for node in tree.findall('MediaTitle'):
##             self.title = node.xpath("string()")
##         for node in tree.findall('ProposedUse/Glossary'):
##             self.glossaryTerms.append(node.get("{%s}ref" % NAMESPACE))
##         for node in tree.findall('DateLastModified'):
##             self.lastMod = node.text
##         for node in tree.findall('ProcessingStatuses/ProcessingStatus'):
##             for child in node:
##                 if child.tag == 'ProcessingStatusValue':
##                     self.status = child.text
##                 elif child.tag == 'ProcessingStatusDate':
##                     self.statusDate = child.text
##                 elif child.tag == 'Comment':
##                     self.comments.append(child.text)
##             break
##     def __cmp__(self, other):
##         if self.lastVersionPublishable == other.lastVersionPublishable:
##             if self.lastMod == other.lastMod:
##                 return cmp(self.title, other.title)
##             return cmp(self.lastMod, other.lastMod)
##         if self.lastVersionPublishable:
##             return -1
##         return 1

#----------------------------------------------------------------------
# Queue up a request for the report.
#----------------------------------------------------------------------
args = (('start', startDate), ('end', endDate), ('language', language))
if not email or '@' not in email:
    cdrcgi.bail("No email address for logged-in user")
try:
    batch = cdrbatch.CdrBatch(jobName=section, email=email, args=args,
                              command='lib/Python/CdrLongReports.py')
except Exception, e:
    cdrcgi.bail("Failure creating batch job: %s" % repr(e))
try:
    batch.queue()
except Exception, e:
    cdrcgi.bail("Unable to start job: %s" % repr(e))
jobId = batch.getJobId()
cdrcgi.sendPage(header + """\
   <h4>Report has been queued for background processing</h4>
   <p>
    To monitor the status of the job, click this
    <a href='http://%s%s/getBatchStatus.py?%s=%s&jobId=%s'><u>link</u></a>
    or use the CDR Administration menu to select 'View
    Batch Job Status'.
   </p>
  </form>
 </body>
</html>
""" % (cdrcgi.WEBSERVER, cdrcgi.BASE, cdrcgi.SESSION, session, jobId))
