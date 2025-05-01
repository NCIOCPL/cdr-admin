# ----------------------------------------------------------------------
# Initiate a new CDR Session using the user's NIH domain account login
# and redirects to the top level CDR Admin menu.
# JIRA::OCECDR-3849
# JIRA::OCECDR-4092
# ----------------------------------------------------------------------

import os
import cdrlite
import datetime
import urllib.parse

target = "cgi-bin/cdr/Admin.py"
query_string = os.environ.get("QUERY_STRING")
if query_string:
    for key, value in urllib.parse.parse_qsl(query_string):
        if key.lower() == "target":
            target = value
session = None
auth_user = os.environ.get("AUTH_USER")
webserver = os.environ.get("SERVER_NAME")
if auth_user:
    domain, name = auth_user.split("\\")
    if domain.upper() == "NIH":
        try:
            session = cdrlite.login(name)
        except Exception:
            session = False
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
try:
    strings = now, repr(auth_user), repr(session), target
    fp = open("d:/cdr/log/admin-login.log", "a")
    fp.write("{} admin.py {} {} {}\n".format(*strings))
    fp.close()
except Exception:
    pass
if session:
    if "//" not in target:
        path = target.lstrip("/")
        target = f"https://{webserver}/{path}"
    delimiter = "&" if "?" in target else "?"
    url = f"{target}{delimiter}Session={session}"
    print(f"Location: {url}\n")
else:
    print("Status: 401 Unauthorized\n")
