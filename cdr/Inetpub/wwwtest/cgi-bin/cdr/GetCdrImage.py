#----------------------------------------------------------------------
#
# $Id: GetCdrImage.py,v 1.1 2004-11-17 14:39:55 bkline Exp $
#
# Send JPEG version of a CDR image to the browser, possibly resized.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cdrdb, sys, cgi, msvcrt, os, cdr, cdrcgi, Image, cStringIO

msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
message = "GetCdrImage: No doc ID found"
fields  = cgi.FieldStorage()
width   = fields and fields.getvalue("width")   or None
fname   = fields and fields.getvalue("fname")   or None
quality = fields and fields.getvalue("quality") or "75"
docId   = fields and fields.getvalue("id")      or cdrcgi.bail(message)
conn    = cdrdb.connect()
cursor  = conn.cursor()
intId   = cdr.exNormalize(docId)[1]
cursor.execute("""\
    SELECT b.data
      FROM doc_blob b
      JOIN doc_blob_usage u
        ON u.blob_id = b.id
     WHERE u.doc_id = ?""", intId)
rows = cursor.fetchall()
if not rows:
    cdrcgi.bail("%s not found" % docId)
bytes = rows[0][0]
iFile = cStringIO.StringIO(bytes)
image = Image.open(iFile)
if image.mode == 'P':
    image = image.convert('RGB')
try:
    quality = int(quality)
except:
    quality = 75
if width:
    try:
        width = int(width)
        iWidth, iHeight = image.size
        if width < iWidth:
            ratio = 1.0 * iHeight / iWidth
            height = int(round(width * ratio))
            image = image.resize((width, height), Image.ANTIALIAS)
    except Exception, e:
        cdrcgi.bail("Failure resizing %s: %s" % (docId, str(e)))
newImageFile = cStringIO.StringIO()
image.save(newImageFile, "JPEG", quality = 85)
bytes = newImageFile.getvalue()
if fname:
    f = open(fname, "wb")
    f.write(bytes)
    f.close
sys.stdout.write("Content-Type: image/jpeg\r\n")
sys.stdout.write("Content-Length: %d\r\n\r\n" % len(bytes))
sys.stdout.write(bytes)
