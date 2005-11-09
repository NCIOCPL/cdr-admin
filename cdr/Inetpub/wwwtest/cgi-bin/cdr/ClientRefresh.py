#----------------------------------------------------------------------
#
# $Id: ClientRefresh.py,v 1.1 2005-11-09 00:00:16 bkline Exp $
#
# Web service for keeping CDR client files up to date.
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------
import WebService, cdr, os, sys, xml.dom.minidom, tempfile, base64, time

STANDALONE = False
LOG_PATH   = cdr.DEFAULT_LOGDIR + '/ClientRefresh.log'
LOG_LEVEL  = 1

#----------------------------------------------------------------------
# Object representing the header for a manifest for CDR client files.
# Contains identification of the server to which the manifest's file
# belong, the date/time the manifest was last built, the application
# used to build the manifest, and who invoked that program.  The
# server and timestamp of the header are compared with those in the
# client's copy of the manifest to detect whether any changes have
# occurred in the client file set since that last time the client
# updated its files.
#----------------------------------------------------------------------
class Ticket:
    def __init__(self, node):
        self.application = None
        self.timestamp   = None
        self.host        = None
        self.author      = None
        for child in node.childNodes:
            if child.nodeName == 'APPLICATION':
                self.application = cdr.getTextContent(child).strip()
            elif child.nodeName == 'TIMESTAMP':
                self.timestamp = cdr.getTextContent(child).strip()
            elif child.nodeName == 'HOST':
                self.host = cdr.getTextContent(child).strip()
            elif child.nodeName == 'AUTHOR':
                self.author = cdr.getTextContent(child).strip()

#----------------------------------------------------------------------
# Object representing one of the files in the CDR client file set.
# Data members for the pathname ('name') and modification date/time
# ('timestamp') are carried in the object.
#----------------------------------------------------------------------
class FileWithTimestamp:
    def __init__(self, node):
        self.name      = None
        self.timestamp = None
        for child in node.childNodes:
            if child.nodeName == 'NAME':
                self.name = cdr.getTextContent(child).strip()
            elif child.nodeName == 'TIMESTAMP':
                self.timestamp = cdr.getTextContent(child).strip()

#----------------------------------------------------------------------
# Object representing the list of files in the CDR client file set,
# along with a header ('ticket') for the list.
#----------------------------------------------------------------------
class Manifest:
    def __init__(self, node, includeFilelist = True):
        self.ticket  = None
        self.files   = []
        for child in node.childNodes:
            if child.nodeName == 'TICKET':
                self.ticket = Ticket(child)
            elif child.nodeName == 'FILELIST' and includeFilelist:
                for grandchild in child.childNodes:
                    if grandchild.nodeName == 'FILE':
                        self.files.append(FileWithTimestamp(grandchild))

#----------------------------------------------------------------------
# Parse the server's copy of the XML document containing the list of
# CDR client files and the header for the list.
#----------------------------------------------------------------------
def loadServerManifest(includeFilelist = True):
    dom = xml.dom.minidom.parse(cdr.MANIFEST_PATH)
    return Manifest(dom.documentElement, includeFilelist)
    
#----------------------------------------------------------------------
# Compare the header for the server's copy of the manifest for CDR
# client files with the copy of the manifest header sent by the
# client machine.  Send a response to the client indicating whether
# the client file set has changed since the last time this client
# checked.  The response from the server consists of an XML document
# containing the single element VALIDATION, whose text content is
# 'ACK' if the client's set is up to date, or 'NAK' otherwise.
#----------------------------------------------------------------------
def checkTicket(clientTicket):
    serverTicket = loadServerManifest(includeFilelist = False).ticket
    debugLog("clientTicket.host: %s" % clientTicket.host, 2)
    debugLog("serverTicket.host: %s" % serverTicket.host, 2)
    debugLog("clientTicket.timestamp: %s" % clientTicket.timestamp, 2)
    debugLog("serverTicket.timestamp: %s" % serverTicket.timestamp, 2)
    ackOrNak = 'ACK'
    if clientTicket.host != serverTicket.host:
        ackOrNak = 'NAK'
    elif clientTicket.timestamp != serverTicket.timestamp:
        ackOrNak = 'NAK'
    return WebService.Response("<VALIDATION>%s</VALIDATION>" % ackOrNak)

#----------------------------------------------------------------------
# Create a compressed archive containing the new and/or modified files
# which this client needs in order to bring its set in sync with the
# set on the server.  Store the archive on the server's disk and return
# the name of the file to the caller.
#----------------------------------------------------------------------
def buildZipfile(fileNames):
    listName = tempfile.mktemp()
    listFile = open(listName, "w")
    for name in fileNames:
        listFile.write("%s\n" % name)
    listFile.close()
    zipName = tempfile.mktemp() + ".zip"
    os.chdir(cdr.CLIENT_FILES_DIR)
    os.system("zip -@ %s < %s > %s.err" % (zipName, listName, zipName))
    debugLog("error file is %s.err" % zipName)
    if LOG_LEVEL < 2:
        os.unlink(listName)
    return zipName
    
#----------------------------------------------------------------------
# Compare the client's copy of the manifest for CDR client files with
# the server's copy and build two lists of file pathnames, one for
# files which are new or changed since the client's last file refresh,
# and the second for files which are on the client's machine, but
# are no longer in the current set of CDR client files.  Return a
# response to the client consisting of an XML document whose top-
# level element is 'DELTA', with optional child elements of 'ZIPFILE'
# (containing the name of the compressed archive which is created
# here for new and/or changed files to be sent to the client in
# a subsequent client-server exchange) and 'DELETE' (containing
# one or more FILE grandchild elements, one for each client file
# which needs to be removed).
#----------------------------------------------------------------------
def makeDelta(clientManifest):
    serverManifest = loadServerManifest()
    clientFiles    = {}
    serverFiles    = {}
    toBeInstalled  = []
    toBeDeleted    = []
    for f in clientManifest.files:
        clientFiles[f.name.upper()] = f
    for f in serverManifest.files:
        serverFiles[f.name.upper()] = f
    for key in serverFiles:
        serverFile = serverFiles[key]
        if key not in clientFiles:
            debugLog("adding new client file %s" % serverFile.name, 3)
            toBeInstalled.append(serverFile.name)
        elif clientFiles[key].timestamp != serverFile.timestamp:
            debugLog("adding changed client file %s" % serverFile.name, 3)
            toBeInstalled.append(serverFile.name)
    for key in clientFiles:
        if key not in serverFiles:
            name = clientFiles[key].name
            debugLog("client file %s to be deleted" % name)
            toBeDeleted.append(name)
    lines = ["<DELTA>"]
    if toBeInstalled:
        debugLog("sending %d files to be installed" % len(toBeInstalled), 2)
        lines.append("<ZIPFILE>%s</ZIPFILE>" % buildZipfile(toBeInstalled))
    if toBeDeleted:
        debugLog("%d files will be removed" % len(toBeDeleted), 2)
        lines.append("<DELETE>")
        for name in toBeDeleted:
            lines.append("<FILE>%s</FILE>" % name)
        lines.append("</DELETE>")
    lines.append("</DELTA>")
    return WebService.Response("".join(lines))

#----------------------------------------------------------------------
# Send the compressed archive of new and/or modified files to the
# client.
#----------------------------------------------------------------------
def sendZipfile(zipName):
    f = open(zipName, "rb")
    zipData = f.read()
    f.close()
    response = WebService.Response("<ZIPFILE><FNAME>%s</FNAME>"
                                   "<DATA encoding='base64'>%s</DATA>"
                                   "</ZIPFILE>" %
                                   (zipName, base64.encodestring(zipData)))
    if LOG_LEVEL < 2:
        os.unlink(zipName)
        os.unlink(zipName + ".err")
    return response

#----------------------------------------------------------------------
# Optionally (depending on the logging level specified by the caller,
# compared with that set for this run of the program) append a log entry
# to the log for this program.  Prepend a date/time stamp string to
# the entry.
#----------------------------------------------------------------------
def debugLog(what, logLevel = 1):
    if logLevel >= LOG_LEVEL:
        try:
            logFile = file(LOG_PATH, 'a')
            now     = time.strftime("%Y-%m-%d %H:%M:%S")
            logFile.write("%s: %s\n" % (now, what))
            logFile.close()
        except:
            if STANDALONE:
                raise

#----------------------------------------------------------------------
# Entry point for the service's program.  Catch the client's request,
# parse it, determine which command was sent, and pass the request
# to the appropriate handler function.
#----------------------------------------------------------------------
def main():
    global LOG_LEVEL
    LOG_LEVEL = 1
    global STANDALONE
    if len(sys.argv) > 1 and sys.argv[1] == '--standalone':
        STANDALONE = True
    try:
        request = WebService.Request(STANDALONE, debugLog)
        LOG_LEVEL = request.logLevel
        debugLog("%s request from %s" % (request.type, request.client))
        debugLog("Request body:\n%s" % request.message, 3)
        if request.type == "TICKET":
            response = checkTicket(Ticket(request.doc))
        elif request.type == "MANIFEST":
            response = makeDelta(Manifest(request.doc))
        elif request.type == "ZIPREQ":
            response = sendZipfile(cdr.getTextContent(request.doc))
        else:
            response = WebService.ErrorResponse("Don't understand %s" %
                                                request.type)
    except Exception, e:
        response = WebService.ErrorResponse(str(e))
    debugLog("Response:\n%s\n" % response.body, 3)
    if STANDALONE:
        sys.stdout.write(response.body)
    else:
        response.send()

#----------------------------------------------------------------------
# Allow this to be loaded as a module, without doing any processing
# until explicitly requested.
#----------------------------------------------------------------------
if __name__== "__main__":
    main()
