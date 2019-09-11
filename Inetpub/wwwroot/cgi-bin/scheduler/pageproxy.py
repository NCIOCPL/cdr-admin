"""
    Pass through proxy for HTTP requests.

    Allows requests sent to one server to be transparently serviced by a different
    server with a differnt base path.

    Configuration Points:
        PROXIED_URL_BASE    Base URL for the remote server. (Proxied pages need not
                            be on the same base path as the request, though it does
                            help if the HTML avoids paths beginning with a /.)

        PROXIED_PATH_PARAM  Name of the query string parameter (provided via a rewrite rule)
                            containg the path relative to PROXIED_URL_BASE which is to be
                            retrieved.

        SESSIONLESS_STEMS   List of path bases which do not require validation before
                            proxied.  Paths must NOT start a leading slash.  It is a
                            best practice for directory names to end with a slash to
                            avoid conflicts with partial file names.

        (Rarely modified items)

        CDR_SESSION_PARAM   The name of the query string parameter which contains the
                            CDR Session ID.

        SCHEDULER_PERMISSION_NAME   The name of the permission/action name used by the
                                    CDR to manage access to the scheduler.

        RESPONSE_CHUNK_SIZE Size of the largest chunk of data to transmit in a packet.
                            See https://bugs.python.org/issue11395.

        REQUEST_CHUNK_SIZE  Maximum number of bytes to read at a time
"""
import json
import logging
import logging.handlers
import os
import sys
import urlparse

import msvcrt # Windows-specific for setting binary output
import requests

import cdr


PROXIED_URL_BASE = 'http://localhost:8888/'
PROXIED_PATH_PARAM = 'path' # Query string param containing the
                            # URL to retrieve.

# Paths beginning with names in this list are not checked for a session.  All other paths are
# required to have a valid, logged in, session ID. (Note: Paths do NOT begin with a leading /.)
SESSIONLESS_STEMS = ["static/"]

CDR_SESSION_PARAM = "Session"

SCHEDULER_PERMISSION_NAME = "MANAGE SCHEDULER"

RESPONSE_CHUNK_SIZE = 32000       # HTTP chunk size for returns.
REQUEST_CHUNK_SIZE = 4096


# Configure logging for the entire module.
logging.basicConfig(level=logging.DEBUG,
                    filename='d:\\cdr\\Log\\pageproxy.log',
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)


# Set standard out to binary mode.  (Standard IN is reported as an invalid
# file descriptor, so it's deliberately left out.)
try:
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    #msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
except:
    logger.error('Error when setting output to binary.', exc_info=True)

class IncomingRequest(object):
    "Encapsulates the logic for gathering details of the incoming HTTP request."

    def __init__(self):
        self.form_data = IncomingRequest._get_form_data()
        self.query_params = IncomingRequest._get_query_params()
        self.verb = IncomingRequest._get_verb()
        self.remote_subpath = self._get_path_to_proxy()
        logger.debug("Proxying to path '%s'.", self.remote_subpath)

    @staticmethod
    def _get_form_data():
        "Retrieve request body as a raw blob of text."

        formdata = {}

        if "CONTENT_LENGTH" in os.environ:
            remaining = int(os.environ['CONTENT_LENGTH'])
            logger.debug("Reading '%d' bytes", remaining)
            rawString = '' # JSON blob.
            while remaining > 0:
                bitesize = min(remaining, REQUEST_CHUNK_SIZE)
                data = sys.stdin.read(bitesize)
                rawString += data
                remaining -= bitesize

                # Tricky bit. We have the JSON data as a blob of text. It shouldn't
                # be sent as an encoded string, wo first it has to be turned into
                # a proper JSON structure.
                formdata = json.loads(rawString.strip())

        logger.debug("Data: '%s'.", repr(formdata))
        return formdata

    @staticmethod
    def _get_query_params():
        "Retrieves parameters from the HTTP query string."
        query_string = ''
        if 'QUERY_STRING' in os.environ:
            query_string = os.environ['QUERY_STRING']

        args = urlparse.parse_qs(query_string, True)
        return args

    def _get_path_to_proxy(self):
        """
            Retrieves the path to be proxied from the query string parameter
            identified by the PROXIED_PATH_PARAM setting.
        """

        # Handle the possibility of future refactoring putting
        # this call ahead of query_params being set.
        if not hasattr(self, 'query_params'):
            self.query_params = IncomingRequest._get_query_params()

        path = ''
        if PROXIED_PATH_PARAM in self.query_params:
            for piece in self.query_params[PROXIED_PATH_PARAM]:
                path += piece
        return path

    @staticmethod
    def _get_verb():
        "Determine request type. (internal)"
        if 'REQUEST_METHOD' in os.environ:
            return os.environ['REQUEST_METHOD'].upper()
        else:
            return 'GET'

    def get_filtered_query_string(self):
        """
            Returns a copy of the query string, minus the parameter identified
            by the PROXIED_PATH_PARAM value.
        """
        # Make a shallow copy of the parameter data in order to leave the
        # original unaltered.
        queryData = self.query_params.copy()
        if PROXIED_PATH_PARAM in queryData:
            queryData.pop(PROXIED_PATH_PARAM)

        return queryData

    def may_be_proxied(self):
        """
            Reports whether the requested path is allowed to be proxied:

            Conditions for allowing proxying to occur are either:
                The requested path begins with one of the values contained in
                the SESSIONLESS_STEMS list.

                OR

                a) The request includes a 'Session' parameter.
                b) AND The session ID is valid.
                c) AND The user ID associated with the session is permitted to
                   access the scheduler.
        """

        path = self._get_path_to_proxy()

        proxyAllowed = False
        if IncomingRequest._path_is_unguarded(path):
            logger.debug("Path '%s' is not guarded.", path)
            proxyAllowed = True
        elif self._session_is_valid():
            logger.debug("A valid session was found.")
            proxyAllowed = True
        else:
            logger.debug("No authorization for this request.")
            proxyAllowed = False

        return proxyAllowed

    @staticmethod
    def _path_is_unguarded(path):
        """
            Checks whether the value of the 'path' parameter begins with a value which
            appears in the SESSIONLESS_STEMS list.
        """
        # Force the path to lowercase in order to ensure case insensitivity.
        if path:
            path = path.lower()

        unguarded = False
        for entry in SESSIONLESS_STEMS:
            if entry:
                entry = entry.lower()

            # Does the entry match the beginning of the path?
            if entry == path[:len(entry)]:
                logger.debug("Path '%s' matches exception '%s'", path, entry)
                unguarded = True
                break

        return unguarded

    def _session_is_valid(self):
        """
            Validates that:

            a) The request includes a 'Session' parameter.
            b) AND The session ID is valid.
            c) AND The user ID associated with the session is permitted to
               access the scheduler.
        """
        sessionIsValid = False

        if CDR_SESSION_PARAM in self.query_params:
            session = self.query_params[CDR_SESSION_PARAM]
            if isinstance(session, list):
                session = session[0]
            logger.debug("Validating Session '%s'", session)

            if cdr.canDo(session, SCHEDULER_PERMISSION_NAME):
                sessionIsValid = True

        return sessionIsValid

class Proxy(object):
    """
        Encapsulates the logic for requesting a page from the remote server.

        To create an instance
            proxy = Proxy(request)

        Where:

        request - An instance of IncomingRequest class. (i.e. the request
        that's being proxied.)

        base_url - The base URL for pages being request. At a minimum, this
        should be the remove server name, but may also include a path.
    """

    def __init__(self, incoming, base_url):
        if not isinstance(incoming, IncomingRequest):
            message = ("Parameter 'incoming' must be an instance of IncomingRequest. Got '%s' instead."
                       % type(incoming).__name__)
            logger.error(message)
            raise TypeError(message)
        self.incoming = incoming

        if base_url is None or (len(base_url.strip()) == 0):
            message = "Parameter base_url must be non-empty."
            logger.error(message)
            raise ValueError(message)

        self._base_url = base_url.strip()

    def get_remote_url(self):
        """
            Constructs the remote URL by concatenating the requested path from
            the incoming request with the base URL supplied to the Proxy object's
            __init__() function.
        """
        remote = self._base_url.strip()
        additional = self.incoming.remote_subpath

        endPos = len(remote) - 1
        if not remote[endPos] == '/':
            formatter = '%s/%s'
        else:
            formatter = '%s%s'

        # Only append if a subpath exists.
        if additional:
            remote = formatter % (remote, additional)

        return remote

    def _send_return(self, response):
        """
            Send the proxied response back to the orignal caller.
            This method terminates the script by calling sys.exit().
        """

        code = response.status_code

        # Report a 404 as a 404 and terminate, else pass the status.
        print("status: %s" % code)
        logger.debug("Return status: %d", code)
        if code == 404:
            sys.exit(0)
        if code == 500:
            logger.error("Error return:")
            logger.error(response.content)

        # Headers.
        if "Content-Type" in response.headers:
            logger.debug("Returning content type: '%s'", response.headers["Content-Type"])
            print("Content-Type: " + response.headers["Content-Type"])
        else:
            logger.debug("No content type. Returning 'text/plain'.")
            print("Content-Type: text/plain")

        # Blank separator before page body.
        print()

        # Send the page body.  This is done in slices because of a Windows bug
        # See https://bugs.python.org/issue11395.
        body = response.content
        written = 0
        while written < len(body):
            portion = body[written:written + RESPONSE_CHUNK_SIZE]
            sys.stdout.write(portion)
            written += RESPONSE_CHUNK_SIZE
        sys.exit(0)

    def do_proxy_request(self):
        "Perform the proxied call and return the results to the caller."
        requestURL = self.get_remote_url()
        method = self.incoming.verb

        # Do the actual request.
        logger.debug("Performing '%s' request to '%s'.", method, requestURL)
        if method == 'GET':
            logger.debug("Params: '%s'", repr(self.incoming.get_filtered_query_string()))
            response = requests.get(requestURL, params=self.incoming.get_filtered_query_string())
        elif method == 'POST':
            logger.debug("POST Data: '%s'", repr(self.incoming.form_data))
            response = requests.post(requestURL, json=self.incoming.form_data)
        elif method == 'PUT':
            response = requests.put(requestURL, json=self.incoming.form_data)
        elif method == 'PATCH':
            response = requests.patch(requestURL)
        elif method == 'OPTIONS':
            response = requests.options(requestURL)
        elif method == 'DELETE':
            response = requests.delete(requestURL)
        else:
            logger.error("Unknown request type: '%s'", method)
            raise NotImplementedError("Don't know how to handle request type: '%s'." % method)

        self._send_return(response)


try:
    logger.debug("Begin Request")
    incomingRequest = IncomingRequest()

    if incomingRequest.may_be_proxied():
        proxy = Proxy(incomingRequest, PROXIED_URL_BASE)
        proxy.do_proxy_request()
    else:
        print("Status: 403\n\n<h1>Not allowed.</h1>")


except Exception:
    print("Status: 500\n<h1>Error servicing request.</h1>")
    logger.error('Error servicing request.', exc_info=True)
    raise
finally:
    logger.debug("End Request")

