#----------------------------------------------------------------------
# Web interface for requesting status from the Cancer.gov GateKeeper
# and testing if our record in pub_proc_cg confirms that the documents
# have been published.
#
# This program has been modified from the original GateKeeperStatus.py
#
# BZIssue::5015 - Documents on Cancer.gov not accounted for
# Rewritten July 2015 as part of security sweep (lots of dead code dropped).
#----------------------------------------------------------------------
import cdr
import cdr2gk
import cdrcgi
import cdrdb
import cgi
import re
import sys

fields  = cgi.FieldStorage()
cdrId   = fields.getvalue('cdrId') # or '525153'
jobId   = fields.getvalue('jobId') # or '8437'
host    = fields.getvalue('targetHost') or cdr2gk.HOST
logging = fields.getvalue('debugLogging') and True or False
action  = fields.getvalue('action') # or 'yes!'
flavor  = fields.getvalue('flavor') # or 'full'

if not re.match(r"^[a-zA-Z0-9._-]+$", host):
    cdrcgi.bail("invalid host name")

cdr2gk.DEBUGLEVEL = 2 if logging else 0

# ----------------------------------------------------------------------
# Set up a database connection and cursor.
# ----------------------------------------------------------------------
try:
    conn = cdrdb.connect("CdrGuest")
    cursor = conn.cursor()
except cdrdb.Error as info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])

#----------------------------------------------------------------------
# Make a value safe for display on a web page.
#----------------------------------------------------------------------
def fix(me, nbsp_for_empty_values=False):
    val = cgi.escape(str(me))
    if not val and nbsp_for_empty_values:
        return "&nbsp;"
    return val

# ----------------------------------------------------------------------
# Display the input form
# ----------------------------------------------------------------------
def showForm(extra = u""):
    title = u"GateKeeper Status Request Form"
    html = u"""\
<html>
 <head>
  <title>%s</title>
  <style type='text/css'>
   body   { font-family: Arial; font-size: 10pt }
   h1     { font-size: 14pt; color: maroon; text-align: center; }
   .fw    { width: 250px }
   h1, p  { width: 650px }
   div.help { width: 650px; border: 1px solid blue; padding: 5px }
   b, th  { color: green }
   a      { color: blue }
   th, td { font-size: 10pt }
   input.fw { padding-left: 4px; }
  </style>
 </head>
 <body>
  <br>
  <h1>%s</h1>
  <br>
  <div class="help">
  <p>
   This interface is provided for submitting status requests to
   Cancer.gov's GateKeeper 2.0 and comparing them to what the
   CDR has recorded in the table pub_proc_cg.
   Currently the three types of status which can be requested
   are:
   </p>
    <il>
     <li><b>Summary</b>, which provides information about a specific
         push publishing job,</li>
     <li><b>Single Document</b>, which provides
         information about the location of an individual CDR document
         in the Cancer.gov system, and</li>
     <li><b>All Documents</b>, which
         provides that information for every document in the Cancer.gov
         system.</li>
    </il>
   <p>
   Enter a <b>Job ID</b> to request a <b>Summary</b> report
   for that job.
   Enter a <b>CDR ID</b> to request a <b>Single Document</b>
   report for that document.
   If both <b>Job ID</b> and <b>CDR ID</b> are omitted, you
   will receive an <b>All Documents</b> report.
   If the <b>Display</b> option is removed only the recorded
   problems are displayed.
   Debug logging can be requested when needed for tracking down
   failures and other unexpected behavior.<br /><br />
   <b>NOTE</b>: The <b>All Documents</b> report is large; if you
   invoke it you should be prepared to wait a while for it to
   complete; if you invoke it with debug logging enabled, you
   will have a <i>large</i> amount of data added to the debug log.
  </p>
  </div>
  <br>
  <form method='post' action='GatekeeperStatus.py'>
   <table border='0' cellpadding='2' cellspacing='0'>
    <tr>
     <th align='right'>GateKeeper Host:&nbsp;</th>
     <td><input class='fw' name='targetHost' value='%s'></td>
    </tr>
    <tr>
     <th align='right'>Job ID:&nbsp;</th>
     <td><input class='fw' name='jobId'></td>
    </tr>
    <tr>
     <th align='right'>CDR ID:&nbsp;</th>
     <td><input class='fw' name='cdrId'></td>
    </tr>
    <tr>
     <th align='right'>Display:&nbsp;</th>
     <td><input class='fw' name='flavor' value='all'></td>
    </tr>
    <tr>
     <td align='center' colspan='2'><br>
      <br />
      <input type='checkbox' name='debugLogging'>
      Enable Debug Logging &nbsp; &nbsp;&nbsp;&nbsp;
      <input type='submit' name='action' value='Submit'></td>
    </tr>
   </table>
  </form>
%s </body>
</html>
""" % (title, title, host, extra)
    cdrcgi.sendPage(html)


# -----------------------------------------------------------------
# Query to check if a given CDR-ID is recorded in pub_proc_cg.
# Except for removed documents this should be true for all records.
# -----------------------------------------------------------------
def checkPubProcCg(cursor, cdrId):
    cursor.execute("""\
        SELECT id
          FROM pub_proc_cg
         WHERE id = ?""", cdrId)
    rows = cursor.fetchall()

    if not rows:
        return False
    return True

# -----------------------------------------------------------------
# Create the HTML format to add to the output table.
# -----------------------------------------------------------------
def addRow(cursor, cdrFlag):
    if doc.pubType == "Remove":
        cdrRecord = cdrFlag and "Error" or "Removed"
    else:
        cdrRecord = cdrFlag and "OK" or "Error"
    return (u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (fix(doc.packetNumber, True), fix(doc.group, True),
       fix(doc.cdrId, True), fix(doc.pubType, True),
       fix(doc.docType, True), fix(doc.status, True),
       fix(doc.dependentStatus, True), fix(doc.location, True),
       cdrRecord))


# -----------------------------------------------------------------
#
# -----------------------------------------------------------------
def makeError(error, exception):
    if logging:
        return (u"<span style='color: red; font-weight: bold'>%s: %s</span>"
                % (fix(error), fix(exception)))
    else:
        return (u"<span style='color: red; font-weight: bold'>%s</span>" %
                fix(error))


if jobId:
    if not jobId.isdigit():
        cdrcgi.bail("Job ID must be an integer")
    try:
        response = cdr2gk.requestStatus('Summary', jobId, host=host)
    except Exception as e:
        showForm(makeError(u"Job %s not found" % jobId, e))

    details = response.details

    html = [u"""\
<html>
 <head>
  <title>Summary Report for Job %s</title>
  <style type='text/css'>
   body { font-family: Arial }
   h1   { font-size: 12pt; color: green }
   th   { color: blue; }
  </style>
 </head>
 <body>
  <h1>Summary Report for Job %s</h1>
  <table border='0'>
   <tr>
    <th align='right'>Job ID:&nbsp;</th>
    <td>%s</td>
   </tr>
   <tr>
    <th align='right'>Request Type:&nbsp;</th>
    <td>%s</td>
   </tr>
   <tr>
    <th align='right'>Description:&nbsp;</th>
    <td>%s</td>
   </tr>
   <tr>
    <th align='right'>Status:&nbsp;</th>
    <td>%s</td>
   </tr>
   <tr>
    <th align='right'>Source:&nbsp;</th>
    <td>%s</td>
   </tr>
   <tr>
    <th align='right'>Initiated:&nbsp;</th>
    <td>%s</td>
   </tr>
   <tr>
    <th align='right'>Completion:&nbsp;</th>
    <td>%s</td>
   </tr>
   <tr>
    <th align='right'>Target:&nbsp;</th>
    <td>%s</td>
   </tr>
   <tr>
    <th align='right'>Expected Count:&nbsp;</th>
    <td>%s</td>
   </tr>
   <tr>
    <th align='right'>Actual Count:&nbsp;</th>
    <td>%s</td>
   </tr>
  </table>
  <br />
  <h1>Documents</h1>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th>Packet #</th>
    <th>Group</th>
    <th>CDR ID</th>
    <th>Pub Type</th>
    <th>Doc Type</th>
    <th>Status</th>
    <th>Dependent Status</th>
    <th>Location</th>
    <th>CDR Record</th>
   </tr>
""" % (fix(jobId), fix(jobId), fix(details.jobId), fix(details.requestType),
       fix(details.description), fix(details.status), fix(details.source),
       fix(details.initiated), fix(details.completion), fix(details.target),
       fix(details.expectedCount), fix(details.actualCount))]

    iDoc = pDoc = 0

    for doc in details.docs:
        iDoc += 1
        isRecorded = checkPubProcCg(cursor, doc.cdrId)

        if flavor == 'full' or flavor == 'all':

            html.append(addRow(cursor, isRecorded))
            if not isRecorded:
                pDoc += 1
        else:
            if not isRecorded:
                pDoc += 1
                html.append(addRow(cursor, isRecorded))

    html.append(u"""\
  </table>
  <p>%d Records checked, %d Records not in pub_proc_cg</p>
 </body>
</html>
""" % (iDoc, pDoc))
    cdrcgi.sendPage(u"".join(html))

# Process the case when *all* documents are being checked or a single
# CDR-ID has been passed.
# -------------------------------------------------------------------
if action:
    if cdrId:
        if not cdrId.isdigit():
            cdrcgi.bail("CDR ID must be an integer")
        try:
            response = cdr2gk.requestStatus('SingleDocument', cdrId, host=host)
        except Exception as e:
            showForm(makeError("Report for CDR%s not found" % cdrId, e))
        title = u"Location Status for Document CDR%s" % cdrId
    else:
        try:
            response = cdr2gk.requestStatus('DocumentLocation', host=host)
        except Exception as e:
            showForm(makeError("Unable to generate report on all documents",
                               e))
        title = u"Location Status for All Documents"

    details = response.details
    docs = details and details.docs or []
    print(u"""\
Content-type: text/html

<html>
 <head>
  <title>%s</title>
  <style type='text/css'>
   body { font-family: Arial }
   h1   { font-size: 12pt; color: green }
   th   { color: blue }
  </style>
 </head>
 <body>
  <h1>%s</h1>
  <table border='1' cellpadding='2' cellspacing='0'>
   <tr>
    <th rowspan='2'>CDR ID</th>
    <th colspan='2'>GateKeeper</th>
    <th colspan='2'>Preview</th>
    <th colspan='2'>Live</th>
    <th rowspan='2'>CDR Record</th>
   </tr>
   <tr>
    <th>Job ID</th>
    <th>Date/Time</th>
    <th>Job ID</th>
    <th>Date/Time</th>
    <th>Job ID</th>
    <th>Date/Time</th>
   </tr>""" % (title, title))
    docs.sort(lambda a,b: cmp(a.cdrId, b.cdrId))

    iDoc = pDoc = 0

    for doc in docs:
        iDoc += 1

        # Documents that used to be on Gatekeeper but have since been
        # removed are listed as 'Not Present' on all stages
        # We can skip these.
        # -----------------------------------------------------------
        if doc.gatekeeperJobId == 'Not Present' and \
           doc.previewJobId == 'Not Present' and \
           doc.liveJobId == 'Not Present' and not cdrId:
            continue

        isRecorded = checkPubProcCg(cursor, doc.cdrId)

        if cdrId or not isRecorded:
            if not isRecorded:
                pDoc += 1
            print(u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>""" % (fix(doc.cdrId),
               fix(doc.gatekeeperJobId),
               fix(doc.gatekeeperDateTime),
               fix(doc.previewJobId),
               fix(doc.previewDateTime),
               fix(doc.liveJobId),
               fix(doc.liveDateTime),
               isRecorded and 'OK' or 'Error'))

    print(u"""\
  </table>
  <p>%d Records checked, %d Records not in pub_proc_cg</p>
 </body>
</html>""" % (iDoc, pDoc))
    sys.exit(0)

showForm()
