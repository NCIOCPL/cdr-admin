#----------------------------------------------------------------------
#
# $Id: VersionDiffs.py,v 1.4 2007-10-31 21:11:42 bkline Exp $
#
# Compare two versions of a document.
#
# $Log: not supported by cvs2svn $
# Revision 1.3  2002/12/05 19:09:41  bkline
# Added ability to compare doc between two servers.
#
# Revision 1.2  2002/09/13 11:48:22  bkline
# Added filter to normalize document XML before comparison.
#
#----------------------------------------------------------------------

import cdr, cdrdb, cgi, cdrcgi, os, tempfile, re

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
version1 = fields and fields.getvalue('v1')
version2 = fields and fields.getvalue('v2')
server1  = fields and fields.getvalue('s1') or 'localhost'
server2  = fields and fields.getvalue('s2') or 'localhost'
docId    = fields and fields.getvalue('id')
if not docId:
    cdrcgi.bail("Missing id parameter")
docId    = int(re.sub(r"[^\d+]", "", docId))
if version1 is None or version1 == "0": version1 = "current"
if version2 is None or version2 == "0": version2 = "current"
if version1 == version2 and server1 == server2: 
    cdrcgi.bail("Must specify different versions")

#----------------------------------------------------------------------
# Object for results of an external command.
#----------------------------------------------------------------------
class CommandResult:
    def __init__(self, code, output):
        self.code   = code
        self.output = output

#----------------------------------------------------------------------
# Run an external command.
#----------------------------------------------------------------------
def runCommand(command):
    commandStream = os.popen('%s 2>&1' % command)
    output = commandStream.read()
    code = commandStream.close()
    return CommandResult(code, output)

#----------------------------------------------------------------------
# Create a temporary working area.
#----------------------------------------------------------------------
def makeTempDir():
    if os.environ.has_key("TMP"):
        tempfile.tempdir = os.environ["TMP"]
    where = tempfile.mktemp("diff")
    abspath = os.path.abspath(where)
    try: os.mkdir(abspath)
    except: cdrcgi.bail("Cannot create directory %s" % abspath)
    try: os.chdir(abspath)
    except: 
        cleanup(abspath)
        cdrcgi.bail("Cannot cd to %s" % abspath)
    return abspath

#----------------------------------------------------------------------
# Don't leave dross around if we can help it.
#----------------------------------------------------------------------
def cleanup(abspath):
    try:
        os.chdir("..")
        runCommand("rm -rf %s" % abspath)
    except:
        pass

#----------------------------------------------------------------------
# Get the filters from one of the two servers.
#----------------------------------------------------------------------
def getVersion(docId, version, server = 'localhost'):
    try:
        conn = cdrdb.connect('CdrGuest', dataSource = server)
        curs = conn.cursor()
        if version == "current":
            curs.execute("""\
                    SELECT xml
                      FROM document
                     WHERE id = ?""", docId)
        elif version == "last":
            curs.execute("""\
                    SELECT v.xml
                      FROM doc_version v
                     WHERE v.id = ?
                       AND v.num = (SELECT MAX(num)
                                      FROM doc_version
                                     WHERE id = v.id)""", docId)
        elif version == "lastp":
            curs.execute("""\
                    SELECT v.xml
                      FROM doc_version v
                     WHERE v.id = ?
                       AND v.num = (SELECT MAX(num)
                                      FROM doc_version
                                     WHERE id = v.id
                                       AND publishable = 'Y')""", docId)
        else:
            try:
                verNum = int(version)
            except:
                cdrcgi.bail("invalid version %s" % version)
            curs.execute("""\
                    SELECT xml
                      FROM doc_version
                     WHERE id = ?
                       AND num = ?""", (docId, verNum))
        row = curs.fetchone()
        if not row:
            cdrcgi.bail("Unable to find version '%s' for CDR%010d" %
                    (version, docId))
    except cdrdb.Error, info:
        cleanup(workDir)
        cdrcgi.bail('Database failure: %s' % info[1][0])
    return row[0]

workDir = makeTempDir()
v1Xml = getVersion(docId, version1, server1).replace("\r", "")
v2Xml = getVersion(docId, version2, server2).replace("\r", "")
if v1Xml == v2Xml: cdrcgi.bail("Versions %s and %s are identical" % (version1,
                                                                     version2))
filters = ['name:Fast Denormalization Filter With Indent']
doc1 = cdr.filterDoc('guest', filters, doc = v1Xml.encode('utf-8'))
doc2 = cdr.filterDoc('guest', filters, doc = v2Xml.encode('utf-8'))
if not doc1[0]: cdrcgi.bail(doc1[1])
if not doc2[0]: cdrcgi.bail(doc2[1])
fn1 = "%d-%s-%s.xml" % (docId, version1, server1)
fn2 = "%d-%s-%s.xml" % (docId, version2, server2)
open(fn1, "w").write(doc1[0])
open(fn2, "w").write(doc2[0])
result = runCommand("diff -au %s %s" % (fn1, fn2))
report = cgi.escape(result.output)
cleanup(workDir)
title = "Differences between versions %s and %s for CDR%010d" % (version1,
                                                                 version2,
                                                                 docId)
print """\
Content-type: text/html; enctype=utf-8

<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>%s</title>
 </head>
 <body>
  <h3>%s</h3>
  <pre>%s</pre>
 </body>
</html>""" % (title, title, report)
