#----------------------------------------------------------------------
# Send JPEG version of a CDR image to the browser, possibly resized.
# BZIssue::5001
#----------------------------------------------------------------------
import cdrdb, sys, cgi, msvcrt, os, cdr, cdrcgi, cStringIO
from PIL import Image, ImageEnhance

msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
message = "GetCdrImage: No doc ID found"
fields  = cgi.FieldStorage()
width   = fields.getvalue("width")
res     = fields.getvalue("res")
fname   = fields.getvalue("fname")
quality = fields.getvalue("quality") or "85"
sharpen = fields.getvalue("sharpen")
pp      = fields.getvalue("pp") or ""
cdrId   = fields.getvalue("id")      or cdrcgi.bail(message)

conn    = cdrdb.connect()
cursor  = conn.cursor()

#----------------------------------------------------------------------
# Support for Visuals Online.  Four possible values for res:
#   300   - full size (for printing)
#    72   - 24% (viewing on screen)
#   150   - 1/2 size (in between)
#   thumb - max 120px on a side (thumbnails)
#----------------------------------------------------------------------
def widthFromRes(size, res):
    width, height = size
    if res == "300":
        return None # don't resize
    elif res == "150":
        return int(round(width / 2.0))
    elif res == "72":
        return int(round(width * .24))
    elif res == "thumb":
        if width >= height:
            if width <= 120:
                return None
            return 120
        if height <= 120:
            return None
        return int(round(width * (120.0 / height)))
    else:
        cdrcgi.bail("invalid res value '%s'" % res)

# If the docId comes in in the format 'CDR99999-111.jpg' it is coming
# from the PublishPreview with a size postfix.
# We capture the size instructions.
# --------------------------------------------------------------------
cdrId = cdrId.split('.')[0]
if cdrId.find('-') > 0:
    docId, width = cdrId.split('-')
else:
    docId = cdrId

intId   = cdr.exNormalize(docId)[1]

# If the docId comes in the format 'CDR000999999' it is coming
# from the QC report. If it's coming in the format 'CDR999999' it is 
# coming from the PublishPreview report.  We're selecting the 
# last publishable version for the PP report.
# ------------------------------------------------------------------
ppQuery = ""
if pp == 'Y':
    ppQuery = "AND publishable = 'Y'"
elif pp == 'N':
    ppQuery = ""
elif cdrId.find('CDR0') < 0:
    ppQuery= "AND publishable = 'Y'"

query = """\
    SELECT b.data
      FROM doc_blob b
      JOIN version_blob_usage v
        ON b.id = v.blob_id
      JOIN doc_version dv
        ON dv.id = v.doc_id
       AND dv.num = v.doc_version
     WHERE v.doc_id = %d
       AND dv.num = (SELECT max(num) 
                       FROM doc_version 
                      WHERE id = dv.id
                      %s
                    )""" % (intId, ppQuery)
cursor.execute(query)

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
    quality = 85
if res:
    width = widthFromRes(image.size, res)
if width:
    try:
        width = int(width)
        iWidth, iHeight = image.size
        if width < iWidth:
            ratio = 1.0 * iHeight / iWidth
            height = int(round(width * ratio))
            image = image.resize((width, height), Image.ANTIALIAS)
    except Exception as e:
        cdrcgi.bail("Failure resizing %s: %s" % (docId, str(e)))
newImageFile = cStringIO.StringIO()
if sharpen:
    try:
        sharpen = float(sharpen)
        enh = ImageEnhance.Sharpness(image)
        image = enh.enhance(sharpen)
    except:
        pass
image.save(newImageFile, "JPEG", quality=quality)
bytes = newImageFile.getvalue()
if fname:
    f = open(fname, "wb")
    f.write(bytes)
    f.close
sys.stdout.write("Content-Type: image/jpeg\r\n")
sys.stdout.write("Content-Length: %d\r\n\r\n" % len(bytes))
sys.stdout.write(bytes)
