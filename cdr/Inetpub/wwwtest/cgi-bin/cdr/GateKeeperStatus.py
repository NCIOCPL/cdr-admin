#----------------------------------------------------------------------
#
# $Id: GateKeeperStatus.py,v 1.3 2009-02-10 19:32:28 bkline Exp $
#
# Web interface for requesting status from the new Cancer.gov GateKeeper.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2007/08/09 15:58:41  venglisc
# Added new variable to allow displaying only the records with errors or
# warnings or both.
#
# Revision 1.1  2007/05/24 20:08:09  bkline
# User interface for status report SOAP methods at Cancer.gov's GateKeeper.
#
#----------------------------------------------------------------------
import cdr2gk, cgi, xml.sax.saxutils, cdrcgi, cdr, cdrdb, re, sys

fields  = cgi.FieldStorage()
cdrId   = fields.getvalue('cdrId') # or '525153'
jobId   = fields.getvalue('jobId') # or '102056'
host    = fields.getvalue('targetHost') or 'gkdev.cancer.gov'
logging = fields.getvalue('debugLogging')
action  = fields.getvalue('action') # or 'yes!'
flavor  = fields.getvalue('flavor') or 'full'

cdr2gk.host = host
cdr2gk.debuglevel = logging and True or False

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
   p      { border: 1px solid blue; padding: 5px }
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
  <p>
   This interface is provided for submitting status requests to
   Cancer.gov's GateKeeper 2.0.
   Currently the three types of status which can be requested
   are <b>Summary</b>, which provides information about a specific
   push publishing job, <b>Single Document</b>, which provides
   information about the location of an individual CDR document
   in the Cancer.gov system, and <b>All Documents</b>, which
   provides that information for every document in the Cancer.gov
   system.
   Enter a <b>Job ID</b> to request a <b>Summary</b> report
   for that job.
   Enter a <b>CDR ID</b> to request a <b>Single Document</b>
   report for that document.
   If both <b>Job ID</b> and <b>CDR ID</b> are omitted, you
   will receive an <b>All Documents</b> report.
   Debug logging can be requested when needed for tracking down
   failures and other unexpected behavior.<br /><br />
   <b>NOTE</b>: The <b>All Documents</b> report is large; if you
   invoke it you should be prepared to wait a while for it to
   complete; if you invoke it with debug logging enabled, you
   will have a <i>large</i> amount of data added to the debug log.
  </p>
  <br>
  <form method='post' action='GateKeeperStatus.py'>
   <table border='0' cellpadding='2' cellspacing='0'>
    <tr>
     <th align='right'>GateKeeper Host:&nbsp;</th>
     <td><input class='fw' name='targetHost' value='gkdev.cancer.gov'></td>
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

def addRow(doc):
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
   </tr>
""" % (doc.packetNumber or "&nbsp;", doc.group or "&nbsp;",
       doc.cdrId or "&nbsp;", doc.pubType or "&nbsp;",
       doc.docType or "&nbsp;", doc.status or "&nbsp;",
       doc.dependentStatus or "&nbsp;", doc.location or "&nbsp;"))


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
   </tr>
""" % (jobId, jobId, details.jobId, details.requestType,
       cgi.escape(details.description), details.status, details.source,
       details.initiated, details.completion, details.target,
       details.expectedCount, details.actualCount)]
    for doc in details.docs:
        if flavor == 'full':
            html.append(addRow(doc))
        elif flavor == 'error':
            if doc.status == 'Error' or doc.dependentStatus == 'Error':
                html.append(addRow(doc))
        elif flavor == 'warning':
            if doc.status == 'Warning' or doc.dependentStatus == 'Warning':
                html.append(addRow(doc))
        elif flavor == 'all':
            if (doc.status == 'Warning' or doc.dependentStatus == 'Warning'
                or doc.status == 'Error' or doc.dependentStatus == 'Error'):
                html.append(addRow(doc))
        else:
            cdrcgi.bail('Invalid flavor: %s <br/>' % flavor +
                        'Valid values: full, error, warning, all')
        
    html.append(u"""\
  </table>
 </body>
</html>
""")
    cdrcgi.sendPage(u"".join(html))

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
    for doc in docs:
        print u"""\
   <tr>
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
               doc.liveDateTime)
    print u"""\
  </table>
 </body>
</html>"""
    sys.exit(0)



def extractFaultString(exceptionObject):
    exceptionString = unicode(exceptionObject)
    match = FaultString.search(exceptionString)
    return match and match.group(1) or exceptionString
        
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
    
def makeCdrServerPicklist(current):
    html = [u"<select class='fw' name='cdrServer'>"]
    for name in ('Production', 'Test', 'Development'):
        sel = (name == current) and ' selected' or ''
        html.append(u"<option value='%s'%s>%s</option>" % (name, sel, name))
    html.append(u"</select>")
    return u''.join(html)

def makeCdrSourcePicklist(current):
    html = [u"<select class='fw' name='cdrSource'>"]
    for v in ('CDR Development', 'CDR Testing'):
        sel = (v == current) and ' selected' or ''
        html.append(u"<option value='%s'%s>%s</option>" % (v, sel, v))
    html.append(u"</select>")
    return u"".join(html)

def quoteAttr(what):
    return xml.sax.saxutils.quoteattr(what)

def addFaultResults(results, fault):
    if fault:
        results.append(Result(u"Fault Code", fault.faultcode))
        results.append(Result(u"Fault String", fault.faultstring))

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
        
class Server:
    def __init__(self, dnsName, source):
        self.dnsName = dnsName
        self.source  = source

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
