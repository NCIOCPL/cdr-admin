#----------------------------------------------------------------------
#
# $Id$
#
# Show a piece of a log file.
#
#----------------------------------------------------------------------
import os, cgi, sys, time, re

DEFAULT_COUNT = 2000000

try: # Windows needs stdio set for binary mode.
    import msvcrt
    msvcrt.setmode (0, os.O_BINARY) # stdin  = 0
    msvcrt.setmode (1, os.O_BINARY) # stdout = 1
except ImportError:
    pass

def makeAscii(s):
    return re.sub(u"[\x80-\xff%]", lambda m: "%%%02X" % ord(m.group(0)[0]), s)

def showForm(info="", path="", start="", count=""):
    print """\
Content-type: text/html

<html>
 <head>
  <title>CDR Log Viewer</title>
  <style type="text/css">
   * { font-family: sans-serif }
   label { width: 50px; padding-bottom: 5px; display: inline-block; }
   #path, #start, #count { width: 300px; }
  </style>
 </head>
 <body>
  <h1>CDR Log Viewer</h1>
  <p>%s</p>
  <form action="log-tail.py" method="POST">
   <label for="path">Path: </label>
   <input id="path" name="p" value="%s"/><br />
   <label for="start">Start: </label>
   <input name="s" id="start" value="%s" /><br />
   <label for="count">Count: </label>
   <input name="c" id="count" value="%s"/><br /><br />
   <input type="submit" />
  </form>
 </body>
</html>
""" % (info, path, start, count)

fields = cgi.FieldStorage()
p = fields.getvalue("p") or ""
s = fields.getvalue("s") or ""
c = fields.getvalue("c") or ""

if p:
    try:
        stat = os.stat(p)
        stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(stat.st_mtime))
        info = "%s %s bytes (%s GMT)" % (p, stat.st_size, stamp)
        count = long(c or "100000")
        start = long(s or "0")
        if count < 0:
            count = 0
        if not start and s != "0":
            if not count:
                count = DEFAULT_COUNT
            if count > stat.st_size:
                count = stat.st_size
            else:
                start = stat.st_size - count
        else:
            if start < 0:
                if abs(start) > stat.st_size:
                    start = 0
                else:
                    start = stat.st_size + start
            elif start > stat.st_size:
                start = stat.st_size
            available = stat.st_size - start
            if count > available:
                count = available
        if count:
            fp = open(p, "rb")
            if start:
                fp.seek(start)
            bytes = fp.read(count)
            print "Content-type: text/plain\n"
            print "%s bytes %d-%d\n" % (info, start + 1, start + count)
            print makeAscii(bytes)
        else:
            showForm(info)
    except Exception, e:
        print "Content-type: text/plain\n\n%s" % repr(e)
else:
    showForm()
