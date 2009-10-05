#----------------------------------------------------------------------
#
# $Id: FilterDiffs.py,v 1.2 2007-11-03 14:15:07 bkline Exp $
#
# Compare filters between two servers.
#
# $Log: not supported by cvs2svn $
# Revision 1.1  2002/09/11 21:11:57  bkline
# New report to compare all filters between two specified servers.
#
#----------------------------------------------------------------------

import cdr, cdrdb, cgi, cdrcgi, os, tempfile, re

#----------------------------------------------------------------------
# Get the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
server1  = fields and fields.getvalue('s1')
server2  = fields and fields.getvalue('s2')
pattern  = re.compile("diff -aur %s/@@MARK@@(.*?)@@MARK@@" % server1)

if not server1 or not server2:
    cdrcgi.bail("Must specify parameters s1 and s2")


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
# Get the filters from one of the two servers.
#----------------------------------------------------------------------
def getFilters(tmpDir, server):
    try: os.mkdir(server)
    except: 
        cleanup(tmpDir)
        cdrcgi.bail("Cannot create directory %s" % server)
    try:
        conn = cdrdb.connect('CdrGuest', dataSource = server)
        curs = conn.cursor()
        curs.execute("""\
            SELECT d.title, d.xml
              FROM document d
              JOIN doc_type t
                ON t.id = d.doc_type
             WHERE t.name = 'Filter'""")
        rows = curs.fetchall()
    except:
        cleanup(tmpDir)
        cdrcgi.bail('Database failure on %s: %s' % (server, info[1][0]))
    for row in rows:
        try:
            title = row[0].replace(" ", "@@SPACE@@") \
                          .replace(":", "@@COLON@@") \
                          .replace("/", "@@SLASH@@") \
                          .replace("*", "@@STAR@@")
            xml = row[1].replace("\r", "")
            filename = "%s/@@MARK@@%s@@MARK@@" % (server, title)
            open(filename, "w").write(xml.encode('utf-8'))
        except:
            cleanup(tmpDir)
            cdrcgi.bail("Failure writing %s" % filename);

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
# Undo our homemade encoding.
#----------------------------------------------------------------------
def unEncode(str):
    return str.replace("@@SPACE@@", " ") \
              .replace("@@COLON@@", ":") \
              .replace("@@SLASH@@", "/") \
              .replace("@@STAR@@", "*")  \
              .replace("@@MARK@@", "")
 
#----------------------------------------------------------------------
# Create a banner for the report on a single filter.
#----------------------------------------------------------------------
def makeBanner(name):
    line = "*" * 79 + "\n"
    leftOver = 77 - len(name)
    if leftOver > 0:
        leftHalf = leftOver / 2
        rightHalf = leftOver - leftHalf
        middleLine = "%s %s %s\n" % ("*" * leftHalf, name, "*" * rightHalf)
    else:
        middleLine = name + "\n"
    return "\n\n%s%s%s\n" % (line * 2, middleLine, line * 2)

#----------------------------------------------------------------------
# Get the filters.
#----------------------------------------------------------------------
workDir = makeTempDir()
getFilters(workDir, server1)
getFilters(workDir, server2)

#----------------------------------------------------------------------
# Compare the filters.
#----------------------------------------------------------------------
result  = runCommand("diff -aur %s %s" % (server1, server2))
lines   = result.output.splitlines()
for i in range(len(lines)):
    match = pattern.match(lines[i])
    if match:
        lines[i] = makeBanner(unEncode(match.group(1)))
report = cgi.escape(unEncode("\n".join(lines)))
cleanup(workDir)

print """\
Content-type: text/html; charset: utf-8

<!DOCTYPE HTML PUBLIC '-//IETF//DTD HTML//EN'>
<html>
 <head>
  <title>Filter Comparison Results</title>
 </head>
 <body>
  <h3>The following filters differ between %s and %s</h3>
  <pre>%s</pre>
 </body>
</html>""" % (server1, server2, report)
