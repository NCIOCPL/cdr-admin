#----------------------------------------------------------------------
#
# $Id$
#
# Send back resized version of a JPEG image.
#
# BZIssue::5125
#
#----------------------------------------------------------------------
import sys, cgi, msvcrt, os, Image, cStringIO, ImageEnhance, base64

DEBUG = False

msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

fields  = cgi.FieldStorage()
fname   = fields.getvalue("fname")
percent = fields.getvalue("percent")
width   = fields.getvalue("width")
res     = fields.getvalue("res")
image   = fields.getvalue("image")
quality = fields.getvalue("quality") or "85"
sharpen = fields.getvalue("sharpen")

#----------------------------------------------------------------------
# Used for debugging.
#----------------------------------------------------------------------
def log(what):
    fp = open("d:/cdr/log/ResizeImage.log", "a")
    fp.write("%s\n" % repr(what))
    fp.close()

#----------------------------------------------------------------------
# Used for failures.
#----------------------------------------------------------------------
def bail(why):
    log(why)
    print """\
Content-type: text/plain

%s""" % why
    sys.exit(0)

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
        bail("invalid res value '%s'" % res)

#----------------------------------------------------------------------
# If the script is invoked without an image parameter, show usage.
#----------------------------------------------------------------------
if not image:
    print """\
Content-type: text/plain

ResizeImage.py

Send a POST request to this service with the following parameters:

image
   bytes for the original JPEG image; required
percent
   floating point value (without "%") for percentage to scale image; optional
width
   integer representing new width of scaled image; optional
quality
   integer representing JPEG compression quality; optional
sharpen
   non-negative floating point value for sharpening image; optional

Returns the bytes for the rescaled image, with a ContentType header of
image/jpeg.

If neither percent nor width is specified the image will be returned
at the original scale.  If both percent and width are specified, the
width value will be ignored.  If quality is not specified, the default
value of 85 will be used.  Values less than 0.5 for sharpen will blur
the image (lower values blur more); values greater than 0.5 will
sharpen edges."""

    sys.exit(0)

if DEBUG:
    fp = open('/tmp/ResizeImage-%s' % os.getpid(), 'wb')
    fp.write(repr(image))
    fp.close()
try:
    iFile = cStringIO.StringIO(image)
    image = Image.open(iFile)
except:
    try:
        bytes = base64.b64decode(image)
        if DEBUG:
            fp = open('/tmp/image-b64decoded-%s' % os.getpid(), 'wb')
            fp.write(bytes)
            fp.close()
        iFile = cStringIO.StringIO(bytes)
        image = Image.open(iFile)
    except Exception, e:
        bail("invalid image: %s" % e)

# If we started with an RGB + JPEG, we'll use the same icc_profile in the
#  scaled image.  Otherwise we'll take the default behavior of discarding it
try:
    if image.mode == 'RGB' and image.format == 'JPEG':
        #copyICC = image.info['icc_profile']
        copyICC = image.info.get("icc_profile")
    else:
        copyICC = None
except Exception, e:
    bail("failure remembering profile: %s" % e)
if DEBUG:
    log("checkpoint A")
try:
    if image.mode == 'P':
        image = image.convert('RGB')
except Exception, e:
    bail("image.convert() failure: %s" % e)
try:
    quality = int(quality)
except:
    quality = 85

if percent:
    try:
        width = float(percent) * image.size[0] * .01
    except Exception, e:
        bail("inavlid percent value %s: %s" % (percent, e))
elif res:
    try:
        width = widthFromRes(image.size, res)
    except Exception, e:
        bail("widthFromRes(): %s" % e)
if width:
    try:
        width = int(width)
        iWidth, iHeight = image.size
        if width < iWidth:
            ratio = 1.0 * iHeight / iWidth
            height = int(round(width * ratio))
            image = image.resize((width, height), Image.ANTIALIAS)
    except Exception, e:
        bail("Failure resizing image: %s" % e)
if DEBUG:
    log("checkpoint B")
newImageFile = cStringIO.StringIO()
if sharpen:
    try:
        sharpen = float(sharpen)
        enh = ImageEnhance.Sharpness(image)
        image = enh.enhance(sharpen)
    except:
        pass

# Options in save()
try:
    saveArgs = {}
    saveArgs['quality'] = quality
    if copyICC:
        saveArgs['icc_profile'] = copyICC
except Exception, e:
    bail("setting saveArgs: %s" % repr(e))
try:
    image.save(newImageFile, "JPEG", **saveArgs)
    bytes = newImageFile.getvalue()
except Exception, e:
    bail("failure transforming image: %s" % e)
if DEBUG:
    log("checkpoint C")
    fname = "d:/tmp/final-image.jpg"
if fname:
    f = open(fname, "wb")
    f.write(bytes)
    f.close
sys.stdout.write("Content-Type: image/jpeg\r\n")
sys.stdout.write("Content-Length: %d\r\n\r\n" % len(bytes))
sys.stdout.write(bytes)
