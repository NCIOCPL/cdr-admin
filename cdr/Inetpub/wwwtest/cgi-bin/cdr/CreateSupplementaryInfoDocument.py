#----------------------------------------------------------------------
#
# $Id: CreateSupplementaryInfoDocument.py,v 1.1 2008-09-02 19:27:33 bkline Exp $
#
# Service for creating a new SupplementaryInfo document in the CDR.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, cdrcgi, urllib, xml.dom.minidom, cdr, re, sys, cdrdb

def sendPage(page, textType = 'html'):
    output = u"""\
Content-type: text/%s; charset=utf-8

%s""" % (textType, page)
    print output.encode('utf-8')
    sys.exit(0)

def fail(why):
    sendPage(u"FAILURE: %s" % why, 'text')

def getMimeType(mimeType, fileName):
    mimeKey = fileName[-5:].lower()
    if mimeKey != ".html":
        mimeKey = mimeKey[1:]
    return mimeType or {
        ".doc":  "application/msword",
        ".txt":  "text/plain",
        ".rtf":  "text/rtf",
        ".htm":  "text/html",
        ".zip":  "application/zip",
        ".pdf":  "application/pdf",
        ".xls":  "application/vnd.ms-excel",
        ".wpd":  "application/vnd.wordperfect",
        ".ppd":  "application/vnd.ms-powerpoint",
        ".html": "text/html"
        }.get(mimeKey, "")

def toUnicode(s):
    if not s:
        return u""
    if type(s) is unicode:
        return s
    return unicode(s, 'utf-8')

def addSupplementaryInfoDoc(session, docBytes, title, mimeType, category,
                            description, source, fileName):
    docXml = [u"""\
<SupplementaryInfo xmlns:cdr="cips.nci.nih.gov/cdr">
 <Title>%s</Title>
 <MimeType>%s</MimeType>
 <Category>%s</Category>
""" % (toUnicode(title),
       toUnicode(mimeType),
       toUnicode(category))]
    if description:
        docXml.append(u"""\
 <Description>%s</Description>
""" % toUnicode(description))
    if source:
        docXml.append(u"""\
 <Source>%s</Source>
""" % toUnicode(source))
    if fileName:
        docXml.append(u"""\
 <OriginalFilename>%s</OriginalFilename>
""" % toUnicode(fileName))
    docXml.append(u"""\
</SupplementaryInfo>
""")
    docXml = u"".join(docXml).encode('utf-8')
    fp = open('d:/tmp/supdoc.xml', 'a')
    fp.write(docXml)
    fp.close()
    doc = cdr.Doc(docXml, "SupplementaryInfo", blob = docBytes,
                  ctrl = { "DocType": "SupplementaryInfo" },
                  encoding = 'utf-8')
    cdrDoc = str(doc)
    fp = open('d:/tmp/supdoc2.xml', 'a')
    fp.write(cdrDoc)
    fp.close()
    resp = cdr.addDoc(session, doc = cdrDoc, val = 'N', showWarnings = True)
    fp = open('d:/tmp/CreateSupplementaryInfoDocument.log', 'w')
    fp.write("%s" % repr(resp))
    fp.close()
    if not resp[0]:
        raise Exception(toUnicode(cdr.checkErr(resp[1])))
    docId = resp[0]
    doc = cdr.getDoc(session, docId, 'Y')
    error = cdr.checkErr(doc)
    if error:
        raise Exception(u"retrieving %s: %s" % (docId, toUnicode(error)))
    resp = cdr.repDoc(session, doc = doc, val = 'Y', ver = 'Y', checkIn = 'Y',
                      verPublishable = 'N')
    error = cdr.checkErr(resp)
    if error:
        raise Exception(u"checking in %s: %s" % (docId, toUnicode(error)))
    return cdr.exNormalize(docId)[1]

def getPayload(fields):
    payload = fields.getvalue('payload')
    if payload:
        return payload
    url = fields.getvalue('url')
    fp = open('d:/tmp/urlopen.log', 'wb')
    fp.write(u'url: %s\n' % url)
    fp.close()
    if url:
        try:
            urlobj = urllib.urlopen(url)
            if urlobj:
                payload = urlobj.read()
                fp = open('d:/tmp/payload', 'wb')
                fp.write(payload)
                fp.close()
                return payload
        except Exception, e:
            fp = open('d:/tmp/urlopen.log', 'ab')
            fp.write("%s\n" % e) #"foobar") #repr(e))
            fp.close()
            raise
    return None

#----------------------------------------------------------------------
# Processing starts here.
#----------------------------------------------------------------------
fields      = cgi.FieldStorage()
docBytes    = getPayload(fields)              or fail("missing payload")
session     = cdr.login('VerifMailer', '7Verif2Mailer')
fileName    = fields.getvalue('filename')     or u""
mimeType    = fields.getvalue('mimetype')     or u""
mimeType    = getMimeType(mimeType, fileName) or fail("missing mimetype")
category    = fields.getvalue('category')     or fail("missing category")
title       = fields.getvalue('title')        or fail("missing title")
description = fields.getvalue('description')
source      = fields.getvalue('source')
error       = cdr.checkErr(session)

if error:
    fail(error)
try:
    docId = addSupplementaryInfoDoc(session, docBytes, title, mimeType,
                                    category, description, source, fileName)
    cdr.logout(session)
except Exception, e:
    fail(u"%s" % e)
sendPage(u"%d" % docId, "text")
