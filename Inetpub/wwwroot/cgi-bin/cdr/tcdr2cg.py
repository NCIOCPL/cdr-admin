#----------------------------------------------------------------------
#
# $Id$
#
# Web interface for requesting retransmission of CDR documents to the
# Cancer.gov GateKeeper.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2006/06/14 13:03:46  bkline
# Script for re-submitting documents to Cancer.gov's GateKeeper.
#
#----------------------------------------------------------------------
import cdr2cg, cgi, xml.sax.saxutils, cdrcgi, cdr, cdrdb, re

cdr2cg.debuglevel = 1

fields      = cgi.FieldStorage()
cdrSource   = fields and fields.getvalue('cdrSource')   or ''
cdrServer   = fields and fields.getvalue('cdrServer')   or ''
jobId       = fields and fields.getvalue('jobId')       or ''
cdrIds      = fields and fields.getvalue('cdrIds')      or ''
targetHost  = fields and fields.getvalue('targetHost')  or ''
desc        = fields and fields.getvalue('description') or ''
results     = []
newJobId    = None
XmlDeclLine = re.compile(u"<\\?xml.*?\\?>\\s*", re.DOTALL)
DocTypeLine = re.compile(u"<!DOCTYPE.*?>\\s*", re.DOTALL)
FaultString = re.compile(u"<faultstring>(.*)</faultstring>", re.DOTALL)

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

if cdrServer and cdrSource and (jobId or cdrIds) and targetHost and desc:
    dbServer = {
        'Development': 'mahler.nci.nih.gov',
        'Test'       : 'franck.nci.nih.gov',
        'Production' : 'bach.nci.nih.gov'
    }[cdrServer]
    conn = cdrdb.connect('CdrGuest', dbServer)
    cursor = conn.cursor()
    ok = True
    try:
        docIds = getDocList(cursor, jobId, cdrIds)
    except Exception, e:
        ok = False
        results.append(Result(u"Invalid Parameter", unicode(e)))

    # See if the GateKeeper is awake.
    if ok:
        #cdrcgi.bail(docIds)
        cdr2cg.source = cdrSource
        cdr2cg.host   = targetHost
        response = cdr2cg.initiateRequest(desc, "Export", "ignore")
        results.append(Result(u"Initial Handshake", response))
        if response.type != "OK":
            ok = False
        else:
            newJobId = response.details.nextJobId

    # Prepare the server for a batch of documents.
    if ok:
        response = cdr2cg.sendDataProlog(desc, newJobId, "Export",
                                         "ignore", "ignore") #len(docIds))
        results.append(Result(u"Data Prolog", response))
        if response.type != "OK":
            ok = False

    if ok:
        for i in range(len(docIds)):
            docId = docIds[i]
            try:
                doc = Doc(cursor, docId)
            except Exception, e:
                results.append(Result(u"Document %s" % docId, unicode(e)))
                continue
            try:
                response = cdr2cg.sendDocument(newJobId, i + 1, "Export",
                                               doc.type, doc.id, doc.version,
                                               doc.xml.encode('utf-8'))
                results.append(Result(u"Document %s" % docId, response))
            except Exception, e:
                results.append(Result(u"Document %s" % docId,
                                      extractFaultString(e)))
        response = cdr2cg.sendJobComplete(newJobId, "Export")
        results.append(Result(u"Job Complete", response))

targetHost = targetHost or 'test4.cancer.gov'
cdrServer  = cdrServer or 'Production'
title = u"CDR Document GateKeeper Re-Submission Request Form"
html = u"""\
<html>
 <head>
  <title>%s</title>
  <style type='text/css'>
   body   { font-family: Arial; font-size: 10pt }
   h1     { font-size: 14pt; color: maroon; text-align: center; }
   .fw    { width: 350px }
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
   This interface is provided for re-sending one or more CDR documents
   to a Cancer.gov GateKeeper server.
   The <b>CDR Server</b>, <b>GateKeeper Host</b>, <b>Source</b>,
   and <b>Description</b>
   fields are required.  You must also provide a <b>Job ID</b> or
   one or more <b>CDR ID</b> values.  The current implementation is
   only capable of handling a limited number of documents at a
   time (constrained by the amount of processing which can be done
   before the web server times out the request).
   You can view a list of the most recent push jobs from any of the
   CDR Servers <a href='ListPushJobs.py'>here</a>.
  </p>
  <br>
  <form method='post' action='tcdr2cg.py'>
   <table border='0' cellpadding='2' cellspacing='0'>
    <tr>
     <th align='right'>CDR Server:&nbsp;</th>
     <td>%s</td>
    </tr>
    <tr>
     <th align='right'>GateKeeper Host:&nbsp;</th>
     <td><input class='fw' name='targetHost' value=%s></td>
    </tr>
    <tr>
     <th align='right'>Source:&nbsp;</th>
     <td>%s</td>
    </tr>
    <tr>
     <th align='right'>Description:&nbsp;</th>
     <td><input class='fw' name='description' value=%s></td>
    </tr>
    <tr>
     <th align='right'>Job ID:&nbsp;</th>
     <td><input class='fw' name='jobId' value=%s> <u>or</u></td>
    </tr>
    <tr>
     <th align='right'>CDR IDs:&nbsp;</th>
     <td><input class='fw' name='cdrIds' value=%s> (separate with spaces)</td>
    </tr>
    <tr>
     <td align='center' colspan='2'><br><input type='submit'
                                               value='Submit'></td>
    </tr>
   </table>
  </form>
%s </body>
</html>
""" % (title, title, makeCdrServerPicklist(cdrServer), quoteAttr(targetHost),
       makeCdrSourcePicklist(cdrSource), quoteAttr(desc), jobId,
       quoteAttr(cdrIds), Result.joinResults(results, newJobId))
cdrcgi.sendPage(html)
