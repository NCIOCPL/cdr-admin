#----------------------------------------------------------------------
#
# $Id$
#
# Page with links to a set of PDQ Board Member Mailers.
#
#----------------------------------------------------------------------
import cdrdb, cdrcgi, cgi, os, sys

#----------------------------------------------------------------------
# Look for the mailer job first in the new location, then in the old.
#----------------------------------------------------------------------
def findJob(job):
    bases = ("d:/cdr/Output/Mailers", "d:/cdr/Mailers/Output")
    for base in bases:
        dirName = "%s/Job%s-r" % (base, job)
        if os.path.isdir(dirName):
            return dirName
    cdrcgi.bail("Unable to find output for mailer job %s" % job)

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields    = cgi.FieldStorage()
session   = cdrcgi.getSession(fields) or "guest"
title     = "CDR Administration"
section   = "Board Member Letters"
job       = fields and fields.getvalue("job") or cdrcgi.bail("Job required")
fileName  = fields and fields.getvalue("file") or None
script    = "GetBoardMemberLetters.py"
dirName   = findJob(job)
header    = cdrcgi.header(title, title, section, script)

if fileName:
    import msvcrt
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    f = open("%s/%s" % (dirName, fileName), "rb")
    bytes = f.read()
    f.close
    sys.stdout.write("Content-Type: application/rtf\r\n")
    sys.stdout.write("Content-Length: %d\r\n" % len(bytes))
    sys.stdout.write("Content-Disposition: attachment; filename=%s\r\n\r\n" %
                     fileName)
    sys.stdout.write(bytes)
    sys.exit(0)

html = header + """\
<h2>PDQ Board Member Letters for Job %s</h2>
<ul>
""" % job
for name in os.listdir(dirName):
    if name.endswith('.rtf') and not name[0] == '~':
        html += """\
 <li><a href='%s?job=%s&file=%s'>%s</a></li>
""" % (script, job, name, name)
cdrcgi.sendPage(html + """\
</ul>
</body>
</html>""")
