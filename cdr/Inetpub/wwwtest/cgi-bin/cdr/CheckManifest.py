#----------------------------------------------------------------------
#
# Preliminary test program for experimenting with methods of verifying
# that the files in the manifest can be read by the web server.
#
#----------------------------------------------------------------------
import cdr, win32file, sys, xml.dom.minidom, os, cdrcgi

def bail(why):
    cdrcgi.sendPage(u"""\
<html>
 <head>
  <title>Manifest Check Failure</title>
 </head>
 <body>%s</body>
</html>
""" % why)
    sys.exit(0)

class File:
    def __init__(self, node = None, name = None):
        self.name  = name
        self.stamp = None
        if node:
            for child in node.childNodes:
                if child.nodeName == 'Name':
                    self.name  = cdr.getTextContent(child)
                elif child.nodeName == 'Timestamp':
                    self.stamp = cdr.getTextContent(child)
    def getFileTime(self):
        h = win32file.CreateFile(self.name,
                                 win32file.GENERIC_READ, 0, None,
                                 win32file.OPEN_EXISTING, 0, 0)
        t = win32file.GetFileTime(h)
        h.Close()
        s = t[3].Format("%Y-%m-%dT%H:%M:%S")
        return s
    def getFileSize(self):
        f = file(self.name)
        bytes = f.read()
        s = len(bytes)
        f.close()
        return s

def getFiles():
    files = []
    dom = xml.dom.minidom.parse("./CdrManifest.xml")
    for node in dom.getElementsByTagName('File'):
        files.append(File(node))
    return files

try:
    os.chdir(cdr.CLIENT_FILES_DIR)
except Exception, e:
    bail(u"Unable to change to %s: %s" % (cdr.CLIENT_FILES_DIR, e))

try:
    files = getFiles()
except Exception, e:
    bail(u"Failure parsing manifest: %s" % e)

rows = []
errors = 0
filePaths = {}
for f in files:
    filePaths[f.name.upper()] = f
    try:
        s = f.getFileSize()
    except:
        errors += 1
        s = u"Unable to get file size"
    try:
        t = f.getFileTime()
        if t != f.stamp:
            rows.append((f, s, t, u"Timestamps differ"))
            errors += 1
        else:
            rows.append((f, s, t, u"OK"))
    except:
        errors += 1
        rows.append((f, s, None, u"Unable to get file timestamp"))
def gatherFiles(dirPath):
    files = []
    for name in os.listdir(dirPath):
        thisPath = os.path.join(dirPath, name)
        if os.path.isdir(thisPath):
            files += gatherFiles(thisPath)
        else:
            files.append(File(name = thisPath))
    return files

for f in gatherFiles('.'):
    if f.name.upper() not in filePaths:
        errors += 1
        try:
            t = f.getFileTime()
        except:
            t = u"Unable to read file timestamp"
        try:
            s = f.getFileSize()
        except:
            s = u"Unable to read file"
        rows.append((f, t, u"Missing from manifest"))
summary = u"Passed"
if errors:
    summary = u"Failed (%d errors)" % errors
html = [u"""\
<html>
 <head>
  <title>Manifest Check</title>
  <style type='text/css'>
   body { color: blue; }
  </style>
 </head>
 <body>
  <h1>Manifest Check</h1>
  <h2 style='color: %s'>%s</h2>
  <table border='1' cellpadding='3' cellspacing='0'>
   <tr>
    <th>Filename</th>
    <th>File Size</th>
    <th>Manifest Stamp</th>
    <th>File Stamp</th>
    <th>Status</th>
   </tr>
""" % (errors and u'red' or u'green', summary)]
for row in rows:
    html.append(u"""\
   <tr style='color: %s'>
    <td>%s</td>
    <td align='right'>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (row[3] == u'OK' and u'green' or u'red',
       row[0].name, row[1], row[0].stamp, row[2], row[3]))
html.append(u"""\
  </table>
 </body>
</html>
""")
cdrcgi.sendPage(u"".join(html))
