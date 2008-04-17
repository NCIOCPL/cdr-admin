#----------------------------------------------------------------------
#
# $Id: CtsSubmittedTrials.py,v 1.5 2008-04-17 18:41:59 bkline Exp $
#
# CDR-side interface for reviewing CTS trials.
#
# $Log: not supported by cvs2svn $
# Revision 1.4  2008/03/05 19:26:03  bkline
# Workaround for protocol titles in which the submitter has embedded
# newlines for some reason.
#
# Revision 1.3  2007/12/27 20:26:40  bkline
# Disabled link to QC page for CTS trials.
#
# Revision 1.2  2007/10/31 17:46:55  bkline
# Modifications to support Oncore trials.
#
# Revision 1.1  2007/08/17 18:17:45  bkline
# Original production version for reviewing/importing CTS trials.
#
#----------------------------------------------------------------------
import cgi, cdrcgi, urllib, xml.dom.minidom, cdr, re, sys, cdrdb

CTS_HOST = cdr.emailerHost()

def sendPage(page, textType = 'html'):
    output = u"""\
Content-type: text/%s; charset=utf-8

%s""" % (textType, page)
    print output.encode('utf-8')
    sys.exit(0)

def makeFailureMessage(what):
    return makeExtra(cgi.escape(what), "fail")

def makeSuccessMessage(what):
    return makeExtra(what, "ok")

def makeExtra(what, outcome):
    return u"""\
  <h2 class='%s'>%s</h2>
""" % (outcome, what)

class SupplementaryInfoDoc:
    def __init__(self, docType, docId, docName, mimeType = None):
        global source
        #source        = docType.lower() == 'oncore' and 'Oncore' or 'CTS'
        mimeKey       = docName[-5:].lower()
        if mimeKey   != ".html":
            mimeKey   = mimeKey[1:]
        self.filename = docName
        self.title    = u"%s document for %s trial" % (docType, source)
        self.blob     = SupplementaryInfoDoc.__getBlob(docId, docType, source)
        self.desc     = u"supplementary document added in %s system" % source
        self.category = u'Supporting documents'
        self.mimeType = mimeType or {
            ".doc":  u"application/msword",
            ".txt":  u"text/plain",
            ".rtf":  u"text/rtf",
            ".htm":  u"text/html",
            ".zip":  u"application/zip",
            ".pdf":  u"application/pdf",
            ".xls":  u"application/vnd.ms-excel",
            ".wpd":  u"application/vnd.wordperfect",
            ".ppd":  u"application/vnd.ms-powerpoint",
            ".html": u"text/html"
            }.get(mimeKey, "")
        if docType == 'sites':
            self.category = u"Participant site list"
        elif docType == 'protocol':
            self.category = u"Protocol source document"
    @staticmethod
    def __getBlob(docId, docType, source):
        if source.lower() == 'oncore':
            docId = "o%s" % docId
        elif docType == 'sites':
            docId = "s%s" % docId
        else:
            docId = "d%s" % docId
        url = 'http://%s/u/cts-get-doc.py?id=%s' % (CTS_HOST, docId)
        f = urllib.urlopen(url)
        return f.read()
        
def addSupplementaryInfoDoc(match):
    pieces = unicode(match.group(1), 'utf-8').split('|')
    if len(pieces) == 3:
        docType, docId, docName = pieces
        mimeType = None
    elif len(pieces) == 4:
        docType, docId, docName, mimeType = pieces
    suppDoc = SupplementaryInfoDoc(docType, docId, docName, mimeType)
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
    resp = cdr.addDoc(session, doc = cdrDoc, val = 'N', showWarnings = 1)
    if not resp[0]:
        raise Exception(cdr.checkErr(resp[1]))
    doc = cdr.getDoc(session, resp[0], 'Y')
    if doc.startswith("<Errors"):
        raise Exception(u"Unable to retrieve SuppInfo doc %s" % resp[0])
    cdr.repDoc(session, doc = doc, val = 'N', ver = 'Y', checkIn = 'Y')
    docId = cdr.exNormalize(resp[0])[1]
    return "cdr:ref='CDR%010d'" % docId

def markDuplicate(publicId, primaryId, session, source, duplicateOf = ""):
    if source == 'Oncore':
        try:
            dupId = re.sub("[^\\d]+", "", duplicateOf)
        except:
            return makeFailureMessage(u"%s: %s is not a protocol document" %
                                      (primaryId, duplicateOf))
        cursor = cdrdb.connect('CdrGuest').cursor()
        cursor.execute("""\
            SELECT t.name
              FROM doc_type t
              JOIN document d
                ON t.id = d.doc_type
             WHERE d.id = ?""", dupId)
        rows = cursor.fetchall()
        if not rows or rows[0][0] not in ('InScopeProtocol',
                                          'OutOfScopeProtocol',
                                          'CTGovProtocol'):
            return makeFailureMessage(u"%s: %s is not a protocol document" %
                                      (primaryId, duplicateOf))
    f = urllib.urlopen('http://%s/u/cts-mark-trial-duplicate.py?id=%s'
                       '&source=%s&duplicateOf=%s' % (CTS_HOST, publicId,
                                                      source, dupId))
    doc = f.read()
    if "TRIAL MARKED AS DUPLICATE" not in doc:
        return makeFailureMessage(u"%s: %s" % (primaryId, doc))
    return makeSuccessMessage(u"%s successfully marked as duplicate" %
                              primaryId)
    
def importDoc(publicId, primaryId, session, source):
    if not session:
        return makeFailureMessage(u"You aren't logged in")
    pattern = re.compile("@@SUPPINFO@@(.+?)@@SUPPINFO@@")
    f = urllib.urlopen('http://%s/u/cts-create-cdr-doc.py?id=%s&source=%s' %
                       (CTS_HOST, publicId, source))
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
    extra = u"Protocol %s imported as %s" % (primaryId,
                                             source == 'CTS' and link
                                             or resp[0])
    doc = cdr.getDoc(session, resp[0], 'Y')
    if doc.startswith("<Errors"):
        return makeFailureMessage(u"Unable to retrieve %s" % resp[0])
    cdr.repDoc(session, doc = doc, val = 'N', ver = 'Y', checkIn = 'Y')
    cdrId = cdr.exNormalize(resp[0])[1]
    f = urllib.urlopen('http://%s/u/cts-mark-trial-imported.py'
                       '?id=%s&source=%s&cdr-id=%d' % (CTS_HOST, publicId,
                                                       source, cdrId))
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
                 cgi.escape(self.title).replace("'", "\\'")
                                       .replace("\r", "")
                                       .replace("\n", " ")))
    def toHtml(self, styleClass):
        protocolId = self.primaryId or u"[No Protocol ID]"
        protocolId = cgi.escape(protocolId)
        protocolTitle = self.title or u"[No Protocol Title]"
        if len(protocolTitle) > 60:
            protocolTitle = protocolTitle[:60] + u"..."
        created = self.created[:10]
        submitted = self.submitted[:10]
        if source == 'Oncore':
            name = 'Oncore'
        elif self.pup:
            name = u" ".join([self.pup.forename, self.pup.surname]).strip()
            name = cgi.escape(name)
            if self.pup.email:
                email = u"<a href='mailto:%s'>%s</a>" % (self.pup.email,
                                                         self.pup.email)
                name += " (%s)" % email
        else:
            name = u"[Anonymous]"
        url = (u"<a href='ShowCtsTrial.py?id=%s&source=%s'"
               u" target='_new'>%s</a>" % (self.publicId, source, protocolId))
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
session     = cdrcgi.getSession(fields)    or "guest"
importDocId = fields.getvalue('importDoc') or None
duplicate   = fields.getvalue('duplicate') or None
duplicateOf = fields.getvalue('duplicateOf') or ""
primaryId   = fields.getvalue('primaryId') or None
source      = fields.getvalue('source')    or 'CTS'
extra       = u""
if primaryId:
    primaryId = unicode(primaryId, 'utf-8')
if importDocId:
    extra = importDoc(importDocId, primaryId, session, source)
elif duplicate:
    extra = markDuplicate(duplicate, primaryId, session, source, duplicateOf)

url = 'http://%s/u/cts-submitted-trials.py?source=%s' % (CTS_HOST, source)
f = urllib.urlopen(url)
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
        var form = document.forms[0];
        var source = form.source.value;
        if (source == 'Oncore') {
            var dup = prompt("Please enter CDR ID of duplicated document");
            if (!dup)
                return;
            form.duplicateOf.value = dup;
        }
        else {
            if (!window.confirm("Mark " + primaryId + " as Duplicate?"))
                return;
        }
        form.duplicate.value = whichTrial;
        form.primaryId.value = primaryId;
        form.importDoc.value = '';
        form.submit();
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
   <input type='hidden' name='duplicateOf' value='' />
   <input type='hidden' name='Session' value='%s' />
   <input type='hidden' name='source' value='%s' />
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
""" % (u"\n".join(js), session or '', source, extra)]
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
sendPage(u"".join(html))
