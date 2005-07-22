#----------------------------------------------------------------------
#
# $Id: DiffCTGovProtocol.py,v 1.4 2005-07-22 19:41:20 venglisc Exp $
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2003/12/18 22:05:29  bkline
# Moved the line splitting before the invocation of diff and removed
# the visual clues about where extra line breaks have been added.
#
# Revision 1.2  2003/12/17 13:48:32  bkline
# Implemented wrapping of long lines at Lakshmi's request.
#
# Revision 1.1  2003/12/16 16:10:56  bkline
# Script to show the differences between the current working copy of
# a CTGovProtocol document and the latest publishable version (or
# the first version if there are no publishable versions).
#
#----------------------------------------------------------------------
import cdr, cdrcgi, cdrdb, sys, cgi, re, sys, os

#----------------------------------------------------------------------
# Load the fields from the form.
#----------------------------------------------------------------------
fields     = cgi.FieldStorage()
docId      = fields and fields.getvalue('DocId') or sys.argv[1]

#----------------------------------------------------------------------
# Don't leave dross around if we can help it.
#----------------------------------------------------------------------
def cleanup(abspath):
    try:
        os.chdir("..")
        cdr.runCommand("rm -rf %s" % abspath)
    except:
        pass

#--------------------------------------------------------------------
# Wrap long lines in the report.
#--------------------------------------------------------------------
def wrap(report):
    report = report.replace("\r", "")
    oldLines = report.split("\n")
    newLines = []
    for line in oldLines:
        if len(line) <= 80:
            newLines.append(line)
        else:
            while len(line) > 80:
                newLines.append(line[:80])
                line = line[80:]
            if line:
                newLines.append(line)
    return "\n".join(newLines)
                
#--------------------------------------------------------------------
# Show the differences between the CWD and the last (pub) version.
#--------------------------------------------------------------------
docId        = cdr.normalize(docId)
lastVersions = cdr.lastVersions('guest', docId)
filt         = ['name:Extract Significant CTGovProtocol Elements']
name2        = "CurrentWorkingDocument.xml"
# print "docId=%s type(docId)=%s" % (str(docId), type(docId))
response     = cdr.filterDoc('guest', filt, docId)

if type(response) in (type(""), type(u"")):
    cdrcgi.bail(response)

doc2         = unicode(response[0], 'utf-8')
if lastVersions[1] != -1:
    name1 = "LastPublishableVersion.xml"
    response = cdr.filterDoc('guest', filt, docId,
                             docVer = str(lastVersions[1]))
elif lastVersions[0] != -1:
    name1 = "FirstVersion.xml"
    response = cdr.filterDoc('guest', filt, docId, docVer = "1")
                             #docVer = str(lastVersions[0]))
else:
    cdrcgi.bail("No versions exist for %s" % docId)

if type(response) in (type(""), type(u"")):
    cdrcgi.bail(response)

doc1 = unicode(response[0], 'utf-8')
doc1 = wrap(doc1.encode('latin-1', 'replace'))
doc2 = wrap(doc2.encode('latin-1', 'replace'))
cmd = "diff -au %s %s" % (name1, name2)
try:
    workDir = cdr.makeTempDir('diff')
    os.chdir(workDir)
except StandardError, args:
    cdrcgi.bail(str(args))
f1 = open(name1, "w")
f1.write(doc1)
f1.close()
f2 = open(name2, "w")
f2.write(doc2)
f2.close()
result = cdr.runCommand(cmd)
cleanup(workDir)
report = result.output
if report.strip():
    title = "Differences between %s and %s" % (name1, name2)
else:
    title = "%s and %s are identical" % (name1, name2)
cdrcgi.sendPage("""\
<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>%s</title>
 </head>
 <body>
  <h3>%s</h3>
  <pre>%s</pre>
 </body>
</html>""" % (title, title, cgi.escape(report)))
