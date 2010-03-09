#----------------------------------------------------------------------
#
# $Id$
#
# Stream media blob over HTTP directly from the CDR database.  We do
# this to avoid limitations imposed on memory usage within the CDR
# Server.
#
# BZIssue::4767
#
#----------------------------------------------------------------------
import cdrdb, cgi, cdrcgi, cdr, msvcrt, sys, os, time
etree = cdr.importEtree()

mimeTypes = {
    'GIF': 'image/gif',
    'JPEG': 'image/jpeg',
    'PNG': 'image/png',
    'MP3': 'audio/mpeg',
    'RAM': 'audio/x-pn-realaudio',
    'WAV': 'audio/x-wav',
    'WMA': 'audio/x-ms-wma',
    'AVI': 'video/x-msvideo',
    'MPEG2': 'video/mpeg2',
    'MJPG': 'video/x-motion-jpeg' }
suffixes = {
    'GIF': 'gif',
    'JPEG': 'jpg',
    'PNG': 'png',
    'MP3': 'mp3',
    'RAM': 'ram',
    'WAV': 'wav',
    'AVI': 'avi',
    'MPEG2': 'mpeg',
    'MJPG': 'mjpg' }

def makePicklist():
    picklist = ["<select name='enc'>"]
    for key in mimeTypes:
        picklist.append("<option value='%s'>%s</option>" % (key,
                                                            mimeTypes[key]))
    picklist.append('</select>')
    return "\n".join(picklist)

def getEncodingType(cursor, docId, docVer = None):
    docId = cdr.exNormalize(docId)[1]
    if docVer:
        cursor.execute("""\
            SELECT xml
              FROM doc_version
             WHERE id = ?
               AND num = ?""", (docId, docVer))
    else:
        cursor.execute("""\
            SELECT xml
              FROM document
             WHERE id = ?""", docId)
    rows = cursor.fetchall()
    if not rows:
        if docVer:
            cdrcgi.bail("Cannot find version %s of CDR%s" % (docVer, docId))
        else:
            cdrcgi.bail("Cannot find CDR%s" % docId)
    try:
        tree = etree.XML(rows[0][0].encode('utf-8'))
    except Exception, e:
        cdrcgi.bail("parsing CDR%s: %s" % (docId, e))
    for medium in ('Image', 'Sound', 'Video'):
        xpath = 'PhysicalMedia/%sData/%sEncoding' % (medium, medium)
        for e in tree.findall(xpath):
            return e.text
    return None

cursor = cdrdb.connect('CdrGuest').cursor()
fields = cgi.FieldStorage()
docId  = fields.getvalue('id') or cdrcgi.bail("Missing required 'id' parameter")
docVer = fields.getvalue('ver') or ''
enc    = fields.getvalue('enc') or getEncodingType(cursor, docId, docVer)
if not (enc):
    docId = cdr.exNormalize(docId)[1]
    print """\
Content-type: text/html

<html>
 <head><title>Get CDR Blob</title></head>
 <body>
  <h1>Get CDR Blob</h1>
  <form action='GetCdrBlob.py'>
   <input type='hidden' name='id' value='%s' /> 
   <input type='hidden' name='ver' value='%s' />
   Mime Type for CDR%d:  %s
   <input type='submit' />
  </form>
 </body>
</html>""" % (docId, docVer, docId, makePicklist())
else:
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    docId = cdr.exNormalize(docId)[1]
    if docVer:
        cursor.execute("""\
            SELECT b.data
              FROM doc_blob b
              JOIN version_blob_usage u
                ON u.blob_id = b.id
             WHERE u.doc_id = %d
               AND u.doc_version = %s""" % (docId, docVer))
    else:
        cursor.execute("""\
            SELECT b.data
              FROM doc_blob b
              JOIN doc_blob_usage u
                ON u.blob_id = b.id
             WHERE u.doc_id = %d""" % docId)
    rows = cursor.fetchall()
    if not rows:
        if docVer:
            cdrcgi.bail("No blob found for version %s of CDR%d" % (docVer,
                                                                   docId))
        else:
            cdrcgi.bail("no blob found for CDR document %d" % docId)
    bytes = rows[0][0]
    now = time.strftime("%Y%m%d%H%M%S")
    name = "CDR%d-%s.%s" % (docId, now, suffixes[enc])
    sys.stdout.write("Content-Type: %s\r\n" % mimeTypes[enc])
    sys.stdout.write("Content-Disposition: attachment; filename=%s\r\n" % name)
    sys.stdout.write("Content-Length: %d\r\n\r\n" % len(bytes))
    sys.stdout.write(bytes)
