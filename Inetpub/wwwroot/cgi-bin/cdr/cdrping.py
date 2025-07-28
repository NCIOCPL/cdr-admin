#!/usr/bin/env python

############
# CGI script invoked by the Big Brother system monitor to determine if
# the CDR server is up and responding properly.
#
# If error, reports to default log file (cdr-client.log) and to web client.
############

import cdr


def report(what):
    print(f"""\
Content-type: text/plain
X-Content-Type-Options: nosniff

CDR {what}""")


cdr.LOGGER.debug("cdrping called")

try:
    response = cdr.getDoctypes('guest')
    if isinstance(response, (str, bytes)):
        cdr.LOGGER.warning("cdrping getDoctypes error: %s", response)
        report("CORRUPT")
    else:
        report("OK")
except Exception:
    cdr.LOGGER.exception("CDR ping failure")
    report("UNAVAILABLE")
