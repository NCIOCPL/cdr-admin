#----------------------------------------------------------------------
#
# $Id: DiffCTGovProtocol.py,v 1.1 2003-12-16 16:10:56 bkline Exp $
#
# $Log: not supported by cvs2svn $
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
# Show the differences between the CWD and the last (pub) version.
#--------------------------------------------------------------------
docId        = cdr.normalize(docId)
lastVersions = cdr.lastVersions('guest', docId)
filt         = ['name:Extract Significant CTGovProtocol Elements']
name2        = "CurrentWorkingDocument.xml"
print "docId=%s type(docId)=%s" % (str(docId), type(docId))
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
cmd = "diff -au %s %s" % (name1, name2)
try:
    workDir = cdr.makeTempDir('diff')
    os.chdir(workDir)
except StandardError, args:
    cdrcgi.bail(str(args))
f1 = open(name1, "w")
f1.write(doc1.encode('latin-1', 'replace'))
f1.close()
f2 = open(name2, "w")
f2.write(doc2.encode('latin-1', 'replace'))
f2.close()
result = cdr.runCommand(cmd)
cleanup(workDir)
report = cgi.escape(result.output)
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
</html>""" % (title, title, report))

