#----------------------------------------------------------------------
#
# $Id$
#
# Web interface for requesting status from the Cancer.gov GateKeeper
# and testing if our record in pub_proc_cg confirms that the documents
# have been published.
#
# This program has been modified from the original GateKeeperStatus.py
#
# BZIssue::5015 - Documents on Cancer.gov not accounted for
#
#----------------------------------------------------------------------
import cdr2gk, cgi, xml.sax.saxutils, cdrcgi, cdr, cdrdb, re, sys

fields  = cgi.FieldStorage()
cdrId   = fields.getvalue('cdrId') # or '525153'
jobId   = fields.getvalue('jobId') # or '8437'
host    = fields.getvalue('targetHost') or 'gatekeeper.cancer.gov'
logging = fields.getvalue('debugLogging')
action  = fields.getvalue('action') # or 'yes!'
flavor  = fields.getvalue('flavor') # or 'full'

cdr2gk.host = host
cdr2gk.debuglevel = logging and True or False

# ----------------------------------------------------------------------
# Set up a database connection and cursor.
# ----------------------------------------------------------------------
try:
    conn = cdrdb.connect("CdrGuest")
    cursor = conn.cursor()
except cdrdb.Error, info:
    cdrcgi.bail('Database connection failure: %s' % info[1][0])


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
     <td><input class='fw' name='targetHost' value='gatekeeper.cancer.gov'></td>
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
""" % (title, title, extra)
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
    return(u"""\
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
""" % (doc.packetNumber or "&nbsp;", doc.group or "&nbsp;",
       doc.cdrId or "&nbsp;", doc.pubType or "&nbsp;",
       doc.docType or "&nbsp;", doc.status or "&nbsp;",
       doc.dependentStatus or "&nbsp;", doc.location or "&nbsp;",
       cdrFlag and 'OK' or 'Error'))


# -----------------------------------------------------------------
#
# -----------------------------------------------------------------
def makeError(error, exception):
    if logging:
        return (u"<span style='color: red; font-weight: bold'>%s: %s</span>"
                % (error, exception))
    else:
        return u"<span style='color: red; font-weight: bold'>%s</span>" % error


if jobId:
    try:
        response = cdr2gk.requestStatus('Summary', jobId)
    except Exception, e:
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
""" % (jobId, jobId, details.jobId, details.requestType,
       cgi.escape(details.description), details.status, details.source,
       details.initiated, details.completion, details.target,
       details.expectedCount, details.actualCount)]

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
        try:
            response = cdr2gk.requestStatus('SingleDocument', cdrId)
        except Exception, e:
            showForm(makeError("Report for CDR%s not found" % cdrId, e))
        title = u"Location Status for Document CDR%s" % cdrId
    else:
        try:
            response = cdr2gk.requestStatus('DocumentLocation')
        except Exception, e:
            showForm(makeError("Unable to generate report on all documents",
                               e))
        title = u"Location Status for All Documents"

    details = response.details
    docs = details and details.docs or []
    print u"""\
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
   </tr>""" % (title, title)
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
            print u"""\
   <tr>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>""" % (doc.cdrId,
               doc.gatekeeperJobId,
               doc.gatekeeperDateTime,
               doc.previewJobId,
               doc.previewDateTime,
               doc.liveJobId,
               doc.liveDateTime,
               isRecorded and 'OK' or 'Error')

    print u"""\
  </table>
  <p>%d Records checked, %d Records not in pub_proc_cg</p>
 </body>
</html>""" % (iDoc, pDoc)
    sys.exit(0)



# -----------------------------------------------------------------
#
# -----------------------------------------------------------------
def extractFaultString(exceptionObject):
    exceptionString = unicode(exceptionObject)
    match = FaultString.search(exceptionString)
    return match and match.group(1) or exceptionString
        
# -----------------------------------------------------------------
#
# -----------------------------------------------------------------
def getDocList(cursor, jobId, cdrIds):
    if jobId and cdrIds:
        raise Exception(u"Enter Job ID *OR* CDR ID List (not both)")
    if cdrIds:
        return cdrIds.split()
    cursor.execute("""\
        SELECT doc_id
          FROM pub_proc_doc
         WHERE pub_proc = ?""", jobId)
    rows = cursor.fetchall()
    if not rows:
        raise Exception(u"No documents found for job %s" % jobId)
    return [str(row[0]) for row in rows]
    
# -----------------------------------------------------------------
#
# -----------------------------------------------------------------
def makeCdrServerPicklist(current):
    html = [u"<select class='fw' name='cdrServer'>"]
    for name in ('Production', 'Test', 'Development'):
        sel = (name == current) and ' selected' or ''
        html.append(u"<option value='%s'%s>%s</option>" % (name, sel, name))
    html.append(u"</select>")
    return u''.join(html)

# -----------------------------------------------------------------
#
# -----------------------------------------------------------------
def makeCdrSourcePicklist(current):
    html = [u"<select class='fw' name='cdrSource'>"]
    for v in ('CDR Development', 'CDR Testing'):
        sel = (v == current) and ' selected' or ''
        html.append(u"<option value='%s'%s>%s</option>" % (v, sel, v))
    html.append(u"</select>")
    return u"".join(html)

# -----------------------------------------------------------------
#
# -----------------------------------------------------------------
def quoteAttr(what):
    return xml.sax.saxutils.quoteattr(what)

# -----------------------------------------------------------------
#
# -----------------------------------------------------------------
def addFaultResults(results, fault):
    if fault:
        results.append(Result(u"Fault Code", fault.faultcode))
        results.append(Result(u"Fault String", fault.faultstring))

# -----------------------------------------------------------------
#
# -----------------------------------------------------------------
class Doc:
    def __init__(self, cursor, docId):
        self.id = cdr.exNormalize(docId)[1]
        cursor.execute("""\
            SELECT p.xml, d.doc_version, t.name
              FROM pub_proc_cg p
              JOIN pub_proc_doc d
                ON d.pub_proc = p.pub_proc
               AND d.doc_id = p.id
              JOIN doc_version v
                ON v.id = p.id
               AND v.num = d.doc_version
              JOIN doc_type t
                ON t.id = v.doc_type
             WHERE p.id = ?""", self.id)
        rows = cursor.fetchall()
        if not rows:
            raise Exception(u"Document %s is not currently on Cancer.gov" %
                            docId)
        docXml, self.version, self.type = rows[0]
        if self.type == u'InScopeProtocol':
            self.type = u'Protocol'
        self.xml = DocTypeLine.sub(u"", XmlDeclLine.sub(u"", docXml))
        
# -----------------------------------------------------------------
#
# -----------------------------------------------------------------
class Server:
    def __init__(self, dnsName, source):
        self.dnsName = dnsName
        self.source  = source

# -----------------------------------------------------------------
#
# -----------------------------------------------------------------
class Result:
    def __init__(self, label, value):
        self.label = label
        self.value = value
    def joinResults(results, jobId):
        if not results:
            return u""
        if jobId:
            title = u"Request Results for Push %s" % jobId
        else:
            title = u"Request Results"
        html = [u"""\
  <br>
  <h1>%s</h1>
  <br>
  <table border='1' cellpadding='2' cellspacing='0'>
""" % title]
        for result in results:
            html.append(u"""\
   <tr>
    <td><b>%s</b></td>
    <td>%s</td>
   </tr>
""" % (cgi.escape(unicode(result.label)),
       cgi.escape(unicode(result.value))))
        html.append(u"""\
  </table>
""")
        return u"".join(html)
    joinResults = staticmethod(joinResults)

showForm()
