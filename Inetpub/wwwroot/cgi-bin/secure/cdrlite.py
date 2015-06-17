#----------------------------------------------------------------------
# $Id$
# Extraction of just enough functionality from cdr.py to be able to
# connect to the CDR server over port 2019 and request a CDR login
# session. We haven't figured out all the details of what's going on,
# but with Windows authentication mode enforced on the cgi-bin/secure
# directory, IIS runs into one or both of the following problems,
# depending on the user account whose credentials are supplied for
# the script request:
#
#  * unable to load modules from %PYTHONPATH% (permissions problems?)
#  * unable to load the full cdr.py from anywhere (insufficient permission
#    to invoke the Windows CryptoGen API calls, which are used for
#    the random module (which is imported by the cgi module, which the
#    cdr module uses)
#
# See https://tracker.nci.nih.gov/browse/WEBTEAM-5879
#
# JIRA::OCECDR-3849
#----------------------------------------------------------------------
import lxml.etree as etree
import os
import socket
import struct
import time

SENDCMDS_TIMEOUT = 300
SENDCMDS_SLEEP = 3
SENDCMDS_HOST = "localhost"
SENDCMDS_PORT = 2019

#----------------------------------------------------------------------
# Send a set of commands to the CDR Server and return its response.
#----------------------------------------------------------------------
def sendCommands(commands):

    timeout = SENDCMDS_TIMEOUT
    port = SENDCMDS_PORT
    host = SENDCMDS_HOST

    # Connect to the CDR Server.
    connAttempts     = 0
    sendRecvAttempts = 0
    startTime        = time.time()
    endTime          = startTime + timeout

    # Run until logic raises exception or returns data
    while True:
        try:
            connAttempts += 1
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
        except:

            # Can we keep trying
            now = time.time()
            if now >= endTime:
                raise Exception("CDR server not available")

            # Keep trying
            sleepTime = SENDCMDS_SLEEP
            if now + sleepTime > endTime:
                sleepTime = int(endTime - now)
            time.sleep(sleepTime)
            continue

        # If we got here we have a connection
        try:
            # Send the commands to the server.
            sendRecvAttempts += 1
            sock.send(struct.pack('!L', len(commands)))
            sock.send(commands)

            # Read the server's response.
            (rlen,) = struct.unpack('!L', sock.recv(4))
            response = ''
            while len(response) < rlen:
                response = response + sock.recv(rlen - len(response))

            # We got the response.  We're done.  Return it to the caller
            break

        except:
            # The connection is almost certainly gone, but make sure
            try:
                sock.close()
            except:
                pass

            # Handle timeouts as above
            now = time.time()
            if now >= endTime:
                raise Exception("CDR server unavailable")
            sleepTime = SENDCMDS_SLEEP
            if now + sleepTime > endTime:
                sleepTime = int(endTime - now)
            time.sleep(sleepTime)
            continue

    # If we got here, we succeeded
    # Clean up and hand the server's response back to the caller.
    sock.close()
    return response

#----------------------------------------------------------------------
# Create CDR session for user whose NIH domain account has been vetted.
#----------------------------------------------------------------------
def login(userId):
    command_set = etree.Element("CdrCommandSet")
    command = etree.SubElement(command_set, "CdrCommand")
    logon = etree.SubElement(command, "CdrLogon")
    etree.SubElement(logon, "UserName").text = userId
    response = sendCommands(etree.tostring(command_set))
    tree = etree.XML(response)
    errors = tree.findall("CdrResponse/CdrLogonResp/Errors/Err")
    if errors:
        raise Exception([e.text for e in errors])
    return tree.find("CdrResponse/CdrLogonResp/SessionId").text
