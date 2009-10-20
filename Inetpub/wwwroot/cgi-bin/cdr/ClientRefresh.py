#----------------------------------------------------------------------
#
# $Id$
#
# Web service for keeping CDR client files up to date.
#
# $Log: not supported by cvs2svn $
# Revision 1.2  2005/11/22 15:52:22  bkline
# Collapsed last two client-server exchanges into one; changed element
# names to conform more closely with standard usage in the CDR.
#
# Revision 1.1  2005/11/09 00:00:16  bkline
# Server to keep CDR clients up to date with the current set of client
# files.
#
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
            if child.nodeName == 'Application':
                self.application = cdr.getTextContent(child).strip()
            elif child.nodeName == 'Timestamp':
                self.timestamp = cdr.getTextContent(child).strip()
            elif child.nodeName == 'Host':
                self.host = cdr.getTextContent(child).strip()
            elif child.nodeName == 'Author':
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
            if child.nodeName == 'Name':
                self.name = cdr.getTextContent(child).strip()
            elif child.nodeName == 'Timestamp':
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
            if child.nodeName == 'Ticket':
                self.ticket = Ticket(child)
            elif child.nodeName == 'FileList' and includeFilelist:
                for grandchild in child.childNodes:
                    if grandchild.nodeName == 'File':
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
# containing the single element Current, whose text content is
# 'Y' if the client's set is up to date, or 'N' otherwise.
#----------------------------------------------------------------------
def checkTicket(clientTicket):
    serverTicket = loadServerManifest(includeFilelist = False).ticket
    debugLog("clientTicket.host: %s" % clientTicket.host, 2)
    debugLog("serverTicket.host: %s" % serverTicket.host, 2)
    debugLog("clientTicket.timestamp: %s" % clientTicket.timestamp, 2)
    debugLog("serverTicket.timestamp: %s" % serverTicket.timestamp, 2)
    if clientTicket.host != serverTicket.host:
        return WebService.Response("<Current>N</Current>")
    elif clientTicket.timestamp != serverTicket.timestamp:
        return WebService.Response("<Current>N</Current>")
    return WebService.Response("<Current>Y</Current>")

#----------------------------------------------------------------------
# Create a compressed archive containing the new and/or modified files
# which this client needs in order to bring its set in sync with the
# set on the server.  Return the archive as an in-memory string of bytes.
# Retains the copy of the archive on the server's disk if the debugging
# level is 2 or more.  The dependency on the external 'zip.exe' command
# is unfortunate, but the alternatives are even worse.  The built-in
# Python zipfile module does not retain the exact number of seconds
# in the files' timestamps (rounding instead to even seconds), and
# using the more robust tar format would introduce the need to have
# tar and bzip2 (with supporting libraries) installed on the client.
#----------------------------------------------------------------------
def buildZipfile(fileNames):
    baseName = tempfile.mktemp()
    zipName  = baseName + ".zip"
    listName = baseName + ".txt"
    listFile = file(listName, "w")
    for name in fileNames:
        listFile.write("%s\n" % name)
    listFile.close()
    os.chdir(cdr.CLIENT_FILES_DIR)
    result = cdr.runCommand("zip -@ %s < %s" % (zipName, listName))
    debugLog("Creating %s" % zipName) 
    if result.code:
        msg = "zip failure code %d (%s)" % (result.code, result.output)
        debugLog(msg)
        raise msg
    zipFile = file(zipName, 'rb')
    zipBytes = zipFile.read()
    zipFile.close()
    if LOG_LEVEL < 2:
        os.unlink(listName)
        os.unlink(zipName)
        debugLog("saved zipfile as %s" % zipName)
    return zipBytes
    
#----------------------------------------------------------------------
# Compare the client's copy of the manifest for CDR client files with
# the server's copy and build two lists of file pathnames, one for
# files which are new or changed since the client's last file refresh,
# and the second for files which are on the client's machine, but
# are no longer in the current set of CDR client files.  Return a
# response to the client consisting of an XML document whose top-
# level element is 'Updates', with optional child elements of 'ZipFile'
# (containing the base64-encoded bytes for the compressed archived of
# new and/or changed files needed by the client) and Delete (containing
# one or more File grandchild elements, one for each client file
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
    lines = ["<Updates>"]
    if toBeInstalled:
        debugLog("sending %d files to be installed" % len(toBeInstalled), 2)
        lines.append("<ZipFile encoding='base64'>%s</ZipFile>" %
                     base64.encodestring(buildZipfile(toBeInstalled)))
    if toBeDeleted:
        debugLog("%d files will be removed" % len(toBeDeleted), 2)
        lines.append("<Delete>")
        for name in toBeDeleted:
            lines.append("<File>%s</File>" % name)
        lines.append("</Delete>")
    lines.append("</Updates>")
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
    if logLevel <= LOG_LEVEL:
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
        if request.type == "Ticket":
            response = checkTicket(Ticket(request.doc))
        elif request.type == "Manifest":
            response = makeDelta(Manifest(request.doc))
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
