#----------------------------------------------------------------------
# Stream media blob over HTTP directly from the CDR database.  We do
# this to avoid limitations imposed on memory usage within the CDR
# Server.
#
# BZIssue::4767
#----------------------------------------------------------------------
import cdrdb, cgi, cdrcgi, cdr, msvcrt, sys, os, time
etree = cdr.importEtree()

class DocInfo:
    def __init__(self, cursor, docId, docVer = None):
        self.docId = cdr.exNormalize(docId)[1]
        self.docVer = docVer
        self.mimeType = self.filename = None
        if docVer:
            cursor.execute("""\
                SELECT xml
                  FROM doc_version
                 WHERE id = ?
                   AND num = ?""", (self.docId, self.docVer))
        else:
            cursor.execute("""\
                SELECT xml
                  FROM document
                 WHERE id = ?""", self.docId)
        rows = cursor.fetchall()
        if not rows:
            if docVer:
                raise cdr.Exception("Cannot find version %s of CDR%s" %
                                    (docVer, docId))
            else:
                raise cdr.Exception("Cannot find CDR%s" % docId)
        try:
            tree = etree.XML(rows[0][0].encode('utf-8'))
        except Exception, e:
            raise cdr.Exception("parsing CDR%s: %s" % (docId, e))
        if tree.tag == 'Media':
            for medium in ('Image', 'Sound', 'Video'):
                xpath = 'PhysicalMedia/%sData/%sEncoding' % (medium, medium)
                for e in tree.findall(xpath):
                    encoding = e.text
                    self.mimeType = {
                        'GIF': 'image/gif',
                        'JPEG': 'image/jpeg',
                        'PNG': 'image/png',
                        'MP3': 'audio/mpeg',
                        'RAM': 'audio/x-pn-realaudio',
                        'WAV': 'audio/x-wav',
                        'WMA': 'audio/x-ms-wma',
                        'AVI': 'video/x-msvideo',
                        'MPEG2': 'video/mpeg2',
                        'MJPG': 'video/x-motion-jpeg' }.get(encoding)
                    suffix = {
                        'GIF': 'gif',
                        'JPEG': 'jpg',
                        'PNG': 'png',
                        'MP3': 'mp3',
                        'RAM': 'ram',
                        'WAV': 'wav',
                        'AVI': 'avi',
                        'MPEG2': 'mpeg',
                        'MJPG': 'mjpg' }.get(encoding, 'bin')
                    self.filename = DocInfo.makeFilename(self.docId, docVer,
                                                         suffix)
        elif tree.tag == 'SupplementaryInfo':
            for e in tree.findall('MimeType'):
                self.mimeType = e.text
            for e in tree.findall('OriginalFilename'):
                self.filename = e.text
            if not self.filename:
                suffix = {
                    'application/pdf': 'pdf',
                    'application/msword': 'doc',
                    'application/vnd.ms-excel': 'xls',
                    'application/vnd.wordperfect': 'wpd',
                    'application/vnd.ms-powerpoint': 'ppt',
                    'application/zip': 'zip',
                    'text/html': 'html',
                    'text/plain': 'txt',
                    'text/rtf': 'rtf',
                    'message/rfc822': 'eml',
                    'image/jpeg': 'jpg' }.get(self.mimeType, 'bin')
                self.filename = DocInfo.makeFilename(self.docId, docVer,
                                                     suffix)
        else:
            raise cdr.Exception("don't know about '%s' documents" % tree.tag)
        if not self.mimeType:
            if docVer:
                raise cdr.Exception("unable to determine mime type for "
                                    "version %s of CDR%d" %
                                    (docVer, self.docId))
            else:
                raise cdr.Exception("unable to determine mime type for "
                                    "CDR%d" % self.docId)

    @staticmethod
    def makeFilename(docId, docVer, suffix):
        if docVer:
            return "CDR%d-%s.%s" % (docId, docVer, suffix)
        else:
            return "CDR%d.%s" % (docId, suffix)

cursor = cdrdb.connect('CdrGuest').cursor()
fields = cgi.FieldStorage()
docId  = fields.getvalue('id') or cdrcgi.bail("Missing required 'id' parameter")
docVer = fields.getvalue('ver') or ''
try:
    info = DocInfo(cursor, docId, docVer)
except Exception, e:
    cdrcgi.bail(u"%s" % e)
msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
if info.docVer:
    cursor.execute("""\
            SELECT b.data
              FROM doc_blob b
              JOIN version_blob_usage u
                ON u.blob_id = b.id
             WHERE u.doc_id = %d
               AND u.doc_version = %s""" % (info.docId, info.docVer))
else:
    cursor.execute("""\
            SELECT b.data
              FROM doc_blob b
              JOIN doc_blob_usage u
                ON u.blob_id = b.id
             WHERE u.doc_id = %d""" % info.docId)
rows = cursor.fetchall()
if not rows:
    if info.docVer:
        cdrcgi.bail("No blob found for version %s of CDR%d" % (docVer,
            info.docId))
    else:
        cdrcgi.bail("No blob found for CDR document %d" % info.docId)
bytes = rows[0][0]
sys.stdout.write("Content-Type: %s\r\n" % info.mimeType)
sys.stdout.write("Content-Disposition: attachment; filename=%s\r\n" %
                 info.filename)
sys.stdout.write("Content-Length: %d\r\n\r\n" % len(bytes))
sys.stdout.write(bytes)
