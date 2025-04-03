# ----------------------------------------------------------------------
# Initiate a new CDR Session using the user's NIH domain account login.
# JIRA::OCECDR-3849
# ----------------------------------------------------------------------
import os
import cdrlite
import datetime

session = None
auth_user = os.environ.get("AUTH_USER")
if auth_user:
    name = auth_user.split("\\")[-1]
    try:
        session = cdrlite.login(name)
    except Exception:
        session = False
try:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fp = open("d:/cdr/log/admin-login.log", "a")
    fp.write("%s login.py %s %s\n" % (now, repr(auth_user), repr(session)))
    fp.close()
except Exception:
    pass
if session:
    print("Content-type: text/plain")
    print("X-Content-Type-Options: nosniff\n")
    print(session)
else:
    print("Status: 401 Unauthorized\n")
