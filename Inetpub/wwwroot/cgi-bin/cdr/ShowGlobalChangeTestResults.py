#----------------------------------------------------------------------
#
# $Id$
#
# Web interface for showing changes which would be made by a
# global change.
#
# $Log: not supported by cvs2svn $
# Revision 1.4  2009/02/10 19:32:28  bkline
# Added action attribute to form element(s).
#
# Revision 1.3  2008/05/22 16:53:07  ameyer
# Added some sort, count, and error reporting capability.
#
# Revision 1.2  2005/05/26 12:19:22  bkline
# Listed most recent runs at top; changed heading string; fixed unicode
# display.
#
# Revision 1.1  2004/10/25 16:39:12  bkline
# Web interface to changes from proposed global change job.
#
#----------------------------------------------------------------------
import cgi, glob, cdrcgi, os, xml.dom.minidom, cdr

BASE      = 'd:/cdr/GlobalChange/'
script    = 'ShowGlobalChangeTestResults.py'
fields    = cgi.FieldStorage()
directory = fields and fields.getvalue("dir") or None
file      = fields and fields.getvalue("file") or None
sortBy    = fields and fields.getvalue("sortBy") or "byDiff"
reSort    = fields and fields.getvalue("reSort") or None
reSortDir = fields and fields.getvalue("reSortDir") or None

# If re-sort requested, set the directory to force re-sorting
if reSort:
    directory = reSortDir

# Format an xml file with nice indentation
def prettyPrint(doc):
    doc = xml.dom.minidom.parseString(doc).toprettyxml("  ")
    if type(doc) == type(u""):
        doc = doc.encode('utf-8')
    return cdr.stripBlankLines(doc)

# If we got here by a hyperlink to a file from a page constructed
#   by this program, display the file as prettyPrinted xml, or text.
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
        except Exception, info:
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
    baseDir = BASE + directory
    files = os.listdir(baseDir)
    docs = {}
    for file in files:
        if file.startswith('CDR0') and (file.endswith('xml') or
                                        file.endswith('diff') or
                                        file.endswith('NEW_ERRORS.txt')):
            docId = file[:13]
            if not docs.has_key(docId):
                doc = docs[docId] = Doc(baseDir, docId)
    keys = docs.keys()

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
        for key in keys:
            sortKeys[key] = key
        chkSortCdrId = " checked='1'"
    elif sortBy == "byDiff":
        # Index = Diff file size -> docId -> Doc
        # Using negative of size to get reverse sort order
        for key in keys:
            newKey = '%d.%s' % (maxsize - docs[key].diffSize, key)
            sortKeys[newKey] = key
        chkSortDiff = " checked='1'"
    elif sortBy == "byCwdSize":
        # Index = CWD file size -> docId -> Doc
        for key in keys:
            newKey = '%d.%s' % (maxsize - docs[key].cwdSize, key)
            sortKeys[newKey] = key
        chkSortSize = " checked='1'"

    keys = sortKeys.keys()
    keys.sort()
    rows = []
    for key in keys:
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
    docCount = len(keys)
    verCount = len(rows)

    cdrcgi.sendPage(u"""\
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

dirs =  glob.glob(BASE + '/20*')
dirs.sort()
dirs.reverse()
links = []
for d in dirs:
    d2 = os.path.basename(d)
    d3 = d2[:10] + ' ' + d2[11:13] + ':' + d2[14:16] + ':' + d2[17:19]
    link = "<a href='%s?dir=%s'>%s</a><br />\n" % (script, d2, d3)
    links.append(link)
cdrcgi.sendPage(u"""\
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
