############
# CGI script invoked by the Big Brother system monitor to determine if
# the CDR server is up and responding properly.
#
# If error, reports to default log file (debug.log) and to web client.
############

import cdr

def report(what):
    print("""\
Content-type: text/plain

CDR %s""" % what)

# Uncomment if needed
# cdr.logwrite("cdrping called")
try:
    response = cdr.getDoctypes('guest')
    if type(response) in (str, unicode):
        cdr.logwrite("cdrping getDoctypes error: %s" % response)
        report("CORRUPT")
    else:
        report("OK")
except Exception as e:
    cdr.logwrite("cdrping getDoctypes exception type=%s  value=%s" %
                 (type(e), e))
    report("UNAVAILABLE")
