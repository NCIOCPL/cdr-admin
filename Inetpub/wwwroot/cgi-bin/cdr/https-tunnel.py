#----------------------------------------------------------------------
#
# $Id$
#
# Passthrough to tunnel CDR client-server traffic through HTTPS instead
# of running over custom port 2019.
#
# JIRA::OCECDR-3748
#
#----------------------------------------------------------------------
import cdr
import msvcrt
import os
import sys

msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
content_length = os.environ.get("CONTENT_LENGTH")
if content_length:
    request = sys.stdin.read(int(content_length))
else:
    request = sys.stdin.read()
try:
    response = cdr.sendCommands(request, timeout=600)
    print """\
Content-type: application/xml; charset=utf-8

%s""" % response.replace("\r", "")
except Exception, e:
    try:
        logfile = cdr.DEFAULT_LOGDIR + "/https-tunnel.log"
        cdr.logwrite("https-tunnel.py: %s" % e, logfile, True)
    except:
        pass
    sys.stdout.write("Status: 500 CDR not available\r\n\r\n")
