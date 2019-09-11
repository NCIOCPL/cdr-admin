#----------------------------------------------------------------------
# Returns archive of print files from a mailer job.
#----------------------------------------------------------------------
import cgi, sys

#----------------------------------------------------------------------
# Set the form variables.
#----------------------------------------------------------------------
fields   = cgi.FieldStorage()
jobId    = fields and fields.getvalue('job') or None
if not jobId:
    print("Content-type: text/plain\n")
    print("FAILURE: Missing required job parameter\n")
    sys.exit(0)

name = "d:/cdr/Output/Mailers/PrintFilesForJob%s.tar.bz2" % jobId
try:
    fobj = open(name, "rb")
except Exception as e:

    # Fall back on the old location for mailer output.
    name2 = "d:/cdr/mailers/output/PrintFilesForJob%s.tar.bz2" % jobId
    try:
        fobj = file(name2, "rb")
    except:
        print("Content-type: text/plain\n")
        print("FAILURE FETCHING PRINT FILES FOR JOB %s:" % jobId)
        print(str(e))
        sys.exit(0)

import msvcrt, os
msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
bytes = fobj.read()
sys.stdout.write("Content-type: application/binary\n\n")
sys.stdout.write(bytes)
