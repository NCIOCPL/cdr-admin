#----------------------------------------------------------------------
# $Id$
#
# Stub for SOAP interface to CDR from Cancer.gov.
#
# $Log: not supported by cvs2svn $
# Revision 1.4  2002/05/16 14:33:34  bkline
# Changed reply to include real date/time value.
#
# Revision 1.3  2002/04/16 22:43:25  bkline
# Fixed function name.
#
# Revision 1.2  2002/04/16 22:42:08  bkline
# Eliminated some unneeded imports.
#
# Revision 1.1  2002/04/16 22:06:06  bkline
# Stub SOAP server.  Does nothing but provide a harness for catching
# a client message and sending back a response.
#
#----------------------------------------------------------------------
import os, sys, time, msvcrt

#----------------------------------------------------------------------
# Send an XML SOAP message back to the client.
#----------------------------------------------------------------------
def sendMessage(msg):
    print """\
Content-type: text/xml

<?xml                  version = "1.0"
                      encoding = "UTF-8"?>
<env:Envelope        xmlns:env = "http://schemas.xmlsoap.org/soap/envelope/"
             env:encodingStyle = "http://schemas.xmlsoap.org/soap/encoding/">
 <env:Body>
%s
 </env:Body>
</env:Envelope>
""" % msg
    sys.exit(0)

#----------------------------------------------------------------------
# Send an error message back to the client.
#----------------------------------------------------------------------
def bailOut(msg, code = "Server", details = None):

    # Start the fault element
    fault = """\
  <env:Fault>
   <faultcode>env:%s</faultcode>
   <faultstring>%s</faultstring>
""" % (code, msg)

    # Add option details if specified.
    if details:
        fault += """
   <detail>
    <details>%s</details>
   </detail>
""" % details

    # Finish up and send it off.
    sendMessage("""\
   %s
  </env:Fault>
""" % fault)

#----------------------------------------------------------------------
# Gather in the client's message.
#----------------------------------------------------------------------
def readRequest():
    global contentLength
    requestMethod = os.getenv("REQUEST_METHOD")
    if not requestMethod:
        bailOut("Request method not specified")
    if requestMethod != "POST":
        bailOut("Request method should be POST; was %s" % requestMethod,
                "Client")
    contentLengthString = os.getenv("CONTENT_LENGTH")
    if not contentLengthString:
        bailOut("Content length not specified")
    try:
        contentLength = int(contentLengthString)
    except:
        bailOut("Invalid content length: %s" % contentLengthString)
    if contentLength < 1:
        bailOut("Invalid content length: %s" % contentLengthString)
    try:
        request = sys.stdin.read(contentLength)
    except:
        bailOut("Failure reading message")
    return request

#----------------------------------------------------------------------
# Catch the request and echo back a dummy response.
#----------------------------------------------------------------------
msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
request = readRequest()
file = open("d:/tmp/request.dump", "wb")
file.write(request)
file.close()
file = open("d:/tmp/params.dump", "w")
keys = os.environ.keys()
keys.sort()
for key in keys:
    file.write("%s=%s\n" % (key, os.environ[key]))
file.close()
sendMessage("""\
  <PubEventResp         system = "CDR"
                          when = "%s"
                       pubType = "Export"
                       docType = "Term"
                       lastJob = "287398"
                 contentLength = "%d"
                     bytesRead = "%d"/>
""" % (time.strftime("%Y-%m-%dT%H:%M:%S"), contentLength, len(request)))
