#!/usr/bin/env python

"""Install a CDR file.
"""

from hashlib import sha256
from logging import basicConfig, error, exception, info, warning
from os import environ
from pathlib import Path
from subprocess import run
from sys import stdin, stdout
from urllib.parse import unquote_plus
from cdrapi.users import Session

FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
LOGFILE = r"d:\cdr\log\install.log"
FIX_PERMISSIONS = r"d:\cdr\bin\fix-permissions.cmd"


def bail(code, reason):
    """Tell the client why the request failed.

    Required arguments:
        code - HTTP status code
        reason - text explanation for the problem
    """

    reason = str(reason).replace("\r", "").replace("\n", " ")
    stdout.buffer.write(f"""\
Content-type: text/plain;charset=utf-8
Status: {code} {reason}

""".encode("utf-8"))
    exit(0)


basicConfig(filename=LOGFILE, format=FORMAT, level="INFO")
info("top of script")
query_string = environ["QUERY_STRING"]
info("query_string: %s", query_string)
content_length = int(environ["CONTENT_LENGTH"])
info("content_length: %d", content_length)
parameters = {}
body = ""
if query_string:
    for parameter in query_string.split("&"):
        key, value = parameter.split("=")
        parameters[key] = unquote_plus(value)
        info("%s=%s", key, parameters[key])

session_name = parameters.get("session")
if not session_name:
    error("no session specified")
    bail(401, "No session specified")
error("some session specified")
try:
    session = Session(session_name)
except Exception as e:
    exception("Session()")
    bail(403, e)
info("testing permissions")
if not session.can_do("MANAGE SERVER FILES"):
    error("unauthorized")
    bail(403, "Unauthorized")
path = parameters.get("path")
if not path:
    error("no path specified")
    bail(400, "No path specified")
file_bytes = stdin.buffer.read(content_length)
count = len(file_bytes)
if count != content_length:
    error("asked for %d bytes but got %d", content_length, count)
    bail(400, "Unable to read file bytes")
info("read %d file bytes", count)
checksum = sha256(file_bytes).hexdigest()
if checksum != parameters.get("sum"):
    error("mismatched checksum %s", checksum)
    bail(400, f"Mismatched checksum {checksum}")
try:
    p = Path(path).resolve()
except Exception as e:
    exception("resolve()")
    bail(500, f"resolve(): {e}")
try:
    p.parent.mkdir(parents=True, exist_ok=True)
except Exception as e:
    exception("mkdir()")
    bail(500, f"mkdir(): {e}")
try:
    Path(path).write_bytes(file_bytes)
except Exception as e:
    exception("write_bytes()")
    bail(500, f"write_bytes(): {e}")
command = FIX_PERMISSIONS, str(p)
info("running fix permissions on %s", p)
opts = dict(capture_output=True, shell=True, encoding="utf-8")
process = run(command, **opts)
if process.returncode:
    warning("fix-permissions: %d (%s)", process.returncode, process.stdout)

stdout.buffer.write(f"""\
Content-type: text/plain;charset=utf-8

read {len(file_bytes)} bytes
checksum is {checksum}
path is {parameters['path']}
output from fix-permissions script:
{process.stdout}
*** File installed successfully! ***""".encode("utf-8"))
