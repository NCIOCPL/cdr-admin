import os, sys, xml.dom.minidom, cdr, msvcrt, cdrdb, xml.sax.saxutils

#----------------------------------------------------------------------
# Tell the client how to invoke the service.
#----------------------------------------------------------------------
def sendWsdl():
    f = open('d:/cdr/reports/aaciservice.wsdl')
    w = f.read()
    f.close()
    print "Content-type: text/xml\n"
    sys.stdout.write(w)
    sys.exit(0)

def fix(s):
    return xml.sax.saxutils.escape(s)

def getProtocols(term):
    pattern = 'http://bach.nci.nih.gov/cgi-bin/getProtocol.py?id=%d'
    conn = cdrdb.connect('CdrGuest')
    cursor = conn.cursor()
    cursor.execute("""\
        SELECT d.id, d.title, s.value, i.value
          FROM document d
          JOIN query_term s
            ON d.id = s.doc_id
          JOIN query_term i
            ON d.id = i.doc_id
         WHERE s.path = '/InScopeProtocol/ProtocolAdminInfo'
                      + '/CurrentProtocolStatus'
           AND i.path = '/InScopeProtocol/ProtocolIDs/PrimaryID/IDString'
           AND s.value IN ('Active', 'Approved-not yet active')
           AND d.title LIKE '%%%s%%'
      ORDER BY d.title""" % term)
    response = [u"""\
  <getProtocolsResponse xmlns='urn:uddi-aaci-org:protocols'>
   <getProtocolsResult>"""]
    row = cursor.fetchone()
    while row:
        protId = row[3] and fix(row[3]) or u""
        title  = row[1] and fix(row[1]) or u""
        status = row[2] and fix(row[2]) or u""
        url    = pattern % row[0]
        response.append(u"""\
    <Protocol>
     <prot_num>%s</prot_num>
     <prot_title>%s</prot_title>
     <prot_accrual_status>%s</prot_accrual_status>
     <prot_url>%s</prot_url>
    </Protocol>""" % (protId, title, status, url))
        row = cursor.fetchone()
    response.append(u"""\
   </getProtocolsResult>
  </getProtocolsResponse>""")
    return u"\n".join(response)

#----------------------------------------------------------------------
# Send an XML SOAP message back to the client.
#----------------------------------------------------------------------
def sendMessage(msg):
    response = u"""\
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
    sys.stdout.write(response.encode('utf-8'))
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
    requestMethod = os.getenv("REQUEST_METHOD")
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    if not requestMethod:
        bailOut("Request method not specified")
    if requestMethod != "POST":
        sendWsdl()
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
        raise
        bailOut("Failure reading message")
    return request

#----------------------------------------------------------------------
# Catch the request and extract the search string.
#----------------------------------------------------------------------
request = readRequest()
dom = xml.dom.minidom.parseString(request)
term = None
for node in dom.documentElement.childNodes:
    if node.localName == 'Body':
        for child in node.childNodes:
            if child.localName == 'getProtocols':
                for grandchild in child.childNodes:
                    if grandchild.localName == 'SearchString':
                        term = cdr.getTextContent(grandchild).strip()
if term is None:
    bailOut('incorrect request structure; consult WSDL document')

#----------------------------------------------------------------------
# Find matching protocols and return them.
#----------------------------------------------------------------------
response = getProtocols(term)
sendMessage(response)
#sendMessage(u"""\
#  <getProtocolsResponse xmlns='urn:uddi-aaci-org:protocols'>
##   <getProtocolsResult>
#    <Protocol>
#     <prot_num>ARC-3291</prot_num>
#     <prot_title>Test title</prot_title>
#     <prot_accrual_status>Active</prot_accrual_status>
#     <prot_url>http://bach.nci.nih.gov/cgi-bin/getProtocol.py?id=43521</prot_url>
#    </Protocol>
#   </getProtocolsResult>
#  </getProtocolsResponse>
#""")
