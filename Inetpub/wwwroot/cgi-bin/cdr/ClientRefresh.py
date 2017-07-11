#----------------------------------------------------------------------
#
# Web service for keeping CDR client files up to date.
#
# OCECDR-4006: Add support for using checksums instead of time stamps.
# OCECDR-4083: Login errors when switching between tiers.
# OCECDR-4265: Move glossifier service to Windows
#
#----------------------------------------------------------------------
from argparse import ArgumentParser
import base64
import datetime
import logging
import os
import sys
import tempfile
from lxml import etree
import cdr
import WebService

class Control:
    STANDALONE = False
    logger = cdr.Logging.get_logger("ClientRefresh")

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
    Control.logger.debug("client_ticket.host: %s", client_ticket.host, 2)
    Control.logger.debug("server_ticket.host: %s", server_ticket.host, 2)
    Control.logger.debug("client_ticket.checksum: %s", client_ticket.checksum)
    Control.logger.debug("server_ticket.checksum: %s" % server_ticket.checksum)
    Control.logger.debug("client_ticket.timestamp: %s", client_ticket.timestamp)
    Control.logger.debug("server_ticket.timestamp: %s", server_ticket.timestamp)
    response = etree.Element("Current")
    response.text = (client_ticket == server_ticket) and "Y" or "N"
    return WebService.Response(response, Control.logger)

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
    Control.logger.debug("Creating %s", zip_name)
    if result.code:
        msg = "zip failure code %d (%s)" % (result.code, result.output)
        Control.logger.debug(msg)
        raise msg
    zip_file = file(zip_name, "rb")
    zip_bytes = zip_file.read()
    zip_file.close()
    Control.logger.debug("saved zip file as %r", zip_name)
    if Control.logger.level != logging.DEBUG:
        os.unlink(list_name)
        os.unlink(zip_name)
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
    manifest_name = None
    for f in client_manifest.files:
        client_files[f.name.upper()] = f
    for f in server_manifest.files:
        server_files[f.name.upper()] = f
    for key in server_files:
        serverFile = server_files[key]
        if "CDRMANIFEST.XML" in key:
            manifest_name = serverFile.name
        if key not in client_files:
            Control.logger.debug("adding new client file %s", serverFile.name)
            to_be_installed.append(serverFile.name)
        elif client_files[key] != serverFile:
            Control.logger.debug("adding changed client file %s",
                                 serverFile.name)
            to_be_installed.append(serverFile.name)
    for key in client_files:
        if key not in server_files:
            name = client_files[key].name
            Control.logger.debug("client file %s to be deleted", name)
            to_be_deleted.append(name)
    updates = etree.Element("Updates")
    if to_be_installed:
        if manifest_name and manifest_name not in to_be_installed:
            to_be_installed.append(manifest_name)
        Control.logger.debug("sending %d files to be installed",
                             len(to_be_installed))
        zip_file = base64.encodestring(build_zip_file(to_be_installed))
        etree.SubElement(updates, "ZipFile", encoding="base64").text = zip_file
    if to_be_deleted:
        Control.logger.debug("%d files will be removed", len(to_be_deleted))
        deletions = etree.SubElement(updates, "Delete")
        for name in to_be_deleted:
            etree.SubElement(deletions, "File").text = name
    return WebService.Response(updates, Control.logger)

#----------------------------------------------------------------------
# Entry point for the service's program.  Catch the client's request,
# parse it, determine which command was sent, and pass the request
# to the appropriate handler function.
#----------------------------------------------------------------------
def main():
    parser = ArgumentParser()
    parser.add_argument("--standalone", action="store_true")
    parser.add_argument("--debug", action="store_true")
    opts = parser.parse_args()
    if opts.standalone:
        Control.STANDALONE = True
    if opts.debug:
        Control.logger.setLevel(logging.DEBUG)
    try:
        request = WebService.Request(Control.STANDALONE, Control.logger)
        if request.logLevel > 1:
            Control.logger.setLevel(logging.DEBUG)
        Control.logger.info("%s request from %s", request.type, request.client)
        Control.logger.debug("Request body:\n%s", request.message)
        if request.type == "Ticket":
            response = check_ticket(Ticket(request.doc))
        elif request.type == "Manifest":
            response = make_delta(Manifest(request.doc))
        else:
            error = "Don't understand %r" % request.type
            response = WebService.ErrorResponse(error, Control.logger)
    except Exception, e:
        response = WebService.ErrorResponse(str(e), Control.logger)
    Control.logger.debug("Response:\n%s\n", response.body)
    if Control.STANDALONE:
        sys.stdout.write(response.body)
    else:
        response.send()

#----------------------------------------------------------------------
# Allow this to be loaded as a module, without doing any processing
# until explicitly requested.
#----------------------------------------------------------------------
if __name__== "__main__":
    main()
