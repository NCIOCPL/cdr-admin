#----------------------------------------------------------------------
# Web interface for showing changes which would be made by a
# global change.
#----------------------------------------------------------------------
import cgi
from glob import glob
from html import escape as html_escape
import os
import re
from lxml import etree
import cdr
import cdrcgi
from cdrapi.docs import Doc
from cdrapi.users import Session

BASE      = f'{cdr.BASEDIR}/GlobalChange'
script    = 'ShowGlobalChangeTestResults.py'
fields    = cgi.FieldStorage()
directory = fields.getvalue("dir") or None
filename  = fields.getvalue("file") or None
sortBy    = fields.getvalue("sortBy") or "byDiff"
reSort    = fields.getvalue("reSort") or None
reSortDir = fields.getvalue("reSortDir") or None

# If re-sort requested, set the directory to force re-sorting
if reSort:
    directory = reSortDir

# Format an xml file with nice indentation
def prettyPrint(xml):
    xml = re.sub(r"<\?xml[^?]*\?>\s*", "", xml)
    doc = Doc(Session("guest"), xml=xml)
    doc.doctype = doc.root.tag
    doc.normalize()
    xml = etree.tostring(doc.root, pretty_print=True, encoding="unicode")
    return cdr.stripBlankLines(xml)

# If we got here by a hyperlink to a file from a page constructed
#   by this program, display the file as prettyPrinted xml, or text.
if filename and directory:
    path = f"{BASE}/{directory}/{filename}"
    with open(path, encoding="utf-8") as fp:
        doc = fp.read()
    if filename.lower().endswith('.xml'):
        doc = prettyPrint(doc)
    cdrcgi.sendPage("""\
<html>
 <body>
  <pre>
%s
  </pre>
 </body>
</html>
""" % html_escape(doc))

class DocFileInfo:
    """
    Info about one file, e.g., "CDR0000012345.new.xml
    """
    def __init__(self, baseDir, filename):
        """
        Constructor.
        Pass
            baseDir  - Directory path containing the files.
            filename -  e.g., "CDR0000012345.new.xml
        """
        self.fname = filename
        self.fsize = 0
        try:
            fullpath = "%s/%s" % (baseDir, filename)
            self.fsize = os.stat(fullpath).st_size
        except Exception as info:
            # Won't always exist
            self.fname = None

class DocVerInfo:
    """
    Info for all versions of one document.
    """
    def __init__(self, baseDir, basename):
        """
        Constructor
        Pass:
            baseDir  - Directory path containing the files.
            basename - CDR ID in string format "CDR0000012345.lastv".
        """
        self.old  = DocFileInfo(baseDir, "%s%s" % (basename, "old.xml"))
        self.new  = DocFileInfo(baseDir, "%s%s" % (basename, "new.xml"))
        self.diff = DocFileInfo(baseDir, "%s.%s" % (basename, "diff"))
        self.err  = DocFileInfo(baseDir, "%s.%s" % (basename, "NEW_ERRORS.txt"))

class Doc:
    def __init__(self, baseDir, docId):
        """
        Constructor for object representing all files, all versions, of
        one CDR document.  May include old, new, diff, and error files for
        each of CWD, last version, and last publishable version.

        Pass:
            baseDir - Directory path containing the files.
            docId   - "CDR000..." format CDR ID.
        """

        self.docId = docId
        self.cwd   = DocVerInfo(baseDir, "%s.%s" % (docId, "cwd"))
        self.lastv = DocVerInfo(baseDir, "%s.%s" % (docId, "lastv"))
        self.lastp = DocVerInfo(baseDir, "%s.%s" % (docId, "pub"))

        # Used for all sorting
        self.cwdSize  = self.cwd.old.fsize
        self.diffSize = self.cwd.diff.fsize

def makeLink(name, label):
    # Construct a full hyperlink to show a file using this program
    if name is not None:
        return "<a href='%s?dir=%s&file=%s'>%s</a>" % (script, directory,
                                                       name, label)
    # Else there isn't a file with this name
    return "n/a"

def makeRow(docId, col2, verInfo):
    """
    Make one row in the file list display
    Pass:
        docId    - Text format doc id, or "&nbsp;" if id already shown.
        col2     - Disply name, one of "CWD", "LASTV", etc.
        verInfo  - Collection of DocFileInfo's for this doc id.
    Return:
        One complete row for the HTML table of hyperlinked files.
    """
    # If there is an errors file, we need to hyperlink it
    errLink = "&nbsp;"
    if verInfo.err.fname:
        errLink = makeLink(verInfo.err.fname, 'Errs')
    return """\
  <tr>
   <td>%s</td>
   <td align='left'>%s</td>
   <td>%s</td>
   <td>%s</td>
   <td>%s</td>
   <td>%s</td>
   <td align='right'>%s</td>
   <td align='right'>%s</td>
  </tr>
""" % (docId, col2, makeLink(verInfo.old.fname, 'Old'),
                 makeLink(verInfo.new.fname, 'New'),
                 makeLink(verInfo.diff.fname, 'Diff'), errLink,
                 verInfo.new.fsize, verInfo.diff.fsize)


# If the user has picked a directory, take him to a display of
#   all files in that directory
if directory:
    baseDir = f"{BASE}/{directory}"
    files = os.listdir(baseDir)
    docs = {}
    for filename in files:
        if filename.startswith('CDR0') and (filename.endswith('xml') or
                                        filename.endswith('diff') or
                                        filename.endswith('NEW_ERRORS.txt')):
            docId = filename[:13]
            if docId not in docs:
                doc = docs[docId] = Doc(baseDir, docId)

    # Check radio buttons
    chkSortDiff  = ''
    chkSortSize  = ''
    chkSortCdrId = ''

    # Construct an index dictionary of id = Doc
    sortKeys = {}
    maxsize  = 10000000  # Subtract from here to reverse order of sort
    if sortBy == "byCdrId":
        # Index = docId -> docId -> Doc
        # Not needed, but simplifies the logic to have all indexes at the
        #   same level of indirection
        for key in docs:
            sortKeys[key] = key
        chkSortCdrId = " checked='1'"
    elif sortBy == "byDiff":
        # Index = Diff file size -> docId -> Doc
        # Using negative of size to get reverse sort order
        for key in docs:
            newKey = '%d.%s' % (maxsize - docs[key].diffSize, key)
            sortKeys[newKey] = key
        chkSortDiff = " checked='1'"
    elif sortBy == "byCwdSize":
        # Index = CWD file size -> docId -> Doc
        for key in docs:
            newKey = '%d.%s' % (maxsize - docs[key].cwdSize, key)
            sortKeys[newKey] = key
        chkSortSize = " checked='1'"

    rows = []
    for key in sorted(sortKeys):
        doc = docs[sortKeys[key]]
        docId = doc.docId
        if doc.cwd.diff.fname:
            rows.append(makeRow(docId, "CWD", doc.cwd))
            docId = "&nbsp;"
        if doc.lastv.diff.fname:
            rows.append(makeRow(docId, "LASTV", doc.lastv))
            docId = "&nbsp;"
        if doc.lastp.diff.fname:
            rows.append(makeRow(docId, "LASTP", doc.lastp))

    # What we're showing
    stamp = ""
    if directory:
        stamp = "Runtime: %s &nbsp; " % directory
    # Counts
    docCount = len(sortKeys)
    verCount = len(rows)

    cdrcgi.sendPage("""\
<html>
 <head>
  <title>Global Change Test Results</title>
  <style type='text/css'>
   body { font-family: Arial }
  </style>
 </head>
 <body>
<form method='post' action='ShowGlobalChangeTestResults.py'>
 <center>
 <input type='hidden' name='reSortDir' value='%s' />
 <input type='submit' name='reSort' value='Sort By' />
 <input type='radio' name='sortBy' value='byCdrId'%s>CDR ID</input>
 <input type='radio' name='sortBy' value='byDiff'%s>CWD diff size</input>
 <input type='radio' name='sortBy' value='byCwdSize'%s>New file size</input>
 </center>
</form>
<p>%sTotal docs = %d &nbsp; Total versions = %d</p>

  <table border='0'>
  <tr>
   <td>CDR ID</td><td>Ver.</td><td colspan='4'>Files</td>
   <td>New Size</td><td>Diff size</td>
  </tr>
%s
  </table>
 </body>
</html>
""" % (directory, chkSortCdrId, chkSortDiff, chkSortSize,
       stamp, docCount, verCount, "".join(rows)))

dirs =  glob(f"{BASE}/20*")
links = []
for d in reversed(sorted(dirs)):
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
