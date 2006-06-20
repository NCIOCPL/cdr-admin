#----------------------------------------------------------------------
#
# $Id: GetMailerPrintFiles.py,v 1.1 2006-06-20 15:34:05 bkline Exp $
#
# Returns archive of print files from a mailer job.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import cgi, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
jobId    = fields and fields.getvalue('job') or None
if not jobId:
    print "Content-type: text/plain\n"
    print "FAILURE: Missing required job parameter\n"
    sys.exit(0)

name = "d:/cdr/mailers/output/PrintFilesForJob%s.tar.bz2" % jobId
try:
    fobj = file(name, "rb")
except Exception, e:
    print "Content-type: text/plain\n"
    print "FAILURE: error reading %s:\n%s" % (name, str(e))
    sys.exit(0)

import msvcrt, os
msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
bytes = fobj.read()
sys.stdout.write("Content-type: application/binary\n\n")
sys.stdout.write(bytes)
