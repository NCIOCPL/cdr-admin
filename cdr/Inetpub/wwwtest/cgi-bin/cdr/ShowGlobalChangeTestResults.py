#----------------------------------------------------------------------
#
# $Id: ShowGlobalChangeTestResults.py,v 1.2 2005-05-26 12:19:22 bkline Exp $
#
# Web interface for showing changes which would be made by a
# global change.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2004/10/25 16:39:12  bkline
# Web interface to changes from proposed global change job.
#
#----------------------------------------------------------------------
import cgi, glob, cdrcgi, os, xml.dom.minidom, cdr

BASE = 'd:/cdr/GlobalChange/'
script = 'ShowGlobalChangeTestResults.py'
fields = cgi.FieldStorage()
directory = fields and fields.getvalue("dir") or None
file = fields and fields.getvalue("file") or None

def prettyPrint(doc):
    doc = xml.dom.minidom.parseString(doc).toprettyxml("  ")
    if type(doc) == type(u""):
        doc = doc.encode('utf-8')
    return cdr.stripBlankLines(doc)

if file and directory:
    f = open(BASE + directory + "/" + file)
    doc = f.read()
    if file.lower().endswith('.xml'):
        doc = prettyPrint(doc)
    cdrcgi.sendPage(u"""\
<html>
 <body>
  <pre>
%s
  </pre>
 </body>
</html>
""" % cgi.escape(unicode(doc, "utf-8")))

class Set:
    def __init__(self):
        self.old = None
        self.new = None
        self.diff = None
class Doc:
    def __init__(self, id):
        self.id = id
        self.cwd = Set()
        self.lastv = Set()
        self.lastp = Set()

def makeLink(name, label):
    return "<a href='%s?dir=%s&file=%s'>%s</a>" % (script, directory, name,
                                                   label)
def makeRow(id, col2, set):
    return """\
  <tr>
   <td>%s</td>
   <td align='center'>%s</td>
   <td>%s</td>
   <td>%s</td>
   <td>%s</td>
  </tr>
""" % (id, col2, makeLink(set.old, 'Old'), makeLink(set.new, 'New'),
       makeLink(set.diff, 'Diff'))
if directory:
    files = os.listdir(BASE + directory)
    docs = {}
    for file in files:
        if file.startswith('CDR0') and (file.endswith('xml') or
                                        file.endswith('diff')):
            id = file[:13]
            if id not in docs:
                doc = docs[id] = Doc(id)
            else:
                doc = docs[id]
            if file[13:17] == '.cwd':
                set = doc.cwd
            elif file[13:17] == '.pub':
                set = doc.lastp
            else:
                set = doc.lastv
            if file.endswith('.diff'):
                set.diff = file
            elif file.endswith('new.xml'):
                set.new = file
            elif file.endswith('old.xml'):
                set.old = file
    keys = docs.keys()
    keys.sort()
    rows = []
    for key in keys:
        doc = docs[key]
        id = doc.id
        if doc.cwd.diff:
            rows.append(makeRow(id, "CWD", doc.cwd))
            id = "&nbsp;"
        if doc.lastv.diff:
            rows.append(makeRow(id, "LASTV", doc.lastv))
            id = "&nbsp;"
        if doc.lastp.diff:
            rows.append(makeRow(id, "LASTP", doc.lastp))
    cdrcgi.sendPage("""\
<html>
 <head>
  <title>Global Change Test Results</title>
  <style type='text/css'>
   body { font-family: Arial }
  </style>
 </head>
 <body>
  <table border='0'>
%s
  </table>
 </body>
</html>
""" % "".join(rows))
    
dirs =  glob.glob(BASE + '/20*')
dirs.sort()
dirs.reverse()
links = []
for d in dirs:
    d2 = os.path.basename(d)
    d3 = d2[:10] + ' ' + d2[11:13] + ':' + d2[14:16] + ':' + d2[17:19]
    link = "<a href='%s?dir=%s'>%s</a><br />\n" % (script, d2, d3)
    links.append(link)
cdrcgi.sendPage("""\
<html>
 <head>
  <title>Global Change Test Results</title>
  <style type='text/css'>
   body { font-family: Arial }
  </style>
 </head>
 <body>
  <h3>Select Global Change Test Run</h3>
%s
 </body>
</html>""" % "".join(links))
