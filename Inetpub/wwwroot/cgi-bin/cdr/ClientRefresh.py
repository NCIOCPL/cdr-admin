#----------------------------------------------------------------------
#
# $Id$
#
# Web service for keeping CDR client files up to date.
#
# OCECDR-4006: Add support for using checksums instead of time stamps.
#
#----------------------------------------------------------------------
import base64
import cdr
import datetime
import lxml.etree as etree
import os
import sys
import tempfile
import WebService

WebService.USE_ETREE = True
STANDALONE = False
LOG_PATH = cdr.DEFAULT_LOGDIR + "/ClientRefresh.log"
LOG_LEVEL = 1

#----------------------------------------------------------------------
# Base class for Ticket and File classes, supporting check for match
# based on checksums (if present) or time stamps (otherwise). Also
# checks for matching hosts for tickets.
#----------------------------------------------------------------------
class ComparableNode:
    def __init__(self):
        self.host = self.checksum = self.timestamp = None
    def __eq__(self, other):
        if self.host != other.host:
            return False
        if self.checksum is None or other.checksum is None:
            return self.timestamp == other.timestamp
        return self.checksum == other.checksum
    def __ne__(self, other):
        return not self.__eq__(other)

#----------------------------------------------------------------------
# Object representing the header for a manifest for CDR client files.
# Contains identification of the server to which the manifest's file
# belong, the date/time the manifest was last built, the application
# used to build the manifest, and who invoked that program.  The
# server and timestamp of the header are compared with those in the
# client's copy of the manifest to detect whether any changes have
# occurred in the client file set since that last time the client
# updated its files.
#
# 2015-12-07: Add support for using checksums instead of time stamps.
#----------------------------------------------------------------------
class Ticket(ComparableNode):
    def __init__(self, node):
        ComparableNode.__init__(self)
        self.application = self.author = None
        for child in node:
            if child.tag == "Application":
                self.application = child.text.strip()
            elif child.tag == "Host":
                self.host = child.text.strip()
            elif child.tag == "Author":
                self.author = child.text.strip()
            elif child.tag == "Checksum":
                self.checksum = child.text.strip()
            elif child.tag == "Timestamp":
                self.timestamp = child.text.strip()

#----------------------------------------------------------------------
# Object representing one of the files in the CDR client file set.
# Data members for the pathname ("name") and modification date/time
# ("timestamp") are carried in the object.
#
# 2015-12-07: Add support for using checksums instead of time stamps.
#----------------------------------------------------------------------
class File(ComparableNode):
    def __init__(self, node):
        ComparableNode.__init__(self)
        self.name = None
        for child in node:
            if child.tag == "Name":
                self.name = child.text.strip()
            elif child.tag == "Checksum":
                self.checksum = child.text.strip()
            elif child.tag == "Timestamp":
                self.timestamp = child.text.strip()

#----------------------------------------------------------------------
# Object representing the list of files in the CDR client file set,
# along with a header ("ticket") for the list.
#----------------------------------------------------------------------
class Manifest:
    def __init__(self, node, include_file_list=True):
        self.ticket = None
        self.files = []
        for child in node:
            if child.tag == "Ticket":
                self.ticket = Ticket(child)
            elif child.tag == "FileList" and include_file_list:
                for grandchild in child:
                    if grandchild.tag == "File":
                        self.files.append(File(grandchild))

#----------------------------------------------------------------------
# Parse the server's copy of the XML document containing the list of
# CDR client files and the header for the list.
#----------------------------------------------------------------------
def load_server_manifest(include_file_list=True):
    tree = etree.parse(cdr.MANIFEST_PATH)
    return Manifest(tree.getroot(), include_file_list)

#----------------------------------------------------------------------
# Compare the header for the server's copy of the manifest for CDR
# client files with the copy of the manifest header sent by the
# client machine.  Send a response to the client indicating whether
# the client file set has changed since the last time this client
# checked.  The response from the server consists of an XML document
# containing the single element Current, whose text content is
# "Y" if the client's set is up to date, or "N" otherwise.
#----------------------------------------------------------------------
def check_ticket(client_ticket):
    server_ticket = load_server_manifest(include_file_list=False).ticket
    debug_log("client_ticket.host: %s" % client_ticket.host, 2)
    debug_log("server_ticket.host: %s" % server_ticket.host, 2)
    debug_log("client_ticket.checksum: %s" % client_ticket.checksum, 2)
    debug_log("server_ticket.checksum: %s" % server_ticket.checksum, 2)
    debug_log("client_ticket.timestamp: %s" % client_ticket.timestamp, 2)
    debug_log("server_ticket.timestamp: %s" % server_ticket.timestamp, 2)
    response = etree.Element("Current")
    response.text = (client_ticket == server_ticket) and "Y" or "N"
    return WebService.Response(response)

#----------------------------------------------------------------------
# Create a compressed archive containing the new and/or modified files
# which this client needs in order to bring its set in sync with the
# set on the server.  Return the archive as an in-memory string of bytes.
# Retains the copy of the archive on the server's disk if the debugging
# level is 2 or more.  The dependency on the external "zip.exe" command
# is unfortunate, but the alternatives are even worse.  The built-in
# Python zipfile module does not retain the exact number of seconds
# in the files' timestamps (rounding instead to even seconds), and
# using the more robust tar format would introduce the need to have
# tar and bzip2 (with supporting libraries) installed on the client.
#----------------------------------------------------------------------
def build_zip_file(file_names):
    base_name = tempfile.mktemp()
    zip_name  = base_name + ".zip"
    list_name = base_name + ".txt"
    list_file = file(list_name, "w")
    for name in file_names:
        list_file.write("%s\n" % name)
    list_file.close()
    os.chdir(cdr.CLIENT_FILES_DIR)
    result = cdr.runCommand("d:\\bin\\zip -@ %s < %s" % (zip_name, list_name))
    debug_log("Creating %s" % zip_name)
    if result.code:
        msg = "zip failure code %d (%s)" % (result.code, result.output)
        debug_log(msg)
        raise msg
    zip_file = file(zip_name, "rb")
    zip_bytes = zip_file.read()
    zip_file.close()
    if LOG_LEVEL < 2:
        os.unlink(list_name)
        os.unlink(zip_name)
        debug_log("saved zip file as %s" % zip_name)
    return zip_bytes

#----------------------------------------------------------------------
# Compare the client's copy of the manifest for CDR client files with
# the server's copy and build two lists of file pathnames, one for
# files which are new or changed since the client's last file refresh,
# and the second for files which are on the client's machine, but
# are no longer in the current set of CDR client files.  Return a
# response to the client consisting of an XML document whose top-
# level element is "Updates", with optional child elements of "ZipFile"
# (containing the base64-encoded bytes for the compressed archived of
# new and/or changed files needed by the client) and Delete (containing
# one or more File grandchild elements, one for each client file
# which needs to be removed).
#----------------------------------------------------------------------
def make_delta(client_manifest):
    server_manifest = load_server_manifest()
    client_files = {}
    server_files = {}
    to_be_installed = []
    to_be_deleted = []
    for f in client_manifest.files:
        client_files[f.name.upper()] = f
    for f in server_manifest.files:
        server_files[f.name.upper()] = f
    for key in server_files:
        serverFile = server_files[key]
        if key not in client_files:
            debug_log("adding new client file %s" % serverFile.name, 3)
            to_be_installed.append(serverFile.name)
        elif client_files[key] != serverFile:
            debug_log("adding changed client file %s" % serverFile.name, 3)
            to_be_installed.append(serverFile.name)
    for key in client_files:
        if key not in server_files:
            name = client_files[key].name
            debug_log("client file %s to be deleted" % name)
            to_be_deleted.append(name)
    updates = etree.Element("Updates")
    if to_be_installed:
        debug_log("sending %d files to be installed" % len(to_be_installed), 2)
        zip_file = base64.encodestring(build_zip_file(to_be_installed))
        etree.SubElement(updates, "ZipFile", encoding="base64").text = zip_file
    if to_be_deleted:
        debug_log("%d files will be removed" % len(to_be_deleted), 2)
        deletions = etree.SubElement(updates, "Delete")
        for name in to_be_deleted:
            etree.SubElement(deletions, "File").text = name
    return WebService.Response(updates)

#----------------------------------------------------------------------
# Optionally (depending on the logging level specified by the caller,
# compared with that set for this run of the program) append a log entry
# to the log for this program.  Prepend a date/time stamp string to
# the entry.
#----------------------------------------------------------------------
def debug_log(what, logLevel=1):
    if logLevel <= LOG_LEVEL:
        try:
            log_file = file(LOG_PATH, "a")
            now = str(datetime.datetime.now())[:19]
            log_file.write("%s: %s\n" % (now, what))
            log_file.close()
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
    if len(sys.argv) > 1 and sys.argv[1] == "--standalone":
        STANDALONE = True
    try:
        request = WebService.Request(STANDALONE, debug_log)
        LOG_LEVEL = request.logLevel
        debug_log("%s request from %s" % (request.type, request.client))
        debug_log("Request body:\n%s" % request.message, 3)
        if request.type == "Ticket":
            response = check_ticket(Ticket(request.doc))
        elif request.type == "Manifest":
            response = make_delta(Manifest(request.doc))
        else:
            response = WebService.ErrorResponse("Don't understand %s" %
                                                request.type)
    except Exception, e:
        response = WebService.ErrorResponse(str(e))
    debug_log("Response:\n%s\n" % response.body, 3)
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
