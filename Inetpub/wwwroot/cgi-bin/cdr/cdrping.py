############
# CGI script invoked by the Big Brother system monitor to determine if
# the CDR server is up and responding properly.
#
# If error, reports to default log file (debug.log) and to web client.
############

import cdr

def report(what):
    print(f"""\
Content-type: text/plain

CDR {what}""")

cdr.LOGGER.debug("cdrping called")

try:
    response = cdr.getDoctypes('guest')
    if isinstance(response, (str, bytes)):
        cdr.LOGGER.warning("cdrping getDoctypes error: %s", response)
        report("CORRUPT")
    else:
        report("OK")
except Exception as e:
    cdr.LOGGER.exception("CDR ping failure")
    report("UNAVAILABLE")
