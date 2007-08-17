#----------------------------------------------------------------------
#
# $Id: CtsSubmittedTrials.py,v 1.1 2007-08-17 18:17:45 bkline Exp $
#
# CDR-side interface for reviewing CTS trials.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdrcgi, urllib, xml.dom.minidom, cdr, re

# XXX !!! When this goes into production, the following test needs to be
#         changed from "not cdr.isDevHost()" to "cdr.isProdHost()" so that
#         tests from Franck no longer connect to the production CTS
#         server.  The most straightforward way to do this is:
CTS_HOST = cdr.emailerHost()
#CTS_HOST = not cdr.isDevHost() and cdr.EMAILER_PROD or cdr.EMAILER_DEV
# XXX Switch made.

def makeFailureMessage(what):
    return makeExtra(cgi.escape(what), "fail")

def makeSuccessMessage(what):
    return makeExtra(what, "ok")

def makeExtra(what, outcome):
    return u"""\
  <h2 class='%s'>%s</h2>
""" % (outcome, what)

class SupplementaryInfoDoc:
    def __init__(self, docType, docId, docName):
        #print "SupplementaryInfoDoc(%s, %s, %s)" % (docType, docId, docName)
        mimeKey       = docName[-5:].lower()
        if mimeKey   != ".html":
            mimeKey   = mimeKey[1:]
        #print mimeKey
        self.filename = docName
        self.title    = u"%s document for CTS trial" % docType
        self.blob     = SupplementaryInfoDoc.__getBlob(docId, docType)
        self.desc     = u"supplementary document added in CTS system"
        self.category = u'Supporting documents'
        self.mimeType = {
            ".doc":  u"application/msword",
            ".txt":  u"text/plain",
            ".htm":  u"text/html",
            ".zip":  u"application/zip",
            ".pdf":  u"application/pdf",
            ".xls":  u"application/vnd.ms-excel",
            ".wpd":  u"application/vnd.wordperfect",
            ".ppd":  u"application/vnd.ms-powerpoint",
            ".html": u"text/html"
            }.get(mimeKey, "")
        #print self.mimeType
        if docType == 'sites':
            self.category = u"Participant site list"
        elif docType == 'protocol':
            self.category = u"Protocol source document"
    @staticmethod
    def __getBlob(docId, docType):
        docId = (docType == 'sites' and 's' or 'd') + docId
        #print docId
        url = 'http://%s/u/cts-get-doc.py?id=%s' % (CTS_HOST, docId)
        f = urllib.urlopen(url)
        return f.read()
        
def addSupplementaryInfoDoc(match):
    docType, docId, docName = match.group(1).split('|')
    #print docType, docId, docName
    suppDoc = SupplementaryInfoDoc(docType, docId, docName)
    #print suppDoc.mimeType, suppDoc.blob
    cdrDoc = cdr.Doc((u"""\
<SupplementaryInfo xmlns:cdr="cips.nci.nih.gov/cdr">
 <Title>%s</Title>
 <MimeType>%s</MimeType>
 <Category>%s</Category>
 <Description>%s</Description>
 <Source>web submission</Source>
 <OriginalFilename>%s</OriginalFilename>
</SupplementaryInfo>
""" % (suppDoc.title, suppDoc.mimeType, suppDoc.category,
       suppDoc.desc, suppDoc.filename)).encode('utf-8'), "SupplementaryInfo",
                     blob = suppDoc.blob,
                     ctrl = { "DocType": "SupplementaryInfo" },
                     encoding = 'utf-8')
    cdrDoc = str(cdrDoc)
    #fp = file('d:/tmp/cts-supp-info-%s-%s.xml' % (docType, docId), 'wb')
    #fp.write(cdrDoc)
    #fp.close()
    resp = cdr.addDoc(session, doc = cdrDoc, val = 'N', showWarnings = 1)
    if not resp[0]:
        raise Exception(cdr.checkErr(resp[1]))
    doc = cdr.getDoc(session, resp[0], 'Y')
    if doc.startswith("<Errors"):
        raise Exception(u"Unable to retrieve SuppInfo doc %s" % resp[0])
    cdr.repDoc(session, doc = doc, val = 'N', ver = 'Y', checkIn = 'Y')
    docId = cdr.exNormalize(resp[0])[1]
    return "cdr:ref='CDR%010d'" % docId

def markDuplicate(publicId, primaryId, session):
    f = urllib.urlopen('http://%s/u/cts-mark-trial-duplicate.py?id=%s' %
                       (CTS_HOST, publicId))
    doc = f.read()
    if "TRIAL MARKED AS DUPLICATE" not in doc:
        return makeFailureMessage(u"%s: %s" % (primaryId, doc))
    return makeSuccessMessage(u"%s successfully marked as duplicate" %
                              primaryId)
    
def importDoc(publicId, primaryId, session):
    if not session:
        return makeFailureMessage(u"You aren't logged in")
    pattern = re.compile("@@SUPPINFO@@(.+?)@@SUPPINFO@@")
    f = urllib.urlopen('http://%s/u/cts-create-cdr-doc.py?id=%s' %
                       (CTS_HOST, publicId))
    doc = f.read()
    match = re.search("<FAULT[^>]*>(.*)</FAULT>", doc, re.DOTALL)
    if match:
        return makeFailureMessage(u"Failure adding document: %s" %
                                  match.group(1))
    try:
        doc = pattern.sub(addSupplementaryInfoDoc, doc)
    except Exception, e:
        return makeFailureMessage(u"Failure adding document: %s" % e)
    doc = (u"""\
<CdrDoc Type='InScopeProtocol' Id=''>
 <CdrDocCtl>
  <DocType>InScopeProtocol</DocType>
 </CdrDocCtl>
 <CdrDocXml><![CDATA[%s]]></CdrDocXml>
</CdrDoc>
""" % unicode(doc, 'utf-8')).encode('utf-8')
    #fp = open('d:/tmp/cts-doc-%s.xml' % publicId, 'wb')
    #fp.write(doc)
    #fp.close()
    resp = cdr.addDoc(session, doc = doc, val = 'N', showWarnings = 1)
    if not resp[0]:
        return makeFailureMessage(u"Failure adding protocol document: %s" %
                                  cdr.checkErr(resp[1]))
    
    filterSet = 'QC+InScopeProtocol+Admin+Set'
    url = 'Filter.py?DocId=%s&Filter=set:%s' % (resp[0], filterSet)
    link = "<a href='%s' target='_new'>%s</a>" % (url, resp[0])
#http://mahler.nci.nih.gov/cgi-bin/cdr/Filter.py?DocId=CDR0000467066&Filter=set:QC%20InScopeProtocol%20Admin%20Set&Session=454C1C5A-81318D-002-RMOWQTCA60D5
    extra = u"Protocol %s imported as %s" % (primaryId, link)
    doc = cdr.getDoc(session, resp[0], 'Y')
    if doc.startswith("<Errors"):
        return makeFailureMessage(u"Unable to retrieve %s" % resp[0])
    cdr.repDoc(session, doc = doc, val = 'N', ver = 'Y', checkIn = 'Y')
    f = urllib.urlopen('http://%s/u/cts-mark-trial-imported.py?id=%s' %
                       (CTS_HOST, publicId))
    doc = f.read()
    if "TRIAL MARKED AS IMPORTED" not in doc:
        return makeFailureMessage(u"Protocol %s added as %s but unable to "
                                  u"record import on CTS server: %s" %
                                  (primaryId, resp[0], doc))
    return makeSuccessMessage(extra)

class Trial:
    class Pup:
        def __init__(self, forename, surname, email):
            self.forename = forename or u""
            self.surname  = surname  or u""
            self.email    = email    or u""
    def __init__(self, node):
        try:
            self.primaryKey = int(node.getAttribute('id'))
        except:
            print node.getAttribute('id')
            import sys
            sys.exit(1)
        self.publicId   = None
        self.created    = None
        self.submitted  = None
        self.title      = None
        self.primaryId  = None
        self.pup        = None
        forename, surname, email = None, None, None
        for child in node.childNodes:
            if child.nodeName == "PublicId":
                self.publicId = cdr.getTextContent(child).strip()
            elif child.nodeName == 'Created':
                self.created = cdr.getTextContent(child).strip()
            elif child.nodeName == 'Submitted':
                self.submitted = cdr.getTextContent(child).strip()
            elif child.nodeName == 'Title':
                self.title = cdr.getTextContent(child).strip()
            elif child.nodeName == 'PrimaryId':
                self.primaryId = cdr.getTextContent(child).strip()
            elif child.nodeName == 'Creator':
                self.creator = cdr.getTextContent(child).strip()
            elif child.nodeName == 'PupForename':
                forename = cdr.getTextContent(child).strip()
            elif child.nodeName == 'PupSurname':
                surname = cdr.getTextContent(child).strip()
            elif child.nodeName == 'PupEmail':
                email = cdr.getTextContent(child).strip()
            if forename or surname or email:
                self.pup = Trial.Pup(forename, surname, email)
    def makeJs(self):
        return (u'CdrTooltip.content[\'t-%d\'] = '
                u'\'<table border="0" width="100%%" '
                u'cellspacing="0" cellpadding="2" bgcolor="#3259B4">'
                u'<tr><td bgcolor="#3259B4">'
                u'<font face="Verdana" style="font-size:7pt" color="white">'
                u'<b>Protocol %s</b></font></td></tr>'
                u'<tr><td bgcolor="white">'
                u'<font face="Verdana" style="font-size:7pt" color="#003E9B">'
                u'%s</font></td></tr></table>\';' %
                (self.primaryKey, cgi.escape(self.primaryId),
                 cgi.escape(self.title).replace("'", "\\'")))
    def toHtml(self, styleClass):
        protocolId = self.primaryId or u"[No Protocol ID]"
        protocolId = cgi.escape(protocolId)
        protocolTitle = self.title or u"[No Protocol Title]"
        if len(protocolTitle) > 60:
            protocolTitle = protocolTitle[:60] + u"..."
        created = self.created[:10]
        submitted = self.submitted[:10]
        if self.pup:
            name = u" ".join([self.pup.forename, self.pup.surname]).strip()
            name = cgi.escape(name)
            if self.pup.email:
                email = u"<a href='mailto:%s'>%s</a>" % (self.pup.email,
                                                         self.pup.email)
                name += " (%s)" % email
        else:
            name = u"[Anonymous]"
        url = (u"<a href='ShowCtsTrial.py?id=%s'"
               u" target='_new'>%s</a>" % (self.publicId, protocolId))
        params = '"%s", "%s"' % (self.publicId, protocolId.replace('"', '\\"'))
        importCommand = (u"<a href='javascript:importTrial(%s)'>Import</a>" %
                         params)
        markDuplicate = (u"<a href='javascript:markDup(%s)'>"
                         u"Mark as Duplicate</a>" % params)
        sendLetter    = u"<a href='javascript:sendLetter()'>Send Letter</a>"
        return u"""\
   <tr style='background-color: %s'>
    <td valign='top' style='width: 120'
        onmouseover='CdrTooltip.doTooltip(event, "t-%d");'
        onmouseout='CdrTooltip.hideTip();'>%s</td>
<!--    <td valign='top' style='width: 425'>%s</td> -->
    <td valign='top' align='center' style='width: 100'>%s</td>
    <td valign='top' align='center' style='width: 100'>%s</td>
    <td valign='top'>%s</td> <!-- width 300 -->
    <td valign='top' align='center' style='width: 75'>%s</td>
    <td valign='top' align='center' style='width: 125'>%s</td>
<!--    <td valign='top' align='center' style='width: 75'>%s</td> -->
   </tr>
""" % (styleClass, self.primaryKey, url,
       cgi.escape(protocolTitle), created, submitted, name,
       importCommand, markDuplicate, sendLetter)

fields      = cgi.FieldStorage()
session     = cdrcgi.getSession(fields) or "guest"
importDocId = fields.getvalue('importDoc') or None
duplicate   = fields.getvalue('duplicate') or None
primaryId   = fields.getvalue('primaryId') or None
extra       = u""
if importDocId:
    extra = importDoc(importDocId, primaryId, session)
elif duplicate:
    extra = markDuplicate(duplicate, primaryId, session)

url = 'http://%s/u/cts-submitted-trials.py' % CTS_HOST
#cdrcgi.bail(url)
f = urllib.urlopen(url)
#d = unicode(f.read(), 'utf-8')
#cdrcgi.sendPage(d, 'xml')
dom = xml.dom.minidom.parse(f)


classes = ('#f8f9ff', '#eeefff') #('Snow', 'SeaShell')
counter = 0
trials = []
js = []
for node in dom.documentElement.childNodes:
    if node.nodeName == 'Trial':
        trial = Trial(node)
        trials.append(trial)
        js.append(trial.makeJs())
html = [u"""\
<html>
 <head>
  <title>Submitted Trials</title>
  <style>
   body { font-family: Arial, sans-serif; font-size: 9pt; }
   h1 { font-size: 18pt; }
   h2 { font-size: 12pt; }
   .fail { color: red; }
   .ok { color: green; }
   th { background-color: navy; color: white; font-size: 10pt; }
   td { font-size: 10pt; }
   a { color: navy; text-decoration: none }
   a:hover {color: #a90101}
  </style>
  <script type='text/javascript' src='/js/CdrTooltip.js'></script>
  <script language='javascript'>
   <!--
%s
    function importTrial(whichTrial, primaryId) {
        if (window.confirm("Import " + primaryId + "?")) {
            var form = document.forms[0];
            form.importDoc.value = whichTrial;
            form.primaryId.value = primaryId;
            form.duplicate.value = '';
            form.submit();
        }
    }
    function markDup(whichTrial, primaryId) {
        if (window.confirm("Mark " + primaryId + " as Duplicate?")) {
            var form = document.forms[0];
            form.duplicate.value = whichTrial;
            form.primaryId.value = primaryId;
            form.importDoc.value = '';
            form.submit();
        }
    }
    function sendLetter() { window.alert('Not yet implemented'); }
   -->
  </script>
 </head>
 <body class='qc'>
  <form method='post'>
   <input type='hidden' name='importDoc' value='' />
   <input type='hidden' name='primaryId' value='' />
   <input type='hidden' name='duplicate' value='' />
   <input type='hidden' name='Session' value='%s' />
  </form>
  <h1 style='color: maroon'>Submitted Trials</h1>%s
  <table>
   <tr>
    <th>Protocol ID</th>
<!--    <th>Protocol Title</th> -->
    <th>Created</th>
    <th>Submitted</th>
    <th>Submitter</th>
    <th colspan='2'>Actions</th>
   </tr>
""" % (u"\n".join(js), session or '', extra)]
for trial in trials:
    html.append(trial.toHtml(classes[counter % 2]))
    counter += 1
html.append(u"""\
  </table>
  <div id='tipDiv'
       style='position:absolute;visibility:hidden;z-index:100'></div>
 </body>
</html>
""")
cdrcgi.sendPage(u"".join(html))
